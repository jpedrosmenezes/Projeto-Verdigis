import requests
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from . import services
from .forms import (
    CompanyForm, ConfirmarSenhaForm, ConsultorOnboardingForm, EditCompanyForm, EditConsultorForm,
    EditProfileForm, EmailAuthenticationForm, EntrarEmpresaForm, FuncionarioOnboardingForm, SignupForm,
)
from .models import Company, Niche, Papel, SolicitacaoVinculo, Vinculo
from .permissions import acoes_permitidas, papel_required


def _dados_post(request):
    return request.POST if request.method == 'POST' else None


def _primeira_mensagem(erro):
    return erro.messages[0] if hasattr(erro, 'messages') else str(erro)


# ---------- Cadastro, login e senha ----------

def signup(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SignupForm(_dados_post(request))
    if form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error('email', 'Já existe uma conta cadastrada com este e-mail.')
        else:
            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Conta criada. Agora conte como você vai usar a plataforma.')
            return redirect('accounts:onboarding')

    return render(request, 'accounts/signup.html', {'form': form})


def login(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    next_url = request.POST.get('next') or request.GET.get('next', '')
    form = EmailAuthenticationForm(request, data=_dados_post(request))

    if form.is_valid():
        auth.login(request, form.get_user())
        seguro = url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                                 require_https=request.is_secure())
        return redirect(next_url if next_url and seguro else settings.LOGIN_REDIRECT_URL)

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@require_POST
def logout(request):
    auth.logout(request)
    messages.success(request, 'Você saiu da sua conta.')
    return redirect(settings.LOGOUT_REDIRECT_URL)


class TrocarSenhaView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Senha alterada com sucesso.')
        return super().form_valid(form)


# ---------- Triagem ----------

FORMULARIOS_ONBOARDING = {
    'empresa': (Papel.EMPRESA, CompanyForm),
    'funcionario': (Papel.FUNCIONARIO, FuncionarioOnboardingForm),
    'consultor': (Papel.CONSULTOR, ConsultorOnboardingForm),
}


@login_required
def onboarding(request):
    if request.user.papel:
        return redirect('dashboard:dashboard')
    return render(request, 'accounts/onboarding.html')


@login_required
def onboarding_papel(request, papel):
    if request.user.papel:
        messages.info(request, 'Você já escolheu como usa a plataforma.')
        return redirect('dashboard:dashboard')
    if papel not in FORMULARIOS_ONBOARDING:
        raise Http404
    valor_papel, form_class = FORMULARIOS_ONBOARDING[papel]
    kwargs = {} if papel == 'empresa' else {'user': request.user}
    form = form_class(_dados_post(request), **kwargs)

    if request.method == 'POST':
        if form.is_valid():
            try:
                services.concluir_onboarding(request.user, valor_papel, form)
            except ValidationError as erro:
                messages.error(request, _primeira_mensagem(erro))
                return redirect('dashboard:dashboard')
            except IntegrityError:
                messages.error(request, 'Não foi possível concluir o cadastro. Verifique os dados e tente novamente.')
            else:
                messages.success(request, 'Tudo pronto! Bem-vindo(a) à Verdigis.')
                return redirect('dashboard:dashboard')
        else:
            messages.warning(request, 'Corrija os campos destacados.')

    if papel == 'empresa':
        return render(request, 'accounts/company_form.html', {
            'form': form,
            'niche_info': {str(n.pk): n.descricao for n in Niche.objects.all()},
        })
    titulos = {'funcionario': 'SOU FUNCIONÁRIO', 'consultor': 'SOU CONSULTOR'}
    return render(request, 'accounts/onboarding_form.html', {'form': form, 'titulo': titulos[papel], 'papel': papel})


@login_required
@require_GET
def buscar_cep(request, cep):
    cep = ''.join(c for c in cep if c.isdigit())
    if len(cep) != 8:
        return JsonResponse({'erro': 'CEP inválido'}, status=400)
    try:
        data = requests.get(f'https://viacep.com.br/ws/{cep}/json/', timeout=5).json()
    except (requests.RequestException, ValueError):
        return JsonResponse({'erro': 'Serviço de CEP indisponível'}, status=502)
    if data.get('erro'):
        return JsonResponse({'erro': 'CEP não encontrado'}, status=404)
    return JsonResponse({
        'logradouro': data.get('logradouro', ''),
        'bairro': data.get('bairro', ''),
        'cidade': data.get('localidade', ''),
        'uf': data.get('uf', ''),
    })


# ---------- Vínculos (funcionário e consultor) ----------

@login_required
@papel_required(Papel.FUNCIONARIO, Papel.CONSULTOR)
def entrar_empresa(request):
    form = EntrarEmpresaForm(_dados_post(request))
    if request.method == 'POST' and form.is_valid():
        try:
            solicitacao = services.criar_solicitacao(request.user, **form.cleaned_data)
        except ValidationError as erro:
            form.add_error('codigo' if 'Código' in _primeira_mensagem(erro) else None, _primeira_mensagem(erro))
        except IntegrityError:
            form.add_error(None, 'Você já tem um pedido em análise para esta empresa.')
        else:
            messages.success(request, f'Pedido enviado para {solicitacao.company.nome_fantasia}. Aguarde a resposta.')
            return redirect('accounts:meus_vinculos')
    return render(request, 'accounts/entrar_empresa.html', {'form': form})


@login_required
@papel_required(Papel.FUNCIONARIO, Papel.CONSULTOR)
def meus_vinculos(request):
    vinculos = list(Vinculo.objects.filter(user=request.user).select_related('company'))
    pendentes = SolicitacaoVinculo.objects.filter(
        solicitante=request.user, status=SolicitacaoVinculo.Status.PENDENTE,
    ).select_related('company')
    return render(request, 'accounts/meus_vinculos.html', {
        'vinculos': vinculos,
        'pendentes': pendentes,
        'acoes': acoes_permitidas(request) if request.empresa else [],
        'pode_pedir': request.user.papel == Papel.CONSULTOR or not vinculos,
    })


@login_required
@require_POST
@papel_required(Papel.FUNCIONARIO, Papel.CONSULTOR)
def sair_empresa(request, vinculo_id):
    vinculo = get_object_or_404(Vinculo.objects.select_related('company__responsavel', 'user'),
                                id=vinculo_id, user=request.user)
    nome = vinculo.company.nome_fantasia
    services.encerrar_vinculo(vinculo)
    messages.success(request, f'Você saiu de {nome}.')
    return redirect('accounts:meus_vinculos')


@login_required
@require_POST
@papel_required(Papel.FUNCIONARIO, Papel.CONSULTOR)
def cancelar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoVinculo, id=solicitacao_id, solicitante=request.user)
    try:
        services.cancelar_solicitacao(solicitacao)
    except ValidationError as erro:
        messages.error(request, _primeira_mensagem(erro))
    else:
        messages.success(request, 'Pedido cancelado.')
    return redirect('accounts:meus_vinculos')


