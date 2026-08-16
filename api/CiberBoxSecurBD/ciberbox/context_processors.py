def utilizador_atual(request):
    return {
        'utilizador_sessao': request.session.get('utilizador'),
    }
