from __future__ import annotations

from pathlib import Path
import logging
import os

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import basededados as bd
from .decorators import login_obrigatorio, perfis_permitidos
from .excel_import import (
    analisar_excel,
    apagar_preview,
    carregar_preview,
    guardar_preview,
    guardar_upload_excel,
)
from .forms import (
    AlterarEstadoPedidoForm,
    AtivoForm,
    AvaliacaoRiscoForm,
    ClienteForm,
    ContactoClienteForm,
    DocumentoForm,
    ImportarExcelForm,
    IncidenteForm,
    LoginForm,
    MensagemPedidoForm,
    PedidoForm,
    UtilizadorForm,
)
from .storage import caminho_privado, guardar_documento

logger = logging.getLogger(__name__)


def _utilizador(request: HttpRequest) -> dict:
    return request.session.get('utilizador') or {}


def _ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


def _clientes_visiveis(request: HttpRequest, apenas_ativos: bool = False) -> list[dict]:
    u = _utilizador(request)
    return bd.listar_clientes(u.get('id'), u.get('perfil_codigo'), apenas_ativos)


def _cliente_fixo(request: HttpRequest) -> int | None:
    u = _utilizador(request)
    if u.get('perfil_codigo') != 'CLIENTE':
        return None
    clientes = _clientes_visiveis(request)
    return clientes[0]['id'] if clientes else None


def _exigir_acesso_cliente(request: HttpRequest, cliente_id: int) -> None:
    u = _utilizador(request)
    if not bd.utilizador_tem_acesso_cliente(u['id'], u['perfil_codigo'], cliente_id):
        raise Http404('Cliente nao encontrado.')


def _erro_base_dados(request: HttpRequest, exc: Exception, mensagem: str = 'Nao foi possivel concluir a operacao.'):
    # O detalhe técnico fica apenas nos logs; o utilizador recebe uma mensagem genérica.
    logger.exception('Erro de base de dados durante pedido %s %s', request.method, request.path, exc_info=exc)
    messages.error(request, mensagem)


@require_http_methods(['GET', 'POST'])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.session.get('utilizador'):
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            utilizador = bd.autenticar_utilizador(form.cleaned_data['email'], form.cleaned_data['password'])
        except DatabaseError:
            utilizador = None
            messages.error(request, 'Nao foi possivel ligar a base de dados. Verifique o ficheiro .env.')
        if utilizador:
            request.session.cycle_key()
            request.session['utilizador'] = {
                'id': utilizador['id'],
                'nome': utilizador['nome'],
                'email': str(utilizador['email']),
                'perfil_codigo': utilizador['perfil_codigo'],
                'perfil_nome': utilizador['perfil_nome'],
            }
            bd.registar_log(utilizador['id'], 'LOGIN', 'sistema', detalhes={}, endereco_ip=_ip(request))
            return redirect('dashboard')
        messages.error(request, 'Email ou password incorretos, ou conta desativada.')
    return render(request, 'ciberbox/login.html', {'form': form})


@login_obrigatorio
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    u = _utilizador(request)
    try:
        bd.registar_log(u.get('id'), 'LOGOUT', 'sistema', endereco_ip=_ip(request))
    finally:
        request.session.flush()
    return redirect('login')


@login_obrigatorio
def dashboard(request: HttpRequest) -> HttpResponse:
    u = _utilizador(request)
    if u['perfil_codigo'] == 'CLIENTE':
        cliente_id = _cliente_fixo(request)
        resumo = bd.obter_resumo_cliente(cliente_id) if cliente_id else {}
        return render(request, 'ciberbox/dashboard_cliente.html', {'resumo': resumo})
    return render(request, 'ciberbox/dashboard.html', bd.obter_dashboard())


