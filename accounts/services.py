"""Regras que alteram dados de contas, empresas e vínculos."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import (
    Capacidade, Company, ConcessaoConsultor, Notificacao, Papel, SolicitacaoVinculo,
    TipoNotificacao, TipoVinculo, User, Vinculo, normalizar_codigo,
)

LIMITE_METAS_NO_AVISO = 5


def notificar(destinatario, tipo, texto, url=''):
    """Cria uma notificação no site. É o único ponto que cria notificações."""
    return Notificacao.objects.create(destinatario=destinatario, tipo=tipo, texto=texto[:500], url=url)


# ---------- Triagem ----------

def concluir_onboarding(user, papel, form):
    """Salva o formulário da triagem e define o papel; recusa se o papel já existir."""
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.papel:
            raise ValidationError('Você já escolheu como usa a plataforma.')
        obj = form.save(commit=False)
        if papel == Papel.EMPRESA:
            obj.responsavel = user
        else:
            obj.user = user
            user.nome = form.cleaned_data['nome']
            user.telefone = form.cleaned_data.get('telefone', '')
        obj.save()
        user.papel = papel
        user.save()
        return obj


# ---------- Solicitações de vínculo ----------

def buscar_empresa_por_codigo(codigo):
    return Company.objects.filter(codigo=normalizar_codigo(codigo)).first()


def criar_solicitacao(user, codigo, cargo, setor, mensagem=''):
    """Pede para entrar numa empresa pelo código e avisa o responsável."""
    if user.papel not in (Papel.FUNCIONARIO, Papel.CONSULTOR):
        raise PermissionDenied
    company = buscar_empresa_por_codigo(codigo)
    if company is None:
        raise ValidationError('Código não encontrado.')
    if user.papel == Papel.FUNCIONARIO and Vinculo.objects.filter(user=user).exists():
        raise ValidationError('Você já faz parte de uma empresa. Saia dela antes de pedir para entrar em outra.')
    if Vinculo.objects.filter(user=user, company=company).exists():
        raise ValidationError('Você já faz parte desta empresa.')
    with transaction.atomic():
        if SolicitacaoVinculo.objects.filter(
            solicitante=user, company=company, status=SolicitacaoVinculo.Status.PENDENTE,
        ).exists():
            raise ValidationError('Você já tem um pedido em análise para esta empresa.')
        solicitacao = SolicitacaoVinculo.objects.create(
            solicitante=user, company=company, cargo=cargo, setor=setor, mensagem=mensagem,
        )
        notificar(
            company.responsavel, TipoNotificacao.SOLICITACAO_RECEBIDA,
            f'{user.nome} ({user.get_papel_display().lower()}) pediu para entrar na equipe.',
            reverse('dashboard:equipe'),
        )
    return solicitacao


def _exigir_pendente(solicitacao):
    if solicitacao.status != SolicitacaoVinculo.Status.PENDENTE:
        raise ValidationError('Este pedido já foi respondido.')


def cancelar_solicitacao(solicitacao):
    """O próprio solicitante desiste do pedido pendente."""
    _exigir_pendente(solicitacao)
    solicitacao.status = SolicitacaoVinculo.Status.CANCELADA
    solicitacao.respondida_em = timezone.now()
    solicitacao.save(update_fields=['status', 'respondida_em'])


def aceitar_solicitacao(solicitacao):
    """Cria o vínculo e, para funcionário, cancela os outros pedidos pendentes dele."""
    with transaction.atomic():
        solicitacao = SolicitacaoVinculo.objects.select_for_update().select_related(
            'solicitante', 'company',
        ).get(pk=solicitacao.pk)
        _exigir_pendente(solicitacao)
        user = solicitacao.solicitante
        # O tipo vem do papel da pessoa, nunca do formulário.
        tipo = {Papel.FUNCIONARIO: TipoVinculo.FUNCIONARIO, Papel.CONSULTOR: TipoVinculo.CONSULTOR}.get(user.papel)
        if tipo is None:
            raise ValidationError('Esta pessoa não pode mais entrar em empresas.')
        if tipo == TipoVinculo.FUNCIONARIO and Vinculo.objects.filter(user=user).exists():
            raise ValidationError('Esta pessoa já entrou em outra empresa.')
        vinculo = Vinculo.objects.create(
            company=solicitacao.company, user=user, tipo=tipo, cargo=solicitacao.cargo, setor=solicitacao.setor,
        )
        agora = timezone.now()
        solicitacao.status = SolicitacaoVinculo.Status.ACEITA
        solicitacao.respondida_em = agora
        solicitacao.save(update_fields=['status', 'respondida_em'])
        if tipo == TipoVinculo.FUNCIONARIO:
            SolicitacaoVinculo.objects.filter(
                solicitante=user, status=SolicitacaoVinculo.Status.PENDENTE,
            ).update(status=SolicitacaoVinculo.Status.CANCELADA, respondida_em=agora)
        notificar(
            user, TipoNotificacao.SOLICITACAO_ACEITA,
            f'Seu pedido para entrar em {solicitacao.company.nome_fantasia} foi aceito.',
            reverse('dashboard:dashboard'),
        )
    return vinculo


def recusar_solicitacao(solicitacao):
    """A empresa recusa o pedido e avisa o solicitante."""
    _exigir_pendente(solicitacao)
    solicitacao.status = SolicitacaoVinculo.Status.RECUSADA
    solicitacao.respondida_em = timezone.now()
    solicitacao.save(update_fields=['status', 'respondida_em'])
    notificar(
        solicitacao.solicitante, TipoNotificacao.SOLICITACAO_RECUSADA,
        f'Seu pedido para entrar em {solicitacao.company.nome_fantasia} foi recusado.',
        reverse('accounts:meus_vinculos'),
    )


# ---------- Saída da equipe ----------

def _resumo_metas_sem_responsavel(vinculo):
    """Títulos das metas individuais que vão ficar sem responsável (até 5, "e mais N")."""
    if vinculo.tipo != TipoVinculo.FUNCIONARIO:
        return ''
    nomes = list(vinculo.metas.filter(tipo='INDIVIDUAL').order_by('deadline').values_list('nome', flat=True))
    if not nomes:
        return ''
    texto = ', '.join(nomes[:LIMITE_METAS_NO_AVISO])
    if len(nomes) > LIMITE_METAS_NO_AVISO:
        texto += f' e mais {len(nomes) - LIMITE_METAS_NO_AVISO}'
    return f' Metas que ficaram sem responsável: {texto}.'


def _avisar_saida(vinculo, motivo):
    notificar(
        vinculo.company.responsavel, TipoNotificacao.MEMBRO_SAIU,
        f'{vinculo.user.nome} {motivo}.{_resumo_metas_sem_responsavel(vinculo)}',
        reverse('dashboard:equipe'),
    )


def encerrar_vinculo(vinculo, removido_pela_empresa=False):
    """Apaga o vínculo; as metas individuais do funcionário ficam sem responsável (SET_NULL)."""
    with transaction.atomic():
        if removido_pela_empresa:
            notificar(
                vinculo.user, TipoNotificacao.VINCULO_REMOVIDO,
                f'Você foi removido da equipe de {vinculo.company.nome_fantasia}.',
                reverse('accounts:meus_vinculos'),
            )
            _avisar_saida(vinculo, 'foi removido da equipe')
        else:
            _avisar_saida(vinculo, 'saiu da equipe')
        vinculo.delete()


# ---------- Capacidades do consultor ----------

def atualizar_capacidades(vinculo, capacidades, company):
    """Liga exatamente as capacidades informadas para um consultor da empresa; avisa se mudou."""
    if vinculo.company_id != company.pk or vinculo.tipo != TipoVinculo.CONSULTOR:
        raise PermissionDenied
    novas = {c for c in capacidades if c in Capacidade.values}
    with transaction.atomic():
        atuais = set(vinculo.concessoes.values_list('capacidade', flat=True))
        if novas == atuais:
            return False
        vinculo.concessoes.filter(capacidade__in=atuais - novas).delete()
        ConcessaoConsultor.objects.bulk_create(
            [ConcessaoConsultor(vinculo=vinculo, capacidade=c) for c in sorted(novas - atuais)]
        )
        notificar(
            vinculo.user, TipoNotificacao.PERMISSOES_ALTERADAS,
            f'{company.nome_fantasia} alterou o que você pode fazer na empresa.',
            reverse('accounts:meus_vinculos'),
        )
    return True


# ---------- Exclusões ----------

def excluir_empresa(company):
    """Apaga a empresa e tudo dela; avisa a equipe e devolve o responsável à triagem."""
    with transaction.atomic():
        responsavel = company.responsavel
        nome = company.nome_fantasia
        avisados = set()
        for vinculo in company.vinculos.select_related('user'):
            avisados.add(vinculo.user_id)
            notificar(
                vinculo.user, TipoNotificacao.EMPRESA_ENCERRADA,
                f'A empresa {nome} encerrou a conta na Verdigis. Seu vínculo com ela foi removido.',
                reverse('accounts:meus_vinculos'),
            )
        pendentes = company.solicitacoes.filter(status=SolicitacaoVinculo.Status.PENDENTE).select_related('solicitante')
        for solicitacao in pendentes:
            if solicitacao.solicitante_id not in avisados:
                avisados.add(solicitacao.solicitante_id)
                notificar(
                    solicitacao.solicitante, TipoNotificacao.EMPRESA_ENCERRADA,
                    f'A empresa {nome} encerrou a conta na Verdigis. Seu pedido foi cancelado.',
                    reverse('accounts:meus_vinculos'),
                )
        # Cascata: vínculos, solicitações, metas e relatos.
        company.delete()
        responsavel.papel = Papel.NENHUM
        responsavel.save(update_fields=['papel'])


def excluir_conta(user):
    """Apaga a conta; quem sai de uma equipe avisa a empresa, e o responsável apaga a empresa antes."""
    with transaction.atomic():
        if user.papel == Papel.EMPRESA:
            company = Company.objects.filter(responsavel=user).first()
            if company is not None:
                excluir_empresa(company)
        else:
            for vinculo in Vinculo.objects.filter(user=user).select_related('company__responsavel', 'user'):
                _avisar_saida(vinculo, 'excluiu a conta na Verdigis')
        User.objects.filter(pk=user.pk).delete()
