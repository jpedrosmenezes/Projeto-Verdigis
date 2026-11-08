"""Painel de Parcerias: a empresa procura parceiros ESG por eixo e dá match."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Papel

from . import services
from .forms import FiltroParceirosForm, PerfilParceriaForm
from .models import PerfilParceria

POR_PAGINA = 12


def painel_da_empresa(view):
    """
    Porta de entrada do painel: exige login, papel de empresa e empresa já cadastrada.

    Sem empresa cadastrada, o gestor é levado ao onboarding em vez de ver o painel.
    Funcionário e consultor recebem 403.
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.papel != Papel.EMPRESA:
            raise PermissionDenied
        if request.empresa is None:
            messages.warning(request, 'Cadastre a sua empresa para acessar o Painel de Parcerias.')
            return redirect('accounts:onboarding')
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def _pilar_ou_404(codigo):
    codigo = (codigo or '').upper()
    if codigo not in services.PILARES_INFO:
        raise Http404('Eixo inexistente.')
    return codigo


# Passo 1 do fluxo: "Exibir eixos de compatibilidade".
@painel_da_empresa
def painel(request):
    eixos, perfil = services.diagnostico_pilares(request.empresa)
    return render(request, 'dashboard/parcerias_painel.html', {
        'eixos': eixos,
        'perfil': perfil,
        'perfil_completo': perfil.qualidades.exists(),
        'total_matches_mutuos': len(services.matches_da_empresa(request.empresa)['mutuos']),
    })


# Passos 2 a 5: eixo escolhido, lista com ou sem filtros, lista de empresas compatíveis.
@painel_da_empresa
def eixo(request, pilar):
    pilar = _pilar_ou_404(pilar)

    form = FiltroParceirosForm(request.GET or None, pilar=pilar)
    if form.is_bound and not form.is_valid():
        messages.warning(request, 'Filtro inválido; mostrando a lista sem filtros.')
        form = FiltroParceirosForm(None, pilar=pilar)

    filtros = form.cleaned_data if form.is_bound else {}
    parceiros, por_necessidades = services.parceiros_do_pilar(
        request.empresa,
        pilar,
        qualidades=filtros.get('qualidades', ()),
        acessibilidades=filtros.get('acessibilidades', ()),
        busca=filtros.get('busca', ''),
    )

    pagina = Paginator(parceiros, POR_PAGINA).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'dashboard/parcerias_eixo.html', {
        'pilar': services.PILARES_INFO[pilar],
        'form': form,
        'com_filtros': form.aplicado,
        'pagina': pagina,
        'total': len(parceiros),
        'por_necessidades': por_necessidades,
        'qs': params.urlencode(),
        'next': request.get_full_path(),
    })


# Passo 6: "Saber mais" com perfil, qualidades e acessibilidade.
@painel_da_empresa
def detalhe(request, company_id):
    perfil = get_object_or_404(
        PerfilParceria.objects.select_related('company').prefetch_related('qualidades', 'acessibilidades'),
        company_id=company_id, visivel=True,
    )
    if perfil.company_id == request.empresa.pk:
        return redirect('dashboard:parcerias_perfil')

    qualidades = list(perfil.qualidades.all())
    pilar_atual = request.GET.get('pilar', '').upper()
    if pilar_atual not in services.PILARES_INFO:
        pilar_atual = qualidades[0].pilar if qualidades else 'E'

    grupos = []
    resumo = services.resumo_metas_por_pilar(perfil.company)
    for codigo, info in services.PILARES_INFO.items():
        do_pilar = [q for q in qualidades if q.pilar == codigo]
        if do_pilar:
            grupos.append({**info, 'qualidades': do_pilar, 'metas': resumo[codigo]})

    return render(request, 'dashboard/parcerias_detalhe.html', {
        'perfil': perfil,
        'company': perfil.company,
        'grupos': grupos,
        'pilar': services.PILARES_INFO[pilar_atual],
        'eixos': services.PILARES_INFO.values(),
        'interesse_enviado': request.empresa.interesses_enviados.filter(destino=perfil.company).exists(),
        'match_mutuo': services.tem_match_mutuo(request.empresa, perfil.company),
        'next': request.get_full_path(),
    })


@require_POST
@painel_da_empresa
def alternar_match(request, company_id):
    perfil = get_object_or_404(PerfilParceria.objects.select_related('company'), company_id=company_id, visivel=True)
    pilar = _pilar_ou_404(request.POST.get('pilar', 'E'))
    try:
        criado = services.alternar_interesse(request.empresa, perfil.company, pilar)
    except ValidationError as erro:
        messages.error(request, erro.messages[0])
    else:
        nome = perfil.company.nome_fantasia
        if not criado:
            messages.info(request, f'Match com {nome} desfeito.')
        elif services.tem_match_mutuo(request.empresa, perfil.company):
            messages.success(request, f'Match mútuo com {nome}! As duas empresas demonstraram interesse.')
        else:
            messages.success(request, f'Você deu match em {nome}. Avisaremos quando houver retribuição.')

    destino = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destino = reverse('dashboard:parcerias_eixo', args=[pilar])
    return redirect(destino)


@painel_da_empresa
def meus_matches(request):
    return render(request, 'dashboard/parcerias_matches.html', services.matches_da_empresa(request.empresa))


@painel_da_empresa
def meu_perfil(request):
    perfil = services.perfil_parceria(request.empresa)
    form = PerfilParceriaForm(request.POST if request.method == 'POST' else None, instance=perfil)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Perfil de parceria atualizado.')
        return redirect('dashboard:parcerias')
    return render(request, 'dashboard/parcerias_perfil.html', {'form': form, 'perfil': perfil})