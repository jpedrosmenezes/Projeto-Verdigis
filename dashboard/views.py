from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import services as contas
from accounts.forms import ConfirmarSenhaForm, EntrarEmpresaForm
from accounts.middleware import CHAVE_EMPRESA_ATIVA
from accounts.models import (
    DESCRICAO_CAPACIDADE, Capacidade, Papel, SolicitacaoVinculo, TipoVinculo, Vinculo,
)
from accounts.permissions import empresa_required, exigir, pode

from . import services
from .forms import FormMetaFuncionario, FormsMetas, OcultarRelatoForm, RelatoSocialForm
from .models import Meta, RelatoSocialVerdigis

SENTIMENTOS = ('POSITIVO', 'NEGATIVO', 'NEUTRO')


def _primeira_mensagem(erro):
    return erro.messages[0] if hasattr(erro, 'messages') else str(erro)


# ---------- Início ----------

@login_required
def home(request):
    contexto = {'metas_atrasadas': 0, 'metas_concluidas': 0}
    user = request.user

    if request.empresa is not None and pode(request, 'meta.ver'):
        metas = services.metas_visiveis(request)
        contexto['metas_atrasadas'] = metas.filter(completo=False, deadline__lt=timezone.localdate()).count()
        contexto['metas_concluidas'] = metas.filter(completo=True).count()

    if user.papel == Papel.EMPRESA and request.empresa is not None:
        contexto['pedidos_pendentes'] = request.empresa.solicitacoes.filter(
            status=SolicitacaoVinculo.Status.PENDENTE,
        ).count()

    if user.papel in (Papel.FUNCIONARIO, Papel.CONSULTOR):
        if user.papel == Papel.CONSULTOR:
            contexto['vinculos_consultor'] = Vinculo.objects.filter(user=user).select_related('company')
        if request.empresa is None:
            contexto['form_entrar'] = EntrarEmpresaForm()
            contexto['pedidos_enviados'] = SolicitacaoVinculo.objects.filter(
                solicitante=user, status=SolicitacaoVinculo.Status.PENDENTE,
            ).select_related('company')

    return render(request, 'dashboard/dashboard.html', contexto)


@login_required
@require_POST
def trocar_contexto(request):
    """Consultor escolhe em qual empresa está atuando."""
    if request.user.papel != Papel.CONSULTOR:
        raise PermissionDenied
    vinculo = get_object_or_404(Vinculo, user=request.user, company_id=request.POST.get('company'))
    request.session[CHAVE_EMPRESA_ATIVA] = vinculo.company_id
    messages.success(request, f'Agora você está atuando em {vinculo.company.nome_fantasia}.')
    return redirect('dashboard:dashboard')


# ---------- Equipe ----------

ABAS_EQUIPE = ('pendentes', 'funcionarios', 'consultores')


@login_required
@empresa_required
def equipe(request):
    exigir(request, 'equipe.gerir')
    company = request.empresa
    aba = request.GET.get('aba', 'pendentes')
    if aba not in ABAS_EQUIPE:
        aba = 'pendentes'

    pendentes = company.solicitacoes.filter(
        status=SolicitacaoVinculo.Status.PENDENTE,
    ).select_related('solicitante').order_by('criada_em')
    vinculos = company.vinculos.select_related('user').prefetch_related('concessoes').order_by('user__nome')
    funcionarios = [v for v in vinculos if v.tipo == TipoVinculo.FUNCIONARIO]
    consultores = [v for v in vinculos if v.tipo == TipoVinculo.CONSULTOR]
    for consultor in consultores:
        ligadas = {c.capacidade for c in consultor.concessoes.all()}
        consultor.capacidades_ui = [
            {'valor': c.value, 'rotulo': c.label, 'descricao': DESCRICAO_CAPACIDADE[c], 'ligada': c.value in ligadas}
            for c in Capacidade
        ]
        consultor.resumo_capacidades = ', '.join(c.label.lower() for c in Capacidade if c.value in ligadas)

    return render(request, 'dashboard/equipe.html', {
        'company': company,
        'aba': aba,
        'pendentes': pendentes,
        'funcionarios': funcionarios,
        'consultores': consultores,
    })


@login_required
@require_POST
@empresa_required
def responder_solicitacao(request, solicitacao_id):
    exigir(request, 'equipe.gerir')
    solicitacao = get_object_or_404(SolicitacaoVinculo, id=solicitacao_id, company=request.empresa)
    acao = request.POST.get('acao')
    try:
        if acao == 'aceitar':
            contas.aceitar_solicitacao(solicitacao)
            messages.success(request, f'{solicitacao.solicitante.nome} agora faz parte da equipe.')
        elif acao == 'recusar':
            contas.recusar_solicitacao(solicitacao)
            messages.success(request, 'Pedido recusado.')
        else:
            messages.error(request, 'Ação inválida.')
    except ValidationError as erro:
        messages.error(request, _primeira_mensagem(erro))
    return redirect('dashboard:equipe')