# ---------- Notificações ----------

@login_required
def notificacoes(request):
    return render(request, 'accounts/notificacoes.html', {
        'notificacoes': request.user.notificacoes.all()[:100],
    })


@login_required
def abrir_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(request.user.notificacoes, id=notificacao_id)
    if notificacao.lida_em is None:
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=['lida_em'])
    destino = notificacao.url
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect('accounts:notificacoes')


@login_required
@require_POST
def marcar_todas_lidas(request):
    request.user.notificacoes.filter(lida_em__isnull=True).update(lida_em=timezone.now())
    messages.success(request, 'Todas as notificações foram marcadas como lidas.')
    return redirect('accounts:notificacoes')


# ---------- Perfil ----------

@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'company': request.empresa if request.user.papel == Papel.EMPRESA else None,
        'vinculos': Vinculo.objects.filter(user=request.user).select_related('company'),
    })


@login_required
def edit_profile(request):
    user = request.user
    dados = _dados_post(request)
    form = EditProfileForm(dados, request.FILES or None, instance=user)

    company = Company.objects.filter(responsavel=user).first() if user.papel == Papel.EMPRESA else None
    company_form = EditCompanyForm(dados, instance=company, prefix='empresa') if company else None
    consultor_form = None
    if user.papel == Papel.CONSULTOR and hasattr(user, 'perfil_consultor'):
        consultor_form = EditConsultorForm(dados, instance=user.perfil_consultor, prefix='consultor')

    if request.method == 'POST':
        extras = [f for f in (company_form, consultor_form) if f is not None]
        validos = all([form.is_valid()] + [f.is_valid() for f in extras])
        if validos:
            with transaction.atomic():
                form.save()
                for f in extras:
                    f.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('accounts:profile')
        messages.warning(request, 'Corrija os campos destacados.')

    return render(request, 'accounts/edit_profile.html', {
        'form': form,
        'company_form': company_form,
        'consultor_form': consultor_form,
        'niche_info': {str(n.pk): n.descricao for n in Niche.objects.all()} if company_form else None,
    })


# ---------- Excluir conta ----------

@login_required
def delete(request):
    user = request.user
    company = Company.objects.filter(responsavel=user).first() if user.papel == Papel.EMPRESA else None
    form = ConfirmarSenhaForm(user, _dados_post(request), company=company)

    if request.method == 'POST' and form.is_valid():
        services.excluir_conta(user)
        auth.logout(request)
        messages.success(request, 'Sua conta foi excluída.')
        return redirect(settings.LOGOUT_REDIRECT_URL)

    return render(request, 'accounts/delete.html', {
        'form': form,
        'company': company,
        'vinculos': Vinculo.objects.filter(user=user).select_related('company'),
    })
