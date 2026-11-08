"""Regras de metas e relatos que alteram dados ou decidem o que cada papel vê."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import Papel, Vinculo
from accounts.permissions import pode

from .models import InteresseParceria, Meta, PerfilParceria, RelatoSocialVerdigis


# ---------- Metas ----------

def metas_visiveis(request):
    """Metas da empresa da requisição que o usuário pode ver."""
    metas = Meta.objects.filter(company=request.empresa).select_related('funcionario__user')
    if request.user.papel == Papel.FUNCIONARIO:
        metas = metas.filter(Q(tipo='GERAL') | Q(funcionario=request.vinculo))
    return metas


def criar_meta(request, form):
    """Salva a meta na empresa da requisição; para o funcionário, é sempre individual dele."""
    meta = form.save(commit=False)
    meta.company = request.empresa
    meta.usuario = request.user
    if request.user.papel == Papel.FUNCIONARIO:
        meta.tipo = 'INDIVIDUAL'
        meta.funcionario = request.vinculo
    meta.save()
    return meta


# ---------- Relatos ----------

def relatos_da_empresa(request, incluir_ocultos=False):
    """Relatos da empresa da requisição; os ocultos só entram quando pedido (moderação)."""
    relatos = RelatoSocialVerdigis.objects.filter(company=request.empresa)
    if not incluir_ocultos:
        relatos = relatos.filter(oculto_em__isnull=True)
    return relatos


def relatos_proprios(request):
    """O que o funcionário vê: só os relatos não anônimos dele que não foram ocultados."""
    return relatos_da_empresa(request).filter(usuario=request.user, eh_anonimo=False)


def pode_ver_relato(request, relato):
    """Quem vê tudo vê o relato; oculto só para quem modera; o autor vê o próprio não anônimo."""
    if relato.oculto_em is not None:
        return pode(request, 'relato.moderar')
    if pode(request, 'relato.ver_todos'):
        return True
    return not relato.eh_anonimo and relato.usuario_id == request.user.pk


def enviar_relato(request, form):
    """Grava o relato na empresa da requisição, sempre com o autor guardado."""
    relato = form.save(commit=False)
    relato.company = request.empresa
    relato.usuario = request.user
    relato.save()
    return relato


def ocultar_relato(relato, user, motivo=''):
    """Tira o relato das listas; continua visível só para quem modera."""
    relato.oculto_em = timezone.now()
    relato.oculto_por = user
    relato.motivo_ocultacao = motivo
    relato.save(update_fields=['oculto_em', 'oculto_por', 'motivo_ocultacao'])


def restaurar_relato(relato):
    """Devolve um relato oculto às listas."""
    with transaction.atomic():
        relato.oculto_em = None
        relato.oculto_por = None
        relato.motivo_ocultacao = ''
        relato.save(update_fields=['oculto_em', 'oculto_por', 'motivo_ocultacao'])


def nome_exibido(relato, request):
    """Único ponto que decide o nome do autor mostrado na tela. Anônimo nunca revela ninguém."""
    if relato.eh_anonimo:
        return 'Anônimo'
    if relato.usuario_id is None:
        return 'Ex-colaborador'
    if relato.usuario_id == request.user.pk:
        return 'Você'
    vinculo = Vinculo.objects.filter(user_id=relato.usuario_id, company_id=relato.company_id).first()
    nome = relato.usuario.nome
    if vinculo is None:
        return nome
    return f'{nome} · {vinculo.cargo} · {vinculo.setor}'

# ---------- Painel de Parcerias ----------

PILARES_INFO = {
    'E': {
        'codigo': 'E', 'nome': 'Ambiental', 'titulo': 'Environmental', 'cor': 'success',
        'descricao': 'Energia, emissões, água, resíduos e uso de recursos.',
    },
    'S': {
        'codigo': 'S', 'nome': 'Social', 'titulo': 'Social', 'cor': 'primary',
        'descricao': 'Pessoas, diversidade, saúde, segurança e comunidade.',
    },
    'G': {
        'codigo': 'G', 'nome': 'Governança', 'titulo': 'Governance', 'cor': 'warning',
        'descricao': 'Ética, transparência, compliance e gestão de riscos.',
    },
}


def perfil_parceria(company):
    """Perfil da empresa no painel; é criado (invisível) na primeira consulta."""
    perfil, _ = PerfilParceria.objects.get_or_create(company=company)
    return perfil


def _resumo_metas_por_empresa(company_ids, pilar=None):
    """{company_id: {'total': n, 'concluidas': n}} só com contagens; nada do texto das metas sai daqui."""
    metas = Meta.objects.filter(company_id__in=company_ids)
    if pilar:
        metas = metas.filter(pilar_esg=pilar)
    linhas = metas.values('company_id').annotate(total=Count('id'), concluidas=Count('id', filter=Q(completo=True)))
    return {linha['company_id']: linha for linha in linhas}


def resumo_metas_por_pilar(company):
    """Contagens de metas da empresa por pilar: {'E': {...}, 'S': {...}, 'G': {...}}."""
    linhas = (
        Meta.objects.filter(company=company).values('pilar_esg')
        .annotate(total=Count('id'), concluidas=Count('id', filter=Q(completo=True)))
    )
    por_pilar = {linha['pilar_esg']: linha for linha in linhas}
    resumo = {}
    for codigo in PILARES_INFO:
        linha = por_pilar.get(codigo, {})
        total, concluidas = linha.get('total', 0), linha.get('concluidas', 0)
        resumo[codigo] = {
            'total': total,
            'concluidas': concluidas,
            'percentual': round(concluidas * 100 / total) if total else 0,
        }
    return resumo


def diagnostico_pilares(empresa):
    """Passo "Exibir eixos de compatibilidade": por pilar, o que a empresa já faz e quantos parceiros existem."""
    resumo = resumo_metas_por_pilar(empresa)
    parceiros = {
        linha['qualidades__pilar']: linha['total']
        for linha in (
            PerfilParceria.objects.filter(visivel=True, qualidades__pilar__isnull=False)
            .exclude(company=empresa)
            .values('qualidades__pilar')
            .annotate(total=Count('id', distinct=True))
        )
    }
    perfil = perfil_parceria(empresa)
    necessidades = {}
    for qualidade in perfil.necessidades.all():
        necessidades[qualidade.pilar] = necessidades.get(qualidade.pilar, 0) + 1

    eixos = []
    for codigo, info in PILARES_INFO.items():
        eixos.append({
            **info,
            'metas_total': resumo[codigo]['total'],
            'metas_concluidas': resumo[codigo]['concluidas'],
            'percentual': resumo[codigo]['percentual'],
            'parceiros': parceiros.get(codigo, 0),
            'necessidades': necessidades.get(codigo, 0),
        })
    return eixos, perfil


def parceiros_do_pilar(empresa, pilar, qualidades=(), acessibilidades=(), busca=''):
    """
    Empresas visíveis com ao menos uma qualidade no pilar.

    Filtros: todas as acessibilidades marcadas são exigidas; basta ter uma das qualidades marcadas.
    A compatibilidade compara as qualidades do parceiro com as marcadas no filtro ou, sem filtro de
    qualidades, com o que a empresa declarou procurar naquele pilar.
    """
    perfis = (
        PerfilParceria.objects.filter(visivel=True, qualidades__pilar=pilar)
        .exclude(company=empresa)
        .select_related('company')
        .prefetch_related('qualidades', 'acessibilidades')
        .distinct()
    )
    for recurso in acessibilidades:
        perfis = perfis.filter(acessibilidades=recurso)
    if qualidades:
        perfis = perfis.filter(qualidades__in=qualidades)
    if busca:
        perfis = perfis.filter(company__nome_fantasia__icontains=busca)
    perfis = list(perfis)

    if qualidades:
        criterio = {q.pk for q in qualidades}
    else:
        criterio = {q.pk for q in perfil_parceria(empresa).necessidades.all() if q.pilar == pilar}

    ids = [perfil.company_id for perfil in perfis]
    metas = _resumo_metas_por_empresa(ids, pilar)
    enviados = set(InteresseParceria.objects.filter(origem=empresa, destino_id__in=ids).values_list('destino_id', flat=True))
    recebidos = set(InteresseParceria.objects.filter(destino=empresa, origem_id__in=ids).values_list('origem_id', flat=True))

    for perfil in perfis:
        no_pilar = [q for q in perfil.qualidades.all() if q.pilar == pilar]
        perfil.qualidades_pilar = no_pilar
        perfil.em_comum = [q.pk for q in no_pilar if q.pk in criterio]
        perfil.compatibilidade = round(len(perfil.em_comum) * 100 / len(criterio)) if criterio else None
        resumo = metas.get(perfil.company_id, {})
        perfil.metas_total = resumo.get('total', 0)
        perfil.metas_concluidas = resumo.get('concluidas', 0)
        perfil.interesse_enviado = perfil.company_id in enviados
        perfil.match_mutuo = perfil.interesse_enviado and perfil.company_id in recebidos

    perfis.sort(key=lambda p: (-(p.compatibilidade or 0), -p.metas_concluidas, p.company.nome_fantasia.lower()))
    return perfis, bool(criterio)


def alternar_interesse(origem, destino, pilar):
    """Dá ou desfaz o match. Devolve True se o interesse passou a existir."""
    if origem.pk == destino.pk:
        raise ValidationError('Uma empresa não pode dar match em si mesma.')
    interesse, criado = InteresseParceria.objects.get_or_create(
        origem=origem, destino=destino, defaults={'pilar': pilar},
    )
    if not criado:
        interesse.delete()
    return criado


def tem_match_mutuo(empresa, outra):
    return (
        InteresseParceria.objects.filter(origem=empresa, destino=outra).exists()
        and InteresseParceria.objects.filter(origem=outra, destino=empresa).exists()
    )


def matches_da_empresa(empresa):
    """Matches separados em mútuos, enviados (sem resposta) e recebidos (ainda não retribuídos)."""
    enviados = list(InteresseParceria.objects.filter(origem=empresa).select_related('destino'))
    recebidos = list(InteresseParceria.objects.filter(destino=empresa).select_related('origem'))
    ids_enviados = {i.destino_id for i in enviados}
    ids_recebidos = {i.origem_id for i in recebidos}
    visiveis = set(
        PerfilParceria.objects.filter(visivel=True, company_id__in=ids_enviados | ids_recebidos)
        .values_list('company_id', flat=True)
    )

    def item(interesse, outra):
        return {
            'company': outra,
            'pilar': interesse.get_pilar_display(),
            'codigo_pilar': interesse.pilar,
            'criado_em': interesse.criado_em,
            'visivel': outra.pk in visiveis,
        }

    mutuos = [item(i, i.destino) for i in enviados if i.destino_id in ids_recebidos]
    so_enviados = [item(i, i.destino) for i in enviados if i.destino_id not in ids_recebidos]
    so_recebidos = [item(i, i.origem) for i in recebidos if i.origem_id not in ids_enviados]
    return {'mutuos': mutuos, 'enviados': so_enviados, 'recebidos': so_recebidos}