@login_required
@require_POST
@empresa_required
def remover_membro(request, vinculo_id):
    exigir(request, 'equipe.gerir')
    vinculo = get_object_or_404(Vinculo.objects.select_related('user'), id=vinculo_id, company=request.empresa)
    aba = 'consultores' if vinculo.tipo == TipoVinculo.CONSULTOR else 'funcionarios'
    nome = vinculo.user.nome
    contas.encerrar_vinculo(vinculo, removido_pela_empresa=True)
    messages.success(request, f'{nome} foi removido da equipe.')
    return redirect(f"{reverse('dashboard:equipe')}?aba={aba}")


@login_required
@require_POST
@empresa_required
def salvar_capacidades(request, vinculo_id):
    exigir(request, 'equipe.gerir')
    vinculo = get_object_or_404(
        Vinculo.objects.select_related('user'), id=vinculo_id, company=request.empresa, tipo=TipoVinculo.CONSULTOR,
    )
    mudou = contas.atualizar_capacidades(vinculo, request.POST.getlist('capacidades'), request.empresa)
    if mudou:
        messages.success(request, f'Permissões de {vinculo.user.nome} atualizadas.')
    else:
        messages.info(request, 'Nenhuma permissão foi alterada.')
    return redirect(f"{reverse('dashboard:equipe')}?aba=consultores")


# ---------- Fábrica de metas ----------

def _form_meta(request, data=None, instance=None):
    if request.user.papel == Papel.FUNCIONARIO:
        return FormMetaFuncionario(data, instance=instance)
    return FormsMetas(data, instance=instance, company=request.empresa)


def _filtrar_por_colaborador(request, metas):
    """Filtro da Empresa e do consultor: um funcionário ou "sem responsável". Valor inválido é ignorado."""
    valor = request.GET.get('colaborador', '')
    if not valor or request.user.papel == Papel.FUNCIONARIO:
        return metas, ''
    if valor == 'sem':
        return metas.filter(tipo='INDIVIDUAL', funcionario__isnull=True), valor
    if valor.isdigit() and Vinculo.objects.filter(
        id=valor, company=request.empresa, tipo=TipoVinculo.FUNCIONARIO,
    ).exists():
        return metas.filter(funcionario_id=int(valor)), valor
    messages.warning(request, 'Colaborador inválido; mostrando todas as metas.')
    return metas, ''


@login_required
@empresa_required
def fabrica_metas_view(request):
    exigir(request, 'meta.ver')
    pode_criar = pode(request, 'meta.criar')

    if request.method == 'POST':
        exigir(request, 'meta.criar')
        form = _form_meta(request, request.POST)
        if form.is_valid():
            services.criar_meta(request, form)
            messages.success(request, 'Meta criada.')
            return redirect('dashboard:fabrica_metas')
    else:
        form = _form_meta(request)

    metas, colaborador = _filtrar_por_colaborador(request, services.metas_visiveis(request))
    metas = list(metas.order_by('completo', 'deadline'))
    for meta in metas:
        meta.pode_editar = pode(request, 'meta.editar', meta)
        meta.pode_concluir = pode(request, 'meta.concluir', meta)
        meta.pode_apagar = pode(request, 'meta.apagar', meta)

    filtro = None
    if request.user.papel != Papel.FUNCIONARIO:
        filtro = Vinculo.objects.filter(company=request.empresa, tipo=TipoVinculo.FUNCIONARIO).select_related('user')

    return render(request, 'dashboard/fabrica_metas.html', {
        'metas': metas,
        'form': form if pode_criar else None,
        'hoje': timezone.localdate(),
        'colaboradores': filtro,
        'colaborador_atual': colaborador,
        'eh_funcionario': request.user.papel == Papel.FUNCIONARIO,
    })


def _meta_da_empresa(request, meta_id):
    # Id de outra empresa dá 404 antes de qualquer checagem de permissão.
    return get_object_or_404(Meta, id=meta_id, company=request.empresa)


