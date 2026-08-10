from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def login_obrigatorio(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('utilizador'):
            messages.warning(request, 'Inicie sessao para aceder a esta area.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def perfis_permitidos(*codigos):
    def decorator(view_func):
        @wraps(view_func)
        @login_obrigatorio
        def wrapper(request, *args, **kwargs):
            utilizador = request.session.get('utilizador') or {}
            if utilizador.get('perfil_codigo') not in codigos:
                messages.error(request, 'Nao tem permissao para executar esta operacao.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
