from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from accounts.models import Company, Funcionario
from verdigis import settings
from .forms import FormsMetas, RelatoSocialForm
from .models import Meta, RelatoSocialVerdigis
from functools import wraps



def _obter_empresa_usuario(user):
    company = Company.objects.filter(responsavel = user).first()
    if not company and hasattr(user, 'FUNCIONARIO'):
        company = user.FUNCIONARIO.company
    return company

def gestor_required(view):
    """Só o responsável por uma empresa passa. Os demais voltam ao dashboard com aviso."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        company = _obter_empresa_usuario(request.user)
        if company is None or hasattr(request.user, 'FUNCIONARIO'):
            messages.error(request, 'Apenas o responsável pela empresa pode ver os relatos.')
            return redirect('dashboard:dashboard')
        request.company = company
        return view(request, *args, **kwargs)
    return wrapper

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

    # Filtra a lista de acordo com o tipo de usuário
    if hasattr(request.user, 'FUNCIONARIO'): # Verifica se é funcionário ou gestor
        metas = Meta.objects.filter(
            company=company
        ).filter(
            Q(tipo='GERAL') | Q(funcionario=request.user.FUNCIONARIO)
        ).order_by('completo', 'deadline')
    else:
        metas = Meta.objects.filter(company=company).order_by('completo', 'deadline')

    if request.method == 'POST':
        # Passa request.POST e nomeia company=company
        form = FormsMetas(request.POST, company=company)
        if form.is_valid():
            meta = form.save(commit=False)
            meta.company = company
            meta.usuario = request.user
            meta.save()
            return redirect('dashboard:fabrica_metas')
    else:
        # Passa apenas o argumento nomeado company=company
        form = FormsMetas(company=company)

    return render(request, 'dashboard/fabrica_metas.html', {
        'metas': metas,
        'form': form,
        'hoje': timezone.localdate(),
    })



@login_required
def editar_meta_view(request, meta_id):
    company = _obter_empresa_usuario(request.user)
    
    # 1. Busca a meta garantindo o ID e a empresa do usuário
    meta = get_object_or_404(Meta, id=meta_id, company=company)

    if request.method == 'POST':
        # 2. Instancia o formulário passando request.POST, instance e company de forma nomeada
        form = FormsMetas(request.POST, instance=meta, company=company)
        
        if form.is_valid():
            form.save()
            return redirect('dashboard:fabrica_metas')
    else:
        # No GET, carrega os dados atuais da meta no formulário
        form = FormsMetas(instance=meta, company=company)

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
@gestor_required
def dashboard_social_verdigis(request):
    base = RelatoSocialVerdigis.objects.filter(company=request.company)
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
@gestor_required
def detalhe_relato_view(request, relato_id):
    relato = RelatoSocialVerdigis.objects.filter(id=relato_id, company=request.company).first()
    if relato is None:
        messages.error(request, 'Relato não encontrado.')
        return redirect('dashboard:dashboard_social')
    return render(request, 'dashboard/avaliacao_detalhe.html', {'relato': relato})  

@login_required
def adicionar_avaliacao(request):
    company = _obter_empresa_usuario(request.user)
    if not company:
        messages.error(request, 'Você precisa estar vinculado a uma empresa para enviar avaliações.')
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = RelatoSocialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sua avaliação foi enviada com sucesso!')
            return redirect('dashboard:adicionar_avaliacao')
    else:
        form = RelatoSocialForm()
    return render(request, 'dashboard/adicionar.html', {'form': form})

@login_required
def adicionar_avaliacao(request):
    company = _obter_empresa_usuario(request.user)
    if not company:
        messages.error(request, 'Você precisa estar vinculado a uma empresa para enviar avaliações.')
        return redirect(settings.LOGIN_REDIRECT_URL)  # importe settings

    if request.method == 'POST':
        form = RelatoSocialForm(request.POST, user=request.user, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sua avaliação foi enviada com sucesso!')
            return redirect('dashboard:adicionar_avaliacao')
    else:
        form = RelatoSocialForm(user=request.user, company=company)
    return render(request, 'dashboard/adicionar.html', {'form': form})


@login_required
def funcionarios_view(request):
    company = _obter_empresa_usuario(request.user)

    # Só o responsável pela empresa vê a lista (funcionário e usuário sem empresa voltam ao dashboard)
    if company is None or hasattr(request.user, 'FUNCIONARIO'):
        messages.error(request, 'Apenas o responsável pela empresa pode ver os funcionários.')
        return redirect('dashboard:dashboard')

    funcionarios = (
        Funcionario.objects
        .filter(company=company)
        .select_related('user', 'user__profile')
        .order_by('user__username')
    )
    return render(request, 'dashboard/funcionarios.html', {
        'company': company,
        'funcionarios': funcionarios,
    })