@login_required
@empresa_required
def editar_meta_view(request, meta_id):
    meta = _meta_da_empresa(request, meta_id)
    exigir(request, 'meta.editar', meta)

    form = _form_meta(request, request.POST if request.method == 'POST' else None, instance=meta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Meta atualizada.')
        return redirect('dashboard:fabrica_metas')

    return render(request, 'dashboard/editar_meta.html', {'form': form, 'meta': meta})


@login_required
@require_POST
@empresa_required
def alternar_conclusao_view(request, meta_id):
    meta = _meta_da_empresa(request, meta_id)
    exigir(request, 'meta.concluir', meta)
    meta.completo = not meta.completo
    meta.save(update_fields=['completo'])
    return redirect('dashboard:fabrica_metas')


@login_required
@require_POST
@empresa_required
def deletar_meta_view(request, meta_id):
    meta = _meta_da_empresa(request, meta_id)
    exigir(request, 'meta.apagar', meta)
    meta.delete()
    messages.success(request, 'Meta excluída.')
    return redirect('dashboard:fabrica_metas')


# ---------- Relatos ----------

@login_required
@empresa_required
def dashboard_social_verdigis(request):
    exigir(request, 'relato.ver_todos')
    moderador = pode(request, 'relato.moderar')
    aba = 'ocultos' if moderador and request.GET.get('aba') == 'ocultos' else ''

    if aba == 'ocultos':
        relatos = services.relatos_da_empresa(request, incluir_ocultos=True).filter(oculto_em__isnull=False)
        return render(request, 'dashboard/avaliacao_ocultos.html', {
            'relatos': relatos.select_related('usuario').order_by('-oculto_em'),
            'moderador': moderador,
        })

    base = services.relatos_da_empresa(request)
    tema = request.GET.get('tema', '')
    sentimento = request.GET.get('sentimento', 'NEGATIVO')
    if sentimento not in SENTIMENTOS:
        sentimento = 'NEGATIVO'

    contagem = {m['tema_esg']: m['total'] for m in base.values('tema_esg').annotate(total=Count('id'))}
    nomes = dict(RelatoSocialVerdigis.TEMA_ESG_CHOICES)
    temas = [
        {'codigo': codigo, 'nome': nome, 'total': contagem.get(codigo, 0)}
        for codigo, nome in RelatoSocialVerdigis.TEMA_ESG_CHOICES
    ]

    relatos = base.filter(sentimento=sentimento).select_related('usuario').order_by('-data_registro')
    if tema in nomes:
        relatos = relatos.filter(tema_esg=tema)
    else:
        tema = ''

    return render(request, 'dashboard/avaliacao.html', {
        'relatos': relatos,
        'temas': temas,
        'tema_atual': tema,
        'tema_atual_nome': nomes.get(tema, ''),
        'sentimento_atual': sentimento,
        'moderador': moderador,
        'total_ocultos': services.relatos_da_empresa(request, incluir_ocultos=True).filter(
            oculto_em__isnull=False).count() if moderador else 0,
    })


def _relato_da_empresa(request, relato_id):
    return get_object_or_404(
        RelatoSocialVerdigis.objects.select_related('usuario'), id=relato_id, company=request.empresa,
    )


@login_required
@empresa_required
def detalhe_relato_view(request, relato_id):
    relato = _relato_da_empresa(request, relato_id)
    if not services.pode_ver_relato(request, relato):
        raise PermissionDenied
    return render(request, 'dashboard/avaliacao_detalhe.html', {
        'relato': relato,
        'moderador': pode(request, 'relato.moderar'),
        'form_ocultar': OcultarRelatoForm(),
        'voltar': 'dashboard:dashboard_social' if pode(request, 'relato.ver_todos') else 'dashboard:meus_relatos',
    })


@login_required
@empresa_required
def adicionar_avaliacao(request):
    exigir(request, 'relato.enviar')
    form = RelatoSocialForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        relato = services.enviar_relato(request, form)
        if relato.eh_anonimo:
            messages.success(request, 'Enviado. Por ser anônimo, ele não aparecerá na sua lista.')
        else:
            messages.success(request, 'Enviado. A empresa e os consultores verão seu nome neste relato.')
        return redirect('dashboard:adicionar_avaliacao')
    return render(request, 'dashboard/adicionar.html', {'form': form})


@login_required
@empresa_required
def meus_relatos(request):
    exigir(request, 'relato.enviar')
    return render(request, 'dashboard/meus_relatos.html', {
        'relatos': services.relatos_proprios(request).select_related('usuario').order_by('-data_registro'),
    })


@login_required
@require_POST
@empresa_required
def ocultar_relato_view(request, relato_id):
    relato = _relato_da_empresa(request, relato_id)
    exigir(request, 'relato.moderar')
    form = OcultarRelatoForm(request.POST)
    motivo = form.cleaned_data['motivo'] if form.is_valid() else ''
    services.ocultar_relato(relato, request.user, motivo)
    messages.success(request, 'Relato ocultado. Ele continua disponível na aba "Ocultos".')
    return redirect('dashboard:detalhe_relato', relato_id=relato.id)


@login_required
@require_POST
@empresa_required
def restaurar_relato_view(request, relato_id):
    relato = _relato_da_empresa(request, relato_id)
    exigir(request, 'relato.moderar')
    services.restaurar_relato(relato)
    messages.success(request, 'Relato restaurado.')
    return redirect('dashboard:detalhe_relato', relato_id=relato.id)


# ---------- Apagar empresa ----------

@login_required
@empresa_required
def apagar_empresa(request):
    exigir(request, 'empresa.apagar')
    company = request.empresa
    form = ConfirmarSenhaForm(request.user, request.POST if request.method == 'POST' else None, company=company)

    if request.method == 'POST' and form.is_valid():
        nome = company.nome_fantasia
        contas.excluir_empresa(company)
        messages.success(request, f'A empresa {nome} foi apagada. Escolha como quer continuar na plataforma.')
        return redirect('accounts:onboarding')

    return render(request, 'dashboard/apagar_empresa.html', {
        'form': form,
        'company': company,
        'total_membros': company.vinculos.count(),
        'total_metas': company.metas.count(),
        'total_relatos': company.relatos.count(),
    })
