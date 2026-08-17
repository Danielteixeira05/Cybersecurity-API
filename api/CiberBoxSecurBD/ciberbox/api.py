from __future__ import annotations

import json
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods

from . import basededados as bd


def _json_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _utilizador(request: HttpRequest) -> dict:
    return request.session.get('utilizador') or {}


def _ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


def _requer_autenticacao(view):
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not _utilizador(request):
            return JsonResponse({'erro': 'Autenticacao obrigatoria.'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _requer_perfil(*codigos: str):
    def decorator(view):
        @wraps(view)
        @_requer_autenticacao
        def wrapper(request: HttpRequest, *args, **kwargs):
            u = _utilizador(request)
            if u.get('perfil_codigo') not in codigos:
                return JsonResponse({'erro': 'Permissoes insuficientes.'}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def _cliente_scope(request: HttpRequest) -> int | None:
    u = _utilizador(request)
    if u.get('perfil_codigo') != 'CLIENTE':
        return None
    sessao_cliente_id = u.get('cliente_id')
    if sessao_cliente_id:
        return int(sessao_cliente_id)
    try:
        listar_fn = getattr(bd, 'listar_clientes_utilizador', None)
        if callable(listar_fn):
            clientes = listar_fn(u['id'])
        else:
            clientes = bd.listar_clientes(utilizador_id=u['id'], perfil_codigo='CLIENTE')
    except TypeError:
        clientes = bd.listar_clientes()
    if not clientes:
        return None
    return int(clientes[0]['id'])


def _map_perfil_role(p: str | None) -> str | None:
    if p == 'ADMINISTRADOR':
        return 'admin'
    if p == 'COLABORADOR':
        return 'manager'
    if p == 'CLIENTE':
        return 'cliente'
    return None


@require_http_methods(['GET'])
def csrf_view(request: HttpRequest) -> JsonResponse:
    token = get_token(request)
    return JsonResponse({'csrfToken': token})


@require_http_methods(['POST'])
def login_api(request: HttpRequest) -> JsonResponse:
    dados = _json_body(request)
    email = dados.get('email', '')
    password = dados.get('password', '')
    utilizador = bd.autenticar_utilizador(email, password)
    if not utilizador:
        return JsonResponse({'erro': 'Credenciais invalidas'}, status=401)
    request.session.cycle_key()
    request.session['utilizador'] = {
        'id': utilizador['id'],
        'nome': utilizador['nome'],
        'email': str(utilizador['email']),
        'perfil_codigo': utilizador['perfil_codigo'],
        'perfil_nome': utilizador['perfil_nome'],
    }
    bd.registar_log(utilizador['id'], 'LOGIN', 'sistema', detalhes={}, endereco_ip=_ip(request))
    cliente_detalhe = None
    scope = _cliente_scope(request)
    if scope:
        try:
            cliente_detalhe = bd.obter_cliente(scope)
        except Exception:
            cliente_detalhe = None
    return JsonResponse({
        'utilizador': request.session['utilizador'],
        'csrf_token': get_token(request),
        'cliente': cliente_detalhe,
    })


@require_http_methods(['POST'])
@_requer_autenticacao
def logout_api(request: HttpRequest) -> HttpResponse:
    u = _utilizador(request)
    try:
        bd.registar_log(u.get('id'), 'LOGOUT', 'sistema', endereco_ip=_ip(request))
    finally:
        request.session.flush()
    return HttpResponse(status=204)


@require_http_methods(['GET'])
def me_api(request: HttpRequest) -> JsonResponse:
    u = _utilizador(request)
    if not u:
        return JsonResponse({'autenticado': False, 'utilizador': None, 'cliente': None, 'role': None})
    utilizador_id = u.get('id')
    extra: dict[str, Any] = {}
    cliente_detalhe = None
    if utilizador_id:
        detalhe = bd.obter_utilizador(utilizador_id)
        if detalhe:
            extra = {
                'telefone': detalhe.get('telefone'),
                'nif': detalhe.get('nif'),
                'ativo': detalhe.get('ativo'),
                'cliente_id': detalhe.get('cliente_id'),
            }
            clientes = None
            listar_clientes_utilizador = getattr(bd, 'listar_clientes_utilizador', None)
            if callable(listar_clientes_utilizador):
                clientes = listar_clientes_utilizador(utilizador_id)
            else:
                try:
                    clientes = bd.listar_clientes(utilizador_id=utilizador_id)
                except TypeError:
                    try:
                        clientes = bd.listar_clientes(utilizador_id=utilizador_id, perfil_codigo=u.get('perfil_codigo'))
                    except TypeError:
                        clientes = None
            extra['clientes'] = clientes
            if extra.get('cliente_id'):
                try:
                    cliente_detalhe = bd.obter_cliente(int(extra['cliente_id']))
                except Exception:
                    cliente_detalhe = None
    utilizador_completo = {**u, **extra}
    role = _map_perfil_role(utilizador_completo.get('perfil_codigo'))
    utilizador_completo['role'] = role
    return JsonResponse({
        'autenticado': True,
        'utilizador': utilizador_completo,
        'cliente': cliente_detalhe,
        'role': role,
    })


@require_http_methods(['GET'])
@_requer_autenticacao
def dashboard_api(request: HttpRequest) -> JsonResponse:
    u = _utilizador(request)
    perfil = u.get('perfil_codigo')
    if perfil == 'CLIENTE':
        cliente_id = _cliente_scope(request)
        resumo = bd.obter_resumo_cliente(cliente_id) if cliente_id else {}
        return JsonResponse({'tipo': 'cliente', **resumo})
    return JsonResponse({'tipo': 'admin', **bd.obter_dashboard()})


@require_http_methods(['GET'])
@_requer_autenticacao
def clientes_api(request: HttpRequest) -> HttpResponse:
    u = _utilizador(request)
    perfil = u.get('perfil_codigo')
    q = request.GET.get('q')
    utilizador_id_param = request.GET.get('utilizador_id')
    scope_cliente = _cliente_scope(request)
    try:
        if scope_cliente is not None:
            clientes = bd.listar_clientes(utilizador_id=u['id'], perfil_codigo=perfil)
        elif utilizador_id_param:
            try:
                clientes = bd.listar_clientes(utilizador_id=int(utilizador_id_param))
            except TypeError:
                clientes = bd.listar_clientes()
        else:
            try:
                clientes = bd.listar_clientes(utilizador_id=u.get('id'), perfil_codigo=perfil)
            except TypeError:
                clientes = bd.listar_clientes()
    except TypeError:
        clientes = bd.listar_clientes()
    if scope_cliente is not None:
        clientes = [c for c in clientes if int(c.get('id')) == int(scope_cliente)]
    if q:
        ql = q.lower()
        clientes = [
            c for c in clientes
            if ql in str(c.get('nome', '')).lower()
            or ql in str(c.get('nif', '')).lower()
            or ql in str(c.get('email', '')).lower()
        ]
    return JsonResponse(clientes, safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def cliente_detalhe_api(request: HttpRequest, id: int) -> JsonResponse:
    u = _utilizador(request)
    scope = _cliente_scope(request)
    if scope is not None and int(scope) != int(id):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)
    if scope is None and not bd.utilizador_tem_acesso_cliente(u['id'], u['perfil_codigo'], id):
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)
    cliente = bd.obter_cliente(id)
    if not cliente:
        return JsonResponse({'erro': 'Cliente nao encontrado.'}, status=404)
    return JsonResponse({
        'cliente': cliente,
        'ativos': bd.listar_ativos(id),
        'incidentes': bd.listar_incidentes(id),
        'documentos': bd.listar_documentos(id),
        'avaliacoes': bd.listar_avaliacoes(id),
        'pedidos': bd.listar_pedidos(id),
        'contactos': bd.listar_contactos_cliente(id),
    })


@require_http_methods(['GET'])
@_requer_perfil('ADMINISTRADOR')
def utilizadores_api(request: HttpRequest) -> HttpResponse:
    perfil = request.GET.get('perfil')
    return JsonResponse(bd.listar_utilizadores(perfil), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def ativos_api(request: HttpRequest) -> HttpResponse:
    cliente_id = request.GET.get('cliente_id')
    scope = _cliente_scope(request)
    if scope is not None:
        cliente_id = str(scope)
    cid = int(cliente_id) if cliente_id else None
    return JsonResponse(bd.listar_ativos(cid), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def incidentes_api(request: HttpRequest) -> HttpResponse:
    cliente_id = request.GET.get('cliente_id')
    scope = _cliente_scope(request)
    if scope is not None:
        cliente_id = str(scope)
    cid = int(cliente_id) if cliente_id else None
    return JsonResponse(bd.listar_incidentes(cid), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def documentos_api(request: HttpRequest) -> HttpResponse:
    cliente_id = request.GET.get('cliente_id')
    scope = _cliente_scope(request)
    if scope is not None:
        cliente_id = str(scope)
    cid = int(cliente_id) if cliente_id else None
    return JsonResponse(bd.listar_documentos(cid), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def pedidos_api(request: HttpRequest) -> HttpResponse:
    cliente_id = request.GET.get('cliente_id')
    scope = _cliente_scope(request)
    if scope is not None:
        cliente_id = str(scope)
    cid = int(cliente_id) if cliente_id else None
    return JsonResponse(bd.listar_pedidos(cid), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def avaliacoes_api(request: HttpRequest) -> HttpResponse:
    cliente_id = request.GET.get('cliente_id')
    scope = _cliente_scope(request)
    if scope is not None:
        cliente_id = str(scope)
    cid = int(cliente_id) if cliente_id else None
    return JsonResponse(bd.listar_avaliacoes(cid), safe=False)


@require_http_methods(['GET'])
@_requer_perfil('ADMINISTRADOR')
def logs_api(request: HttpRequest) -> HttpResponse:
    limite = request.GET.get('limit', '50')
    try:
        limite = int(limite)
    except (ValueError, TypeError):
        limite = 50
    return JsonResponse(bd.listar_logs(limite), safe=False)


@require_http_methods(['GET'])
@_requer_autenticacao
def opcoes_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        'perfis': bd.listar_perfis(),
        'estados_conformidade': bd.listar_estados_conformidade(),
        'estados_pedidos': bd.listar_estados_pedidos(),
    })
