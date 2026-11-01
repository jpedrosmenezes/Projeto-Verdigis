"""Autorização da aplicação: toda decisão de "pode ou não pode" passa por pode()."""
from dataclasses import dataclass
from functools import wraps
from typing import Callable

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Capacidade, Papel


@dataclass(frozen=True)
class Regra:
    empresa: bool = False
    funcionario: bool | Callable = False   # função (request, obj) -> bool para regras por dono
    consultor: bool = False                 # o consultor observador já pode?
    capacidade: str | None = None           # capacidade que libera a ação para o consultor


def _meta_visivel_para_funcionario(request, meta):
    """Funcionário vê as metas gerais e as individuais atribuídas a ele."""
    if meta is None:
        return True
    return meta.tipo == 'GERAL' or (request.vinculo is not None and meta.funcionario_id == request.vinculo.pk)


def _meta_criada_pelo_funcionario(request, meta):
    """Funcionário só altera ou apaga a meta que ele mesmo criou."""
    return meta is not None and meta.usuario_id == request.user.pk


def _funcionario_pode_criar_meta(request, meta):
    """Funcionário cria apenas meta individual para si (o formulário garante isso)."""
    return True


REGRAS = {
    'equipe.gerir': Regra(empresa=True),
    'empresa.apagar': Regra(empresa=True),

    'meta.ver': Regra(empresa=True, funcionario=_meta_visivel_para_funcionario, consultor=True),
    'meta.criar': Regra(empresa=True, funcionario=_funcionario_pode_criar_meta, capacidade=Capacidade.METAS_CRIAR),
    'meta.editar': Regra(empresa=True, funcionario=_meta_criada_pelo_funcionario, capacidade=Capacidade.METAS_EDITAR),
    'meta.concluir': Regra(
        empresa=True, funcionario=_meta_visivel_para_funcionario, capacidade=Capacidade.METAS_CONCLUIR,
    ),
    'meta.apagar': Regra(empresa=True, funcionario=_meta_criada_pelo_funcionario, capacidade=Capacidade.METAS_APAGAR),

    'relato.enviar': Regra(funcionario=True, consultor=True),
    'relato.ver_todos': Regra(empresa=True, consultor=True),
    'relato.moderar': Regra(empresa=True, capacidade=Capacidade.RELATOS_MODERAR),
}

# Ações que nunca podem ser liberadas a um consultor por capacidade.
ACOES_NAO_DELEGAVEIS = frozenset({'equipe.gerir', 'empresa.apagar', 'diagnostico.responder'})


def pode(request, acao, obj=None):
    """Fonte única de autorização. Ação desconhecida levanta KeyError."""
    regra = REGRAS[acao]
    if getattr(request, 'empresa', None) is None:
        return False
    papel = request.user.papel
    if papel == Papel.EMPRESA:
        return regra.empresa
    if papel == Papel.FUNCIONARIO:
        f = regra.funcionario
        return f(request, obj) if callable(f) else f
    if papel == Papel.CONSULTOR:
        return regra.consultor or (regra.capacidade is not None and regra.capacidade in request.capacidades)
    return False


def exigir(request, acao, obj=None):
    """Levanta 403 quando pode() nega a ação."""
    if not pode(request, acao, obj):
        raise PermissionDenied


def empresa_required(view):
    """Exige uma empresa no contexto; sem ela, volta ao dashboard (onde está o "Entre em uma empresa")."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(request, 'empresa', None) is None:
            messages.warning(request, 'Você precisa fazer parte de uma empresa para acessar esta página.')
            return redirect('dashboard:dashboard')
        return view(request, *args, **kwargs)
    return wrapper


def papel_required(*papeis):
    """Restringe a view aos papéis informados (403 para os demais)."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.papel not in papeis:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def acoes_permitidas(request):
    """Lista legível do que o usuário pode fazer na empresa atual (tela "Meus vínculos")."""
    rotulos = {
        'meta.ver': 'Ver metas',
        'meta.criar': 'Criar metas',
        'meta.editar': 'Editar metas',
        'meta.concluir': 'Concluir metas',
        'meta.apagar': 'Apagar metas',
        'relato.enviar': 'Enviar relatos',
        'relato.ver_todos': 'Ver todos os relatos da equipe',
        'relato.moderar': 'Moderar relatos',
    }
    if request.user.papel == Papel.FUNCIONARIO:
        # Para o funcionário as regras dependem do dono; mostramos o resumo do que vale.
        return [
            'Ver as metas gerais e as suas metas individuais',
            'Criar metas individuais para você',
            'Editar e apagar as metas que você criou',
            'Concluir as metas gerais e as suas',
            'Enviar relatos',
        ]
    return [rotulo for acao, rotulo in rotulos.items() if pode(request, acao)]
