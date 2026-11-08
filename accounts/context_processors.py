def notificacoes(request):
    """Contagem de notificações não lidas para o sino do menu."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    return {'notificacoes_nao_lidas': user.notificacoes.filter(lida_em__isnull=True).count()}
