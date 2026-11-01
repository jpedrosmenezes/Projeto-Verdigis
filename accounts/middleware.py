from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .models import Company, Papel, Vinculo

CHAVE_EMPRESA_ATIVA = 'empresa_ativa_id'


def resolver_contexto(request):
    """Define request.empresa, request.vinculo e request.capacidades para o usuário logado."""
    user = request.user
    if user.papel == Papel.EMPRESA:
        request.empresa = Company.objects.filter(responsavel=user).first()
        return

    if user.papel == Papel.FUNCIONARIO:
        vinculo = Vinculo.objects.select_related('company').filter(user=user).first()
    elif user.papel == Papel.CONSULTOR:
        # A empresa ativa vem da sessão, mas é revalidada a cada requisição:
        # se o vínculo deixou de existir, cai para o primeiro vínculo ou para nenhum.
        vinculos = list(Vinculo.objects.select_related('company').filter(user=user))
        ativo_id = request.session.get(CHAVE_EMPRESA_ATIVA)
        vinculo = next((v for v in vinculos if v.company_id == ativo_id), vinculos[0] if vinculos else None)
        if vinculo is None:
            request.session.pop(CHAVE_EMPRESA_ATIVA, None)
        elif ativo_id != vinculo.company_id:
            request.session[CHAVE_EMPRESA_ATIVA] = vinculo.company_id
        if vinculo is not None:
            request.capacidades = frozenset(vinculo.concessoes.values_list('capacidade', flat=True))
    else:
        return

    if vinculo is not None:
        request.vinculo = vinculo
        request.empresa = vinculo.company


class ContextoEmpresaMiddleware:
    """Coloca a empresa em que o usuário está atuando em toda requisição."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None
        request.vinculo = None
        request.capacidades = frozenset()
        if request.user.is_authenticated:
            resolver_contexto(request)
        return self.get_response(request)


# Rotas que quem ainda não escolheu o papel pode acessar.
ROTAS_LIVRES_ACCOUNTS = {
    'onboarding', 'onboarding_papel', 'logout', 'delete', 'buscar_cep',
}
ROTAS_LIVRES_SITE = {'index', 'sobre', 'fale_conosco'}
PREFIXOS_LIVRES = ('/static/', '/media/', '/admin/')


class TriagemObrigatoriaMiddleware:
    """Manda para a triagem quem está logado e ainda não escolheu o papel."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.papel and not user.is_superuser and not self._livre(request):
            return redirect('accounts:onboarding')
        return self.get_response(request)

    @staticmethod
    def _livre(request):
        if request.path_info.startswith(PREFIXOS_LIVRES):
            return True
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return True  # deixa o 404 acontecer normalmente
        if match.namespace == 'accounts':
            return match.url_name in ROTAS_LIVRES_ACCOUNTS
        return match.namespace == '' and match.url_name in ROTAS_LIVRES_SITE
