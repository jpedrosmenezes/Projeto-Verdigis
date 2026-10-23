import hashlib

import requests
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import DatabaseError, IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import get_user_model

from .forms import (
    CODIGO_CREDENCIAL_EMPRESA, CompanyForm, DeleteAccountForm, EditCompanyForm,
    EditProfileForm, EmployeeLoginForm, EmployeeSignupForm, LoginForm,
    ProfileForm, SignupForm, _normalizar_cnpj,
)
from .models import Company, Funcionario, Niche, UserProfile

User = get_user_model()

def _dados_post(request):
    return request.POST if request.method == 'POST' else None


def _salvar_cadastro(form):
    try:
        with transaction.atomic():
            return form.save()
    except IntegrityError:
        form.add_error(None, 'Não foi possível concluir o cadastro. Verifique os dados e tente novamente.')
        return None


def signup(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SignupForm(_dados_post(request))
    if form.is_valid():
        user = _salvar_cadastro(form)
        if user is not None:
            auth.login(request, user)
            messages.success(request, 'Conta criada com sucesso.')
            return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, 'accounts/signup.html', {'form': form})


def login(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    next_url = request.POST.get('next') or request.GET.get('next', '')
    form = LoginForm(request, data=_dados_post(request))

    if form.is_valid():
        user = form.get_user()
        auth.login(request, user)
        return redirect(next_url or settings.LOGIN_REDIRECT_URL)

    return render(
        request,
        'accounts/login.html',
        {'form': form, 'next': next_url}
    )

        user = request.user
        try:
            with transaction.atomic():
                empresas = Company.objects.filter(responsavel=user)
                funcionarios_ids = list(
                    Funcionario.objects.filter(company__in=empresas)
                    .exclude(user=user)
                    .values_list('user_id', flat=True)
                )
                # 1) apaga as contas dos funcionários (perfil e vínculo saem junto, em cascata);
                #    quem for responsável por outra empresa é preservado
                User.objects.filter(pk__in=funcionarios_ids, companies__isnull=True).delete()
                # 2) apaga a(s) empresa(s) do usuário
                empresas.delete()
                # 3) por fim, apaga o próprio usuário
                user.delete()
        except IntegrityError:
            messages.error(request, 'Não foi possível excluir a conta agora. Tente novamente.')
            return render(request, 'accounts/delete.html', {'form': form})
        auth.logout(request)
        messages.success(request, 'Sua conta foi excluída.')
        return redirect(settings.LOGOUT_REDIRECT_URL)




@require_POST
def logout(request):
    auth.logout(request)
    messages.success(request, 'Você saiu da sua conta.')
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required

@login_required
def delete(request):
    form = DeleteAccountForm(request.user, _dados_post(request))

    if request.method == 'POST' and form.is_valid():
        user = request.user

        try:
            with transaction.atomic():
                # 1. Busca as empresas do responsável.
                empresas = Company.objects.filter(responsavel=user)

                # 2. Encontra os funcionários dessas empresas.
                funcionarios_ids = list(
                    Funcionario.objects.filter(
                        company__in=empresas
                    ).values_list('user_id', flat=True)
                )

                # 3. Exclui as contas dos funcionários.
                User.objects.filter(pk__in=funcionarios_ids).delete()

                # 4. Exclui as empresas.
                empresas.delete()

                # 5. Exclui a conta do responsável.
                user.delete()

        except (IntegrityError, DatabaseError):
            messages.error(
                request,
                'Não foi possível excluir a conta agora. Tente novamente.'
            )
            return render(
                request,
                'accounts/delete.html',
                {'form': form}
            )

        # 6. Encerra a sessão do responsável.
        auth.logout(request)

        messages.success(
            request,
            'Sua conta e as contas dos funcionários vinculados '
            'à empresa foram excluídas.'
        )
        return redirect(settings.LOGOUT_REDIRECT_URL)

    return render(request, 'accounts/delete.html', {'form': form})

@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, 'Perfil atualizado com sucesso.')
        return redirect('profile')

    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def company_register(request):
    if Funcionario.objects.filter(user=request.user).exists():
        messages.error(request, 'Funcionários não podem cadastrar empresas.')
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = CompanyForm(_dados_post(request), user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            try:
                with transaction.atomic():
                    company = form.save(commit=False)
                    company.responsavel = request.user
                    company.save()
                    
                    # Alterado 'tipo': 'empresa' para 'tipo': 'EMPRESA' (caixa alta)
                    # para ficar compatível com o TIPO_CHOICES no models.py.
                    UserProfile.objects.update_or_create(
                        user=request.user,
                        defaults={'tipo': 'EMPRESA', 'nome_empresa': company.nome_fantasia},
                    )
                return redirect('company_success')
            except DatabaseError:
                messages.error(request, 'Não foi possível concluir o cadastro. Tente novamente.')
        else:
            messages.warning(request, 'Corrija os campos destacados.')

    niche_info = {str(n.pk): n.description for n in Niche.objects.all()}
    return render(request, 'accounts/company_form.html', {'form': form, 'niche_info': niche_info})


@login_required
def company_success(request):
    return render(request, 'accounts/company_success.html')


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


# ---------- Funcionários ----------

LIMITE_TENTATIVAS = 5
JANELA_TENTATIVAS = 15 * 60


def _chave_tentativas(request, escopo):
    cnpj = _normalizar_cnpj(request.POST.get('cnpj'))
    if not cnpj:
        return None
    return f"tentativas:{escopo}:{hashlib.sha256(cnpj.encode()).hexdigest()}"


def _bloqueado(request, escopo):
    chave = _chave_tentativas(request, escopo)
    return chave is not None and cache.get(chave, 0) >= LIMITE_TENTATIVAS


def _registrar_falha(request, escopo, form):
    chave = _chave_tentativas(request, escopo)
    if chave is None:
        return
    # verifica erros no formulário
    if not form.errors:
        return
    cache.add(chave, 0, JANELA_TENTATIVAS)
    try:
        cache.incr(chave)
    except ValueError:
        cache.set(chave, 1, JANELA_TENTATIVAS)


def signup_funcionario(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    contexto = {
        'titulo': 'Cadastro de funcionário',
        'subtitulo': 'Use o CNPJ e a senha de acesso que a sua empresa forneceu.',
        'botao': 'Criar conta',
        'alt_url': 'login_funcionario',
        'alt_texto': 'Já tenho conta de funcionário',
    }

    if request.method == 'POST' and _bloqueado(request, 'func_signup'):
        messages.error(request, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.')
        return render(
            request, 'accounts/funcionario_form.html',
            {**contexto, 'form': EmployeeSignupForm()}, status=429,
        )

    form = EmployeeSignupForm(_dados_post(request))
    if form.is_valid():
        user = _salvar_cadastro(form)
        if user is not None:
            auth.login(request, user)
            messages.success(request, 'Conta de funcionário criada com sucesso.')
            return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        _registrar_falha(request, 'func_signup', form)
    return render(request, 'accounts/funcionario_form.html', {**contexto, 'form': form})


def login_funcionario(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    contexto = {
        'titulo': 'Entrar como funcionário',
        'subtitulo': 'Informe seu usuário, sua senha e os dados de acesso da empresa.',
        'botao': 'Entrar',
        'alt_url': 'signup_funcionario',
        'alt_texto': 'Criar conta de funcionário',
    }

    if request.method == 'POST' and _bloqueado(request, 'func_login'):
        messages.error(request, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.')
        return render(
            request, 'accounts/funcionario_form.html',
            {**contexto, 'form': EmployeeLoginForm(request)}, status=429,
        )

    form = EmployeeLoginForm(request, data=_dados_post(request))
    if form.is_valid():
        auth.login(request, form.get_user())
        messages.success(request, 'Login realizado com sucesso.')
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        _registrar_falha(request, 'func_login', form)
    return render(request, 'accounts/funcionario_form.html', {**contexto, 'form': form})

@login_required
def edit_profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    company = request.user.companies.first()  # só responsáveis têm empresa

    dados = _dados_post(request)
    form = EditProfileForm(dados, request.FILES or None, instance=profile_obj, user=request.user)
    company_form = (
        EditCompanyForm(dados, instance=company, prefix='empresa') if company else None
    )

    if request.method == 'POST':
        validos = form.is_valid()
        if company_form is not None:
            validos = company_form.is_valid() and validos

        if validos:
            with transaction.atomic():
                form.save()
                if company_form is not None:
                    company = company_form.save()
                    UserProfile.objects.filter(pk=profile_obj.pk).update(
                        nome_empresa=company.nome_fantasia
                    )
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('profile')
        messages.warning(request, 'Corrija os campos destacados.')

    return render(request, 'accounts/edit_profile.html', {
        'form': form,
        'company_form': company_form,
    })