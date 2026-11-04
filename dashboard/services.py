"""Regras de metas e relatos que alteram dados ou decidem o que cada papel vê."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Papel, Vinculo
from accounts.permissions import pode

from .models import Meta, RelatoSocialVerdigis


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