# ---------------------------------------------------------------------------
# Clientes e contactos
# ---------------------------------------------------------------------------
@login_obrigatorio
def clientes_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/clientes_lista.html', {'clientes': _clientes_visiveis(request)})


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_http_methods(['GET', 'POST'])
def cliente_criar(request: HttpRequest) -> HttpResponse:
    form = ClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            cliente_id = bd.criar_cliente(form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Cliente criado com sucesso.')
            return redirect('cliente_detalhe', cliente_id=cliente_id)
        except IntegrityError as exc:
            _erro_base_dados(request, exc, 'Ja existe um cliente com o mesmo NIF ou os dados sao invalidos.')
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo cliente'})


@login_obrigatorio
def cliente_detalhe(request: HttpRequest, cliente_id: int) -> HttpResponse:
    _exigir_acesso_cliente(request, cliente_id)
    cliente = bd.obter_cliente(cliente_id)
    if not cliente:
        raise Http404
    contexto = {
        'cliente': cliente,
        'contactos': bd.listar_contactos_cliente(cliente_id),
        'ativos': bd.listar_ativos(cliente_id)[:10],
        'incidentes': bd.listar_incidentes(cliente_id)[:10],
        'documentos': bd.listar_documentos(cliente_id)[:10],
        'avaliacoes': bd.listar_avaliacoes(cliente_id)[:5],
        'pedidos': bd.listar_pedidos(cliente_id)[:10],
    }
    return render(request, 'ciberbox/cliente_detalhe.html', contexto)


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_http_methods(['GET', 'POST'])
def cliente_editar(request: HttpRequest, cliente_id: int) -> HttpResponse:
    cliente = bd.obter_cliente(cliente_id)
    if not cliente:
        raise Http404
    form = ClienteForm(request.POST or None, initial=cliente)
    if request.method == 'POST' and form.is_valid():
        try:
            bd.atualizar_cliente(cliente_id, form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Cliente atualizado.')
            return redirect('cliente_detalhe', cliente_id=cliente_id)
        except IntegrityError as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Editar cliente'})


@perfis_permitidos('ADMINISTRADOR')
@require_POST
def cliente_alterar_estado(request: HttpRequest, cliente_id: int) -> HttpResponse:
    cliente = bd.obter_cliente(cliente_id)
    if not cliente:
        raise Http404
    bd.alterar_estado_cliente(cliente_id, not cliente['ativo'], _utilizador(request)['id'])
    messages.success(request, 'Estado do cliente alterado.')
    return redirect('clientes_lista')


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_http_methods(['GET', 'POST'])
def contacto_criar(request: HttpRequest, cliente_id: int) -> HttpResponse:
    if not bd.obter_cliente(cliente_id):
        raise Http404
    form = ContactoClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            bd.criar_contacto_cliente(cliente_id, form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Contacto adicionado.')
            return redirect('cliente_detalhe', cliente_id=cliente_id)
        except IntegrityError as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo contacto'})


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_POST
def contacto_eliminar(request: HttpRequest, contacto_id: int) -> HttpResponse:
    contacto = bd.obter_contacto_cliente(contacto_id)
    if not contacto:
        raise Http404
    bd.eliminar_contacto_cliente(contacto_id, _utilizador(request)['id'])
    messages.success(request, 'Contacto removido.')
    return redirect('cliente_detalhe', cliente_id=contacto['cliente_id'])


# ---------------------------------------------------------------------------
# Utilizadores
# ---------------------------------------------------------------------------
@perfis_permitidos('ADMINISTRADOR')
def utilizadores_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/utilizadores_lista.html', {'utilizadores': bd.listar_utilizadores()})


@perfis_permitidos('ADMINISTRADOR')
@require_http_methods(['GET', 'POST'])
def utilizador_criar(request: HttpRequest) -> HttpResponse:
    clientes = bd.listar_clientes(apenas_ativos=True)
    form = UtilizadorForm(request.POST or None, clientes=clientes)
    if request.method == 'POST' and form.is_valid():
        try:
            bd.criar_utilizador(form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Utilizador criado.')
            return redirect('utilizadores_lista')
        except IntegrityError as exc:
            _erro_base_dados(request, exc, 'O email ou NIF ja esta em utilizacao.')
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo utilizador'})


@perfis_permitidos('ADMINISTRADOR')
@require_http_methods(['GET', 'POST'])
def utilizador_editar(request: HttpRequest, utilizador_id: int) -> HttpResponse:
    utilizador = bd.obter_utilizador(utilizador_id)
    if not utilizador:
        raise Http404
    clientes = bd.listar_clientes(apenas_ativos=True)
    initial = dict(utilizador)
    initial['id'] = utilizador_id
    form = UtilizadorForm(request.POST or None, initial=initial, clientes=clientes)
    if request.method == 'POST' and form.is_valid():
        try:
            bd.atualizar_utilizador(utilizador_id, form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Utilizador atualizado.')
            return redirect('utilizadores_lista')
        except IntegrityError as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Editar utilizador'})


@perfis_permitidos('ADMINISTRADOR')
@require_POST
def utilizador_alterar_estado(request: HttpRequest, utilizador_id: int) -> HttpResponse:
    utilizador = bd.obter_utilizador(utilizador_id)
    if not utilizador:
        raise Http404
    if utilizador_id == _utilizador(request)['id']:
        messages.error(request, 'Nao pode desativar a sua propria conta.')
    else:
        bd.alterar_estado_utilizador(utilizador_id, not utilizador['ativo'], _utilizador(request)['id'])
        messages.success(request, 'Estado do utilizador alterado.')
    return redirect('utilizadores_lista')


# ---------------------------------------------------------------------------
# Ativos
# ---------------------------------------------------------------------------
@login_obrigatorio
def ativos_lista(request: HttpRequest) -> HttpResponse:
    cliente_id = _cliente_fixo(request)
    return render(request, 'ciberbox/ativos_lista.html', {'ativos': bd.listar_ativos(cliente_id)})


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def ativo_criar(request: HttpRequest) -> HttpResponse:
    clientes = _clientes_visiveis(request, apenas_ativos=True)
    cliente_fixo = _cliente_fixo(request)
    form = AtivoForm(request.POST or None, clientes=clientes, cliente_fixo=cliente_fixo)
    if request.method == 'POST' and form.is_valid():
        cliente_id = int(form.cleaned_data['cliente_id'])
        _exigir_acesso_cliente(request, cliente_id)
        try:
            bd.criar_ativo(form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Ativo registado.')
            return redirect('ativos_lista')
        except (IntegrityError, DatabaseError) as exc:
            _erro_base_dados(request, exc, 'Nao foi possivel registar o ativo. Verifique inventario, IP e MAC.')
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo ativo tecnologico'})


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def ativo_editar(request: HttpRequest, ativo_id: int) -> HttpResponse:
    ativo = bd.obter_ativo(ativo_id)
    if not ativo:
        raise Http404
    _exigir_acesso_cliente(request, ativo['cliente_id'])
    form = AtivoForm(request.POST or None, initial=ativo, clientes=_clientes_visiveis(request),
                     cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        try:
            bd.atualizar_ativo(ativo_id, form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Ativo atualizado.')
            return redirect('ativos_lista')
        except (IntegrityError, DatabaseError) as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Editar ativo'})


@login_obrigatorio
@require_POST
def ativo_eliminar(request: HttpRequest, ativo_id: int) -> HttpResponse:
    ativo = bd.obter_ativo(ativo_id)
    if not ativo:
        raise Http404
    _exigir_acesso_cliente(request, ativo['cliente_id'])
    bd.eliminar_ativo(ativo_id, _utilizador(request)['id'])
    messages.success(request, 'Ativo eliminado.')
    return redirect('ativos_lista')


# ---------------------------------------------------------------------------
# Incidentes
# ---------------------------------------------------------------------------
@login_obrigatorio
def incidentes_lista(request: HttpRequest) -> HttpResponse:
    cliente_id = _cliente_fixo(request)
    return render(request, 'ciberbox/incidentes_lista.html', {'incidentes': bd.listar_incidentes(cliente_id)})


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def incidente_criar(request: HttpRequest) -> HttpResponse:
    form = IncidenteForm(request.POST or None, clientes=_clientes_visiveis(request, True),
                         cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        _exigir_acesso_cliente(request, int(form.cleaned_data['cliente_id']))
        try:
            bd.criar_incidente(form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Incidente registado.')
            return redirect('incidentes_lista')
        except (IntegrityError, DatabaseError) as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo incidente'})


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def incidente_editar(request: HttpRequest, incidente_id: int) -> HttpResponse:
    incidente = bd.obter_incidente(incidente_id)
    if not incidente:
        raise Http404
    _exigir_acesso_cliente(request, incidente['cliente_id'])
    form = IncidenteForm(request.POST or None, initial=incidente,
                         clientes=_clientes_visiveis(request), cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        try:
            bd.atualizar_incidente(incidente_id, form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Incidente atualizado.')
            return redirect('incidentes_lista')
        except (IntegrityError, DatabaseError) as exc:
            _erro_base_dados(request, exc)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Editar incidente'})


@login_obrigatorio
@require_POST
def incidente_eliminar(request: HttpRequest, incidente_id: int) -> HttpResponse:
    incidente = bd.obter_incidente(incidente_id)
    if not incidente:
        raise Http404
    _exigir_acesso_cliente(request, incidente['cliente_id'])
    bd.eliminar_incidente(incidente_id, _utilizador(request)['id'])
    messages.success(request, 'Incidente eliminado.')
    return redirect('incidentes_lista')


# ---------------------------------------------------------------------------
# Avaliacoes
# ---------------------------------------------------------------------------
@login_obrigatorio
def avaliacoes_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/avaliacoes_lista.html', {
        'avaliacoes': bd.listar_avaliacoes(_cliente_fixo(request))
    })


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_http_methods(['GET', 'POST'])
def avaliacao_criar(request: HttpRequest) -> HttpResponse:
    form = AvaliacaoRiscoForm(request.POST or None, clientes=bd.listar_clientes(apenas_ativos=True),
                              estados=bd.listar_estados_conformidade())
    if request.method == 'POST' and form.is_valid():
        try:
            bd.criar_avaliacao(form.cleaned_data, _utilizador(request)['id'])
            messages.success(request, 'Avaliacao registada.')
            return redirect('avaliacoes_lista')
        except IntegrityError as exc:
            _erro_base_dados(request, exc, 'Ja existe uma avaliacao desse cliente na mesma data.')
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Nova avaliacao de risco'})


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_POST
def avaliacao_eliminar(request: HttpRequest, avaliacao_id: int) -> HttpResponse:
    bd.eliminar_avaliacao(avaliacao_id, _utilizador(request)['id'])
    messages.success(request, 'Avaliacao eliminada.')
    return redirect('avaliacoes_lista')


# ---------------------------------------------------------------------------
# Documentos privados
# ---------------------------------------------------------------------------
@login_obrigatorio
def documentos_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/documentos_lista.html', {
        'documentos': bd.listar_documentos(_cliente_fixo(request))
    })


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def documento_criar(request: HttpRequest) -> HttpResponse:
    form = DocumentoForm(request.POST or None, request.FILES or None,
                         clientes=_clientes_visiveis(request, True), cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        cliente_id = int(form.cleaned_data['cliente_id'])
        _exigir_acesso_cliente(request, cliente_id)
        meta = guardar_documento(form.cleaned_data['ficheiro'])
        dados = {**form.cleaned_data, **meta, 'cliente_id': cliente_id, 'privado': True}
        try:
            bd.criar_documento(dados, _utilizador(request)['id'])
            messages.success(request, 'Documento submetido.')
            return redirect('documentos_lista')
        except Exception:
            caminho_privado(meta['caminho_ficheiro']).unlink(missing_ok=True)
            raise
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Submeter documento', 'multipart': True})


@login_obrigatorio
def documento_download(request: HttpRequest, documento_id: int) -> HttpResponse:
    documento = bd.obter_documento(documento_id)
    if not documento:
        raise Http404
    _exigir_acesso_cliente(request, documento['cliente_id'])
    caminho = caminho_privado(documento['caminho_ficheiro'])
    if not caminho.exists():
        raise Http404('O ficheiro de demonstracao nao existe no disco.')
    bd.registar_log(_utilizador(request)['id'], 'DOWNLOAD', 'documentos', documento_id,
                    endereco_ip=_ip(request))
    return FileResponse(caminho.open('rb'), as_attachment=True,
                        filename=documento['nome_ficheiro_original'], content_type=documento['tipo_mime'])


@login_obrigatorio
@require_POST
def documento_eliminar(request: HttpRequest, documento_id: int) -> HttpResponse:
    documento = bd.obter_documento(documento_id)
    if not documento:
        raise Http404
    _exigir_acesso_cliente(request, documento['cliente_id'])
    removido = bd.eliminar_documento(documento_id, _utilizador(request)['id'])
    if removido:
        caminho_privado(removido['caminho_ficheiro']).unlink(missing_ok=True)
    messages.success(request, 'Documento eliminado.')
    return redirect('documentos_lista')


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------
@login_obrigatorio
def pedidos_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/pedidos_lista.html', {
        'pedidos': bd.listar_pedidos(_cliente_fixo(request))
    })


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def pedido_criar(request: HttpRequest) -> HttpResponse:
    form = PedidoForm(request.POST or None, clientes=_clientes_visiveis(request, True),
                      cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        _exigir_acesso_cliente(request, int(form.cleaned_data['cliente_id']))
        pedido_id = bd.criar_pedido(form.cleaned_data, _utilizador(request)['id'])
        messages.success(request, 'Pedido criado.')
        return redirect('pedido_detalhe', pedido_id=pedido_id)
    return render(request, 'ciberbox/form.html', {'form': form, 'titulo': 'Novo pedido'})


@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def pedido_detalhe(request: HttpRequest, pedido_id: int) -> HttpResponse:
    pedido = bd.obter_pedido(pedido_id)
    if not pedido:
        raise Http404
    _exigir_acesso_cliente(request, pedido['cliente_id'])
    mensagem_form = MensagemPedidoForm(request.POST or None)
    if request.method == 'POST' and 'adicionar_mensagem' in request.POST and mensagem_form.is_valid():
        bd.criar_mensagem_pedido(pedido_id, _utilizador(request)['id'], mensagem_form.cleaned_data['mensagem'])
        messages.success(request, 'Mensagem adicionada.')
        return redirect('pedido_detalhe', pedido_id=pedido_id)
    estado_form = None
    if _utilizador(request)['perfil_codigo'] in ('ADMINISTRADOR', 'COLABORADOR'):
        estado_form = AlterarEstadoPedidoForm(estados=bd.listar_estados_pedidos(),
                                              colaboradores=bd.listar_utilizadores('COLABORADOR'))
    return render(request, 'ciberbox/pedido_detalhe.html', {
        'pedido': pedido,
        'mensagens_pedido': bd.listar_mensagens_pedido(pedido_id),
        'historico': bd.listar_historico_pedido(pedido_id),
        'mensagem_form': mensagem_form,
        'estado_form': estado_form,
    })


@perfis_permitidos('ADMINISTRADOR', 'COLABORADOR')
@require_POST
def pedido_alterar_estado(request: HttpRequest, pedido_id: int) -> HttpResponse:
    pedido = bd.obter_pedido(pedido_id)
    if not pedido:
        raise Http404
    form = AlterarEstadoPedidoForm(request.POST, estados=bd.listar_estados_pedidos(),
                                   colaboradores=bd.listar_utilizadores('COLABORADOR'))
    if form.is_valid():
        bd.alterar_estado_pedido(
            pedido_id,
            int(form.cleaned_data['estado_id']),
            _utilizador(request)['id'],
            form.cleaned_data.get('observacao'),
            int(form.cleaned_data['atribuido_a']) if form.cleaned_data.get('atribuido_a') else None,
        )
        messages.success(request, 'Estado do pedido atualizado.')
    else:
        messages.error(request, 'Dados de alteracao de estado invalidos.')
    return redirect('pedido_detalhe', pedido_id=pedido_id)


# ---------------------------------------------------------------------------
# Importacao Excel com pre-visualizacao e relatorio
# ---------------------------------------------------------------------------
@login_obrigatorio
@require_http_methods(['GET', 'POST'])
def importacao_excel(request: HttpRequest) -> HttpResponse:
    form = ImportarExcelForm(request.POST or None, request.FILES or None,
                             clientes=_clientes_visiveis(request, True), cliente_fixo=_cliente_fixo(request))
    if request.method == 'POST' and form.is_valid():
        cliente_id = int(form.cleaned_data['cliente_id'])
        _exigir_acesso_cliente(request, cliente_id)
        nome_original, caminho_relativo = guardar_upload_excel(form.cleaned_data['ficheiro'])
        caminho_absoluto = caminho_privado(caminho_relativo)
        try:
            analise = analisar_excel(caminho_absoluto, form.cleaned_data['tipo'])
        except Exception as exc:
            caminho_absoluto.unlink(missing_ok=True)
            messages.error(request, f'Nao foi possivel analisar o Excel: {exc}')
        else:
            conteudo = {
                **analise,
                'cliente_id': cliente_id,
                'cliente_nome': bd.obter_cliente(cliente_id)['nome'],
                'nome_ficheiro_original': nome_original,
                'caminho_ficheiro': caminho_relativo,
            }
            token = guardar_preview(conteudo)
            request.session['preview_importacao_token'] = token
            return redirect('importacao_preview', token=token)
    return render(request, 'ciberbox/importacao_form.html', {
        'form': form,
        'importacoes': bd.listar_importacoes(_cliente_fixo(request)),
    })


@login_obrigatorio
def importacao_preview(request: HttpRequest, token: str) -> HttpResponse:
    if request.session.get('preview_importacao_token') != token:
        raise Http404
    preview = carregar_preview(token)
    _exigir_acesso_cliente(request, int(preview['cliente_id']))
    return render(request, 'ciberbox/importacao_preview.html', {'preview': preview, 'token': token})


@login_obrigatorio
@require_POST
def importacao_confirmar(request: HttpRequest, token: str) -> HttpResponse:
    if request.session.get('preview_importacao_token') != token:
        raise Http404
    preview = carregar_preview(token)
    _exigir_acesso_cliente(request, int(preview['cliente_id']))
    try:
        resultado = bd.processar_importacao(
            cliente_id=int(preview['cliente_id']),
            tipo=preview['tipo'],
            nome_ficheiro_original=preview['nome_ficheiro_original'],
            caminho_ficheiro=preview['caminho_ficheiro'],
            linhas=preview['linhas'],
            utilizador_id=_utilizador(request)['id'],
        )
    except Exception as exc:
        _erro_base_dados(request, exc, 'A importacao nao foi concluida.')
        return redirect('importacao_preview', token=token)
    apagar_preview(token)
    request.session.pop('preview_importacao_token', None)
    messages.success(request, f"Importacao concluida: {resultado['importadas']} linhas importadas e {resultado['rejeitadas']} rejeitadas.")
    return redirect('importacao_relatorio', importacao_id=resultado['importacao_id'])


@login_obrigatorio
def importacao_relatorio(request: HttpRequest, importacao_id: int) -> HttpResponse:
    importacao = bd.obter_importacao(importacao_id)
    if not importacao:
        raise Http404
    _exigir_acesso_cliente(request, importacao['cliente_id'])
    return render(request, 'ciberbox/importacao_relatorio.html', {
        'importacao': importacao,
        'linhas': bd.listar_linhas_importacao(importacao_id),
    })


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
@perfis_permitidos('ADMINISTRADOR')
def logs_lista(request: HttpRequest) -> HttpResponse:
    return render(request, 'ciberbox/logs_lista.html', {'logs': bd.listar_logs()})
