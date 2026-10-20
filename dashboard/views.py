from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from urllib3 import request

from accounts.models import Company, Funcionario
from .forms import FormsMetas, RelatoSocialForm
from .models import Meta, RelatoSocialVerdigis


def _obter_empresa_usuario(user):
    company = Company.objects.filter(responsavel = user).first()
    if not company and hasattr(user, 'FUNCIONARIO'):
        company = user.FUNCIONARIO.company
    return company

@login_required
def home(request):
    company = _obter_empresa_usuario(request.user)

    if not company:
        metas = Meta.objects.none()
    elif hasattr(request.user, 'FUNCIONARIO'):
        # Funcionário vê as metas gerais da empresa OU as metas individuais dele
        metas = Meta.objects.filter(
            company=company
        ).filter(
            Q(tipo='GERAL') | Q(funcionario=request.user.FUNCIONARIO)
        )
    else: # para empresa ver todas as metas
        metas = Meta.objects.filter(company=company)

    return render(request, 'dashboard/dashboard.html', {
        'metas_atrasadas': metas.filter(completo=False, deadline__lt=timezone.localdate()).count(),
        'metas_concluidas': metas.filter(completo=True).count(),
    })


#Fabrica de metas
@login_required
def fabrica_metas_view(request):
    company = _obter_empresa_usuario(request.user)

    if not company:
        messages.error(request, "Cadastre sua empresa antes de usar a Fábrica de Metas.")
        return redirect('company_register')

    # Filtra a lista de acordo com o tipo de usuario
    if hasattr(request.user, 'FUNCIONARIO'): #esse hasattr serve justamente pra verificar se é funcionario ou geral
        metas = Meta.objects.filter(
            company=company
        ).filter(
            Q(tipo='GERAL') | Q(funcionario=request.user.FUNCIONARIO)
        ).order_by('completo', 'deadline')
    else:
        metas = Meta.objects.filter(company=company).order_by('completo', 'deadline')

    if request.method == 'POST':
        form = FormsMetas(company, request.POST)
        if form.is_valid():
            meta = form.save(commit=False)
            meta.company = company
            meta.usuario = request.user
            meta.save()
            return redirect('dashboard:fabrica_metas')
    else:
        form = FormsMetas(company)

    return render(request, 'dashboard/fabrica_metas.html', {
        'metas': metas,
        'form': form,
        'hoje': timezone.localdate(),
    })


@login_required
def editar_meta_view(request, meta_id):
    meta = get_object_or_404(Meta, id=meta_id, usuario=request.user)
    if request.method == 'POST':
        form = FormsMetas(request.POST, instance=meta) #instace == atualizar
        if form.is_valid():
            form.save()
            return redirect('dashboard:fabrica_metas')
    else:
        form = FormsMetas(instance=meta)

    return render(request, 'dashboard/editar_meta.html', {
        'form': form,
        'meta': meta,
    })


@login_required
@require_POST
def alternar_conclusao_view(request, meta_id):
    company = _obter_empresa_usuario(request.user)

    # Permite alterar se a meta for da empresa e (for geral OU for atribuída ao funcionário/criada por ele)
    if hasattr(request.user, 'FUNCIONARIO'):
        meta = get_object_or_404(
            Meta,
            Q(id=meta_id, company=company) & 
            (Q(tipo='GERAL') | Q(funcionario=request.user.FUNCIONARIO) | Q(usuario=request.user))
        )
    else:
        # Gestor/Admin da empresa pode alterar qualquer meta da empresa
        meta = get_object_or_404(Meta, id=meta_id, company=company)

    meta.completo = not meta.completo
    meta.save(update_fields=['completo'])
    
    return redirect('dashboard:fabrica_metas')



@login_required
@require_POST
def deletar_meta_view(request, meta_id):
    company = _obter_empresa_usuario(request.user)

    # Permite apagar se a meta for da empresa e (for geral OU for do próprio funcionário)
    if hasattr(request.user, 'FUNCIONARIO'):
        meta = get_object_or_404(
            Meta,
            Q(id=meta_id, company=company) & 
            (Q(tipo='GERAL') | Q(funcionario=request.user.FUNCIONARIO) | Q(usuario=request.user))
        )
    else:
        # Gestor/Admin da empresa pode apagar qualquer meta da empresa
        meta = get_object_or_404(Meta, id=meta_id, company=company)

    meta.delete()
    
    return redirect('dashboard:fabrica_metas')


@login_required
def dashboard_social_verdigis(request):
    tema = request.GET.get('tema', '')
    sentimento = request.GET.get('sentimento', 'NEGATIVO')
    if sentimento not in ('POSITIVO', 'NEGATIVO', 'NEUTRO'):
        sentimento = 'NEGATIVO'

    contagem = {
        m['tema_esg']: m['total']
        for m in RelatoSocialVerdigis.objects.values('tema_esg').annotate(total=Count('id'))
    }
    nomes = dict(RelatoSocialVerdigis.TEMA_ESG_CHOICES)
    temas = [
        {'codigo': codigo, 'nome': nome, 'total': contagem.get(codigo, 0)}
        for codigo, nome in RelatoSocialVerdigis.TEMA_ESG_CHOICES
    ]

    relatos = RelatoSocialVerdigis.objects.filter(sentimento=sentimento).order_by('-data_registro')
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
    })


@login_required
def detalhe_relato_view(request, relato_id):
    relato = get_object_or_404(RelatoSocialVerdigis, id=relato_id)
    return render(request, 'dashboard/avaliacao_detalhe.html', {'relato': relato})

@login_required
def adicionar_avaliacao(request):
    if request.method == 'POST':
        form = RelatoSocialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sua avaliação foi enviada com sucesso!')
            return redirect('dashboard:adicionar_avaliacao')
    else:
        form = RelatoSocialForm()
    return render(request, 'dashboard/adicionar.html', {'form': form})