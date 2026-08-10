"""Camada de acesso a dados da aplicacao.

Todas as operacoes de persistencia usam SQL direto e parametrizado. Nao sao
utilizados models nem QuerySets do Django ORM. As views apenas chamam funcoes
publicas deste modulo, conforme as Fichas 7, 8 e 9 da UC de Bases de Dados.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable
import json

from django.contrib.auth.hashers import check_password, make_password
from django.db import connection, transaction


def _dictfetchall(cursor) -> list[dict[str, Any]]:
    colunas = [col[0] for col in cursor.description]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


def _dictfetchone(cursor) -> dict[str, Any] | None:
    linha = cursor.fetchone()
    if linha is None:
        return None
    colunas = [col[0] for col in cursor.description]
    return dict(zip(colunas, linha))


def _json_default(valor: Any) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    return str(valor)


def registar_log(
    utilizador_id: int | None,
    acao: str,
    entidade: str,
    entidade_id: int | None = None,
    detalhes: dict[str, Any] | None = None,
    endereco_ip: str | None = None,
) -> int:
    """Regista uma acao sem guardar passwords, tokens ou conteudo de ficheiros."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO logs_atividade
                (utilizador_id, acao, entidade, entidade_id, detalhes, endereco_ip)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            [
                utilizador_id,
                acao[:80],
                entidade[:80],
                entidade_id,
                json.dumps(detalhes or {}, default=_json_default),
                endereco_ip or None,
            ],
        )
        return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# Perfis e autenticacao
# ---------------------------------------------------------------------------

def listar_perfis() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, codigo, nome, descricao FROM perfis ORDER BY id")
        return _dictfetchall(cursor)


def obter_perfil(perfil_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, codigo, nome, descricao FROM perfis WHERE id = %s", [perfil_id])
        return _dictfetchone(cursor)


def obter_utilizador_por_email(email: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.nome, u.email, u.telefone, u.nif, u.password_hash,
                   u.ativo, u.perfil_id, p.codigo AS perfil_codigo,
                   p.nome AS perfil_nome
            FROM utilizadores u
            JOIN perfis p ON p.id = u.perfil_id
            WHERE u.email = %s
            """,
            [email.strip()],
        )
        return _dictfetchone(cursor)


def autenticar_utilizador(email: str, password: str) -> dict[str, Any] | None:
    utilizador = obter_utilizador_por_email(email)
    if not utilizador or not utilizador['ativo']:
        return None
    if not check_password(password, utilizador['password_hash']):
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE utilizadores SET ultimo_acesso_em = CURRENT_TIMESTAMP WHERE id = %s",
            [utilizador['id']],
        )
    utilizador.pop('password_hash', None)
    return utilizador


def listar_utilizadores(perfil_codigo: str | None = None) -> list[dict[str, Any]]:
    parametros: list[Any] = []
    filtro = ""
    if perfil_codigo:
        filtro = "WHERE p.codigo = %s"
        parametros.append(perfil_codigo)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT u.id, u.nome, u.email, u.telefone, u.nif, u.ativo,
                   u.ultimo_acesso_em, u.criado_em, u.perfil_id,
                   p.codigo AS perfil_codigo, p.nome AS perfil_nome,
                   STRING_AGG(c.nome, ', ' ORDER BY c.nome) AS clientes
            FROM utilizadores u
            JOIN perfis p ON p.id = u.perfil_id
            LEFT JOIN utilizadores_clientes uc ON uc.utilizador_id = u.id
            LEFT JOIN clientes c ON c.id = uc.cliente_id
            {filtro}
            GROUP BY u.id, p.id
            ORDER BY u.nome
            """,
            parametros,
        )
        return _dictfetchall(cursor)


def obter_utilizador(utilizador_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.nome, u.email, u.telefone, u.nif, u.ativo,
                   u.perfil_id, p.codigo AS perfil_codigo, p.nome AS perfil_nome,
                   (SELECT uc.cliente_id
                    FROM utilizadores_clientes uc
                    WHERE uc.utilizador_id = u.id
                    ORDER BY uc.principal DESC, uc.cliente_id
                    LIMIT 1) AS cliente_id
            FROM utilizadores u
            JOIN perfis p ON p.id = u.perfil_id
            WHERE u.id = %s
            """,
            [utilizador_id],
        )
        return _dictfetchone(cursor)


def criar_utilizador(dados: dict[str, Any], executado_por: int | None = None) -> int:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO utilizadores
                    (perfil_id, nome, email, telefone, nif, password_hash, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    dados['perfil_id'], dados['nome'].strip(), dados['email'].strip(),
                    dados.get('telefone') or None, dados.get('nif') or None,
                    make_password(dados['password']), bool(dados.get('ativo')),
                ],
            )
            utilizador_id = cursor.fetchone()[0]
            cliente_id = dados.get('cliente_id')
            if cliente_id:
                cursor.execute(
                    """
                    INSERT INTO utilizadores_clientes (utilizador_id, cliente_id, principal)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (utilizador_id, cliente_id)
                    DO UPDATE SET principal = TRUE
                    """,
                    [utilizador_id, cliente_id],
                )
        registar_log(executado_por, 'CRIAR', 'utilizadores', utilizador_id,
                     {'email': dados['email'], 'perfil_id': dados['perfil_id']})
        return utilizador_id


def atualizar_utilizador(utilizador_id: int, dados: dict[str, Any], executado_por: int | None = None) -> None:
    with transaction.atomic():
        with connection.cursor() as cursor:
            if dados.get('password'):
                cursor.execute(
                    """
                    UPDATE utilizadores
                    SET perfil_id=%s, nome=%s, email=%s, telefone=%s, nif=%s,
                        password_hash=%s, ativo=%s, atualizado_em=CURRENT_TIMESTAMP
                    WHERE id=%s
                    """,
                    [dados['perfil_id'], dados['nome'].strip(), dados['email'].strip(),
                     dados.get('telefone') or None, dados.get('nif') or None,
                     make_password(dados['password']), bool(dados.get('ativo')), utilizador_id],
                )
            else:
                cursor.execute(
                    """
                    UPDATE utilizadores
                    SET perfil_id=%s, nome=%s, email=%s, telefone=%s, nif=%s,
                        ativo=%s, atualizado_em=CURRENT_TIMESTAMP
                    WHERE id=%s
                    """,
                    [dados['perfil_id'], dados['nome'].strip(), dados['email'].strip(),
                     dados.get('telefone') or None, dados.get('nif') or None,
                     bool(dados.get('ativo')), utilizador_id],
                )
            cursor.execute("DELETE FROM utilizadores_clientes WHERE utilizador_id=%s", [utilizador_id])
            if dados.get('cliente_id'):
                cursor.execute(
                    "INSERT INTO utilizadores_clientes (utilizador_id, cliente_id, principal) VALUES (%s,%s,TRUE)",
                    [utilizador_id, dados['cliente_id']],
                )
        registar_log(executado_por, 'ATUALIZAR', 'utilizadores', utilizador_id,
                     {'email': dados['email'], 'perfil_id': dados['perfil_id']})


def eliminar_utilizador(utilizador_id: int, executado_por: int | None = None) -> None:
    with transaction.atomic():
        registar_log(executado_por, 'ELIMINAR', 'utilizadores', utilizador_id)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM utilizadores WHERE id=%s", [utilizador_id])


def alterar_estado_utilizador(utilizador_id: int, ativo: bool, executado_por: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE utilizadores SET ativo=%s, atualizado_em=CURRENT_TIMESTAMP WHERE id=%s",
            [ativo, utilizador_id],
        )
    registar_log(executado_por, 'ATIVAR' if ativo else 'DESATIVAR', 'utilizadores', utilizador_id)


# ---------------------------------------------------------------------------
# Clientes e contactos
# ---------------------------------------------------------------------------

def listar_clientes(
    utilizador_id: int | None = None,
    perfil_codigo: str | None = None,
    apenas_ativos: bool = False,
) -> list[dict[str, Any]]:
    filtros: list[str] = []
    parametros: list[Any] = []
    joins = ""
    if perfil_codigo == 'CLIENTE' and utilizador_id:
        joins = "JOIN utilizadores_clientes uc ON uc.cliente_id=c.id"
        filtros.append("uc.utilizador_id=%s")
        parametros.append(utilizador_id)
    if apenas_ativos:
        filtros.append("c.ativo=TRUE")
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT c.id, c.nome, c.nif, c.email, c.telefone, c.morada,
                   c.setor_atividade, c.numero_colaboradores, c.volume_negocios,
                   c.ativo, c.criado_em,
                   (SELECT ec.nome
                    FROM avaliacoes_risco ar
                    JOIN estados_conformidade ec ON ec.id=ar.estado_conformidade_id
                    WHERE ar.cliente_id=c.id
                    ORDER BY ar.data_avaliacao DESC, ar.id DESC LIMIT 1) AS estado_conformidade,
                   (SELECT COUNT(*) FROM ativos_tecnologicos a WHERE a.cliente_id=c.id) AS total_ativos,
                   (SELECT COUNT(*) FROM incidentes i WHERE i.cliente_id=c.id) AS total_incidentes
            FROM clientes c
            {joins}
            {where}
            ORDER BY c.nome
            """,
            parametros,
        )
        return _dictfetchall(cursor)


def obter_cliente(cliente_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.*,
                   ec.nome AS estado_conformidade,
                   ar.nivel_risco, ar.pontuacao, ar.data_avaliacao,
                   ar.resumo AS resumo_avaliacao, ar.recomendacoes
            FROM clientes c
            LEFT JOIN LATERAL (
                SELECT * FROM avaliacoes_risco x
                WHERE x.cliente_id=c.id
                ORDER BY x.data_avaliacao DESC, x.id DESC LIMIT 1
            ) ar ON TRUE
            LEFT JOIN estados_conformidade ec ON ec.id=ar.estado_conformidade_id
            WHERE c.id=%s
            """,
            [cliente_id],
        )
        return _dictfetchone(cursor)


def utilizador_tem_acesso_cliente(utilizador_id: int, perfil_codigo: str, cliente_id: int) -> bool:
    if perfil_codigo in ('ADMINISTRADOR', 'COLABORADOR'):
        return True
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM utilizadores_clientes WHERE utilizador_id=%s AND cliente_id=%s)",
            [utilizador_id, cliente_id],
        )
        return bool(cursor.fetchone()[0])


def criar_cliente(dados: dict[str, Any], executado_por: int | None = None) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO clientes
                (nome, nif, email, telefone, morada, setor_atividade,
                 numero_colaboradores, volume_negocios, ativo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            [dados['nome'].strip(), dados['nif'], dados['email'].strip(),
             dados.get('telefone') or None, dados.get('morada') or None,
             dados.get('setor_atividade') or None, dados.get('numero_colaboradores'),
             dados.get('volume_negocios'), bool(dados.get('ativo'))],
        )
        cliente_id = cursor.fetchone()[0]
    registar_log(executado_por, 'CRIAR', 'clientes', cliente_id, {'nif': dados['nif']})
    return cliente_id


def atualizar_cliente(cliente_id: int, dados: dict[str, Any], executado_por: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE clientes SET
                nome=%s, nif=%s, email=%s, telefone=%s, morada=%s,
                setor_atividade=%s, numero_colaboradores=%s, volume_negocios=%s,
                ativo=%s, atualizado_em=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            [dados['nome'].strip(), dados['nif'], dados['email'].strip(),
             dados.get('telefone') or None, dados.get('morada') or None,
             dados.get('setor_atividade') or None, dados.get('numero_colaboradores'),
             dados.get('volume_negocios'), bool(dados.get('ativo')), cliente_id],
        )
    registar_log(executado_por, 'ATUALIZAR', 'clientes', cliente_id, {'nif': dados['nif']})


def eliminar_cliente(cliente_id: int, executado_por: int | None = None) -> None:
    """Eliminacao fisica. As FKs RESTRICT impedem apagar clientes com historico."""
    with transaction.atomic():
        registar_log(executado_por, 'ELIMINAR', 'clientes', cliente_id)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM clientes WHERE id=%s", [cliente_id])


def alterar_estado_cliente(cliente_id: int, ativo: bool, executado_por: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE clientes SET ativo=%s, atualizado_em=CURRENT_TIMESTAMP WHERE id=%s",
            [ativo, cliente_id],
        )
    registar_log(executado_por, 'ATIVAR' if ativo else 'DESATIVAR', 'clientes', cliente_id)


def listar_contactos_cliente(cliente_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM contactos_clientes WHERE cliente_id=%s ORDER BY tipo, nome",
            [cliente_id],
        )
        return _dictfetchall(cursor)


def obter_contacto_cliente(contacto_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM contactos_clientes WHERE id=%s", [contacto_id])
        return _dictfetchone(cursor)


def criar_contacto_cliente(cliente_id: int, dados: dict[str, Any], executado_por: int | None = None) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO contactos_clientes
                (cliente_id, tipo, nome, cargo, email, telefone, comunicado_cncs)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            [cliente_id, dados['tipo'], dados['nome'].strip(), dados.get('cargo') or None,
             dados['email'].strip(), dados.get('telefone') or None,
             bool(dados.get('comunicado_cncs'))],
        )
        contacto_id = cursor.fetchone()[0]
    registar_log(executado_por, 'CRIAR', 'contactos_clientes', contacto_id, {'cliente_id': cliente_id})
    return contacto_id


def atualizar_contacto_cliente(contacto_id: int, dados: dict[str, Any], executado_por: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE contactos_clientes SET tipo=%s, nome=%s, cargo=%s, email=%s,
                telefone=%s, comunicado_cncs=%s, atualizado_em=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            [dados['tipo'], dados['nome'].strip(), dados.get('cargo') or None,
             dados['email'].strip(), dados.get('telefone') or None,
             bool(dados.get('comunicado_cncs')), contacto_id],
        )
    registar_log(executado_por, 'ATUALIZAR', 'contactos_clientes', contacto_id)


def eliminar_contacto_cliente(contacto_id: int, executado_por: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM contactos_clientes WHERE id=%s", [contacto_id])
    registar_log(executado_por, 'ELIMINAR', 'contactos_clientes', contacto_id)


# ---------------------------------------------------------------------------
# Avaliacoes de risco e conformidade
# ---------------------------------------------------------------------------

def listar_estados_conformidade() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, codigo, nome, ordem FROM estados_conformidade ORDER BY ordem")
        return _dictfetchall(cursor)


def listar_avaliacoes(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE ar.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT ar.*, c.nome AS cliente_nome, ec.codigo AS estado_codigo,
                   ec.nome AS estado_nome, u.nome AS criado_por_nome
            FROM avaliacoes_risco ar
            JOIN clientes c ON c.id=ar.cliente_id
            JOIN estados_conformidade ec ON ec.id=ar.estado_conformidade_id
            LEFT JOIN utilizadores u ON u.id=ar.criado_por
            {filtro}
            ORDER BY ar.data_avaliacao DESC, ar.id DESC
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_avaliacao(avaliacao_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM avaliacoes_risco WHERE id=%s", [avaliacao_id])
        return _dictfetchone(cursor)


def criar_avaliacao(dados: dict[str, Any], utilizador_id: int | None = None) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO avaliacoes_risco
                (cliente_id, estado_conformidade_id, data_avaliacao, nivel_risco,
                 pontuacao, resumo, recomendacoes, criado_por)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            [dados['cliente_id'], dados['estado_conformidade_id'], dados['data_avaliacao'],
             dados['nivel_risco'], dados.get('pontuacao'), dados['resumo'],
             dados.get('recomendacoes') or None, utilizador_id],
        )
        avaliacao_id = cursor.fetchone()[0]
    registar_log(utilizador_id, 'CRIAR', 'avaliacoes_risco', avaliacao_id,
                 {'cliente_id': dados['cliente_id']})
    return avaliacao_id


def atualizar_avaliacao(avaliacao_id: int, dados: dict[str, Any], utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE avaliacoes_risco SET cliente_id=%s, estado_conformidade_id=%s,
                data_avaliacao=%s, nivel_risco=%s, pontuacao=%s, resumo=%s,
                recomendacoes=%s
            WHERE id=%s
            """,
            [dados['cliente_id'], dados['estado_conformidade_id'], dados['data_avaliacao'],
             dados['nivel_risco'], dados.get('pontuacao'), dados['resumo'],
             dados.get('recomendacoes') or None, avaliacao_id],
        )
    registar_log(utilizador_id, 'ATUALIZAR', 'avaliacoes_risco', avaliacao_id)


def eliminar_avaliacao(avaliacao_id: int, utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM avaliacoes_risco WHERE id=%s", [avaliacao_id])
    registar_log(utilizador_id, 'ELIMINAR', 'avaliacoes_risco', avaliacao_id)


# ---------------------------------------------------------------------------
# Ativos tecnologicos
# ---------------------------------------------------------------------------
_ATIVO_COLUNAS = [
    'cliente_id', 'importacao_id', 'numero_inventario', 'tipo_equipamento', 'nome',
    'tipologia', 'modelo_versao', 'numero_serie', 'fabricante', 'localizacao',
    'sistema_operativo', 'criticidade', 'endereco_ip', 'endereco_mac', 'fqdn',
    'servico_suportado', 'responsavel_nome', 'responsavel_contacto', 'unidade_organica',
    'aplicacoes_servicos', 'observacoes', 'comunicado_cncs', 'programa_gestao_risco',
    'criado_por',
]


def listar_ativos(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE a.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT a.*, c.nome AS cliente_nome
            FROM ativos_tecnologicos a
            JOIN clientes c ON c.id=a.cliente_id
            {filtro}
            ORDER BY c.nome, a.nome
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_ativo(ativo_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM ativos_tecnologicos WHERE id=%s", [ativo_id])
        return _dictfetchone(cursor)


def _inserir_ativo_cursor(cursor, dados: dict[str, Any], utilizador_id: int | None, importacao_id: int | None = None) -> int:
    cursor.execute(
        """
        INSERT INTO ativos_tecnologicos
            (cliente_id, importacao_id, numero_inventario, tipo_equipamento, nome,
             tipologia, modelo_versao, numero_serie, fabricante, localizacao,
             sistema_operativo, criticidade, endereco_ip, endereco_mac, fqdn,
             servico_suportado, responsavel_nome, responsavel_contacto, unidade_organica,
             aplicacoes_servicos, observacoes, comunicado_cncs, programa_gestao_risco, criado_por)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        [
            dados['cliente_id'], importacao_id or dados.get('importacao_id'),
            dados.get('numero_inventario') or None, dados.get('tipo_equipamento') or None,
            dados['nome'].strip(), dados.get('tipologia') or None,
            dados.get('modelo_versao') or None, dados.get('numero_serie') or None,
            dados.get('fabricante') or None, dados.get('localizacao') or None,
            dados.get('sistema_operativo') or None, dados.get('criticidade') or 'MEDIA',
            dados.get('endereco_ip') or None, dados.get('endereco_mac') or None,
            dados.get('fqdn') or None, dados.get('servico_suportado') or None,
            dados.get('responsavel_nome') or None, dados.get('responsavel_contacto') or None,
            dados.get('unidade_organica') or None, dados.get('aplicacoes_servicos') or None,
            dados.get('observacoes') or None, bool(dados.get('comunicado_cncs')),
            bool(dados.get('programa_gestao_risco')), utilizador_id,
        ],
    )
    return cursor.fetchone()[0]


def criar_ativo(dados: dict[str, Any], utilizador_id: int | None = None) -> int:
    with connection.cursor() as cursor:
        ativo_id = _inserir_ativo_cursor(cursor, dados, utilizador_id)
    registar_log(utilizador_id, 'CRIAR', 'ativos_tecnologicos', ativo_id,
                 {'cliente_id': dados['cliente_id']})
    return ativo_id


def atualizar_ativo(ativo_id: int, dados: dict[str, Any], utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ativos_tecnologicos SET
                cliente_id=%s, numero_inventario=%s, tipo_equipamento=%s, nome=%s,
                tipologia=%s, modelo_versao=%s, numero_serie=%s, fabricante=%s,
                localizacao=%s, sistema_operativo=%s, criticidade=%s, endereco_ip=%s,
                endereco_mac=%s, fqdn=%s, servico_suportado=%s, responsavel_nome=%s,
                responsavel_contacto=%s, unidade_organica=%s, aplicacoes_servicos=%s,
                observacoes=%s, comunicado_cncs=%s, programa_gestao_risco=%s,
                atualizado_em=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            [dados['cliente_id'], dados.get('numero_inventario') or None,
             dados.get('tipo_equipamento') or None, dados['nome'].strip(),
             dados.get('tipologia') or None, dados.get('modelo_versao') or None,
             dados.get('numero_serie') or None, dados.get('fabricante') or None,
             dados.get('localizacao') or None, dados.get('sistema_operativo') or None,
             dados.get('criticidade') or 'MEDIA', dados.get('endereco_ip') or None,
             dados.get('endereco_mac') or None, dados.get('fqdn') or None,
             dados.get('servico_suportado') or None, dados.get('responsavel_nome') or None,
             dados.get('responsavel_contacto') or None, dados.get('unidade_organica') or None,
             dados.get('aplicacoes_servicos') or None, dados.get('observacoes') or None,
             bool(dados.get('comunicado_cncs')), bool(dados.get('programa_gestao_risco')),
             ativo_id],
        )
    registar_log(utilizador_id, 'ATUALIZAR', 'ativos_tecnologicos', ativo_id)


def eliminar_ativo(ativo_id: int, utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM ativos_tecnologicos WHERE id=%s", [ativo_id])
    registar_log(utilizador_id, 'ELIMINAR', 'ativos_tecnologicos', ativo_id)


# ---------------------------------------------------------------------------
# Incidentes
# ---------------------------------------------------------------------------

def listar_incidentes(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE i.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT i.*, c.nome AS cliente_nome
            FROM incidentes i JOIN clientes c ON c.id=i.cliente_id
            {filtro}
            ORDER BY i.data_hora_incidente DESC, i.id DESC
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_incidente(incidente_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM incidentes WHERE id=%s", [incidente_id])
        return _dictfetchone(cursor)


def _inserir_incidente_cursor(cursor, dados: dict[str, Any], utilizador_id: int | None, importacao_id: int | None = None) -> int:
    cursor.execute(
        """
        INSERT INTO incidentes
            (cliente_id, importacao_id, codigo, data_hora_incidente, registado_por,
             departamento, tipo_incidente, descricao, utilizadores_afetados,
             dados_comprometidos, sistemas_afetados, origem_ataque, ip_atacante,
             analise_log, resposta_imediata, medidas_corretivas, entidades_internas,
             entidades_externas, gravidade, probabilidade_reincidencia, recomendacoes,
             estado, encerrado_em, responsavel_encerramento, criado_por)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        [
            dados['cliente_id'], importacao_id or dados.get('importacao_id'), dados['codigo'],
            dados['data_hora_incidente'], dados.get('registado_por') or None,
            dados.get('departamento') or None, dados['tipo_incidente'], dados['descricao'],
            dados.get('utilizadores_afetados') or 0, bool(dados.get('dados_comprometidos')),
            dados.get('sistemas_afetados') or None, dados.get('origem_ataque') or None,
            dados.get('ip_atacante') or None, dados.get('analise_log') or None,
            dados.get('resposta_imediata') or None, dados.get('medidas_corretivas') or None,
            dados.get('entidades_internas') or None, dados.get('entidades_externas') or None,
            dados.get('gravidade') or 'MEDIA', dados.get('probabilidade_reincidencia') or None,
            dados.get('recomendacoes') or None, dados.get('estado') or 'ABERTO',
            dados.get('encerrado_em'), dados.get('responsavel_encerramento') or None,
            utilizador_id,
        ],
    )
    return cursor.fetchone()[0]


def criar_incidente(dados: dict[str, Any], utilizador_id: int | None = None) -> int:
    with connection.cursor() as cursor:
        incidente_id = _inserir_incidente_cursor(cursor, dados, utilizador_id)
    registar_log(utilizador_id, 'CRIAR', 'incidentes', incidente_id,
                 {'cliente_id': dados['cliente_id'], 'codigo': dados['codigo']})
    return incidente_id


def atualizar_incidente(incidente_id: int, dados: dict[str, Any], utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE incidentes SET
                cliente_id=%s, codigo=%s, data_hora_incidente=%s, registado_por=%s,
                departamento=%s, tipo_incidente=%s, descricao=%s,
                utilizadores_afetados=%s, dados_comprometidos=%s, sistemas_afetados=%s,
                origem_ataque=%s, ip_atacante=%s, analise_log=%s, resposta_imediata=%s,
                medidas_corretivas=%s, gravidade=%s, probabilidade_reincidencia=%s,
                recomendacoes=%s, estado=%s, encerrado_em=%s,
                responsavel_encerramento=%s, atualizado_em=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            [dados['cliente_id'], dados['codigo'], dados['data_hora_incidente'],
             dados.get('registado_por') or None, dados.get('departamento') or None,
             dados['tipo_incidente'], dados['descricao'], dados.get('utilizadores_afetados') or 0,
             bool(dados.get('dados_comprometidos')), dados.get('sistemas_afetados') or None,
             dados.get('origem_ataque') or None, dados.get('ip_atacante') or None,
             dados.get('analise_log') or None, dados.get('resposta_imediata') or None,
             dados.get('medidas_corretivas') or None, dados.get('gravidade') or 'MEDIA',
             dados.get('probabilidade_reincidencia') or None, dados.get('recomendacoes') or None,
             dados.get('estado') or 'ABERTO', dados.get('encerrado_em'),
             dados.get('responsavel_encerramento') or None, incidente_id],
        )
    registar_log(utilizador_id, 'ATUALIZAR', 'incidentes', incidente_id)


def eliminar_incidente(incidente_id: int, utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM incidentes WHERE id=%s", [incidente_id])
    registar_log(utilizador_id, 'ELIMINAR', 'incidentes', incidente_id)


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------

def listar_documentos(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE d.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT d.*, c.nome AS cliente_nome, u.nome AS submetido_por_nome
            FROM documentos d
            JOIN clientes c ON c.id=d.cliente_id
            LEFT JOIN utilizadores u ON u.id=d.submetido_por
            {filtro}
            ORDER BY d.submetido_em DESC
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_documento(documento_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT d.*, c.nome AS cliente_nome FROM documentos d JOIN clientes c ON c.id=d.cliente_id WHERE d.id=%s",
            [documento_id],
        )
        return _dictfetchone(cursor)


def criar_documento(dados: dict[str, Any], utilizador_id: int | None = None) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documentos
                (cliente_id, categoria, titulo, descricao, nome_ficheiro_original,
                 nome_ficheiro_guardado, caminho_ficheiro, tipo_mime, tamanho_bytes,
                 hash_sha256, privado, submetido_por)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            [dados['cliente_id'], dados['categoria'], dados['titulo'],
             dados.get('descricao') or None, dados['nome_ficheiro_original'],
             dados['nome_ficheiro_guardado'], dados['caminho_ficheiro'], dados['tipo_mime'],
             dados['tamanho_bytes'], dados['hash_sha256'], bool(dados.get('privado', True)),
             utilizador_id],
        )
        documento_id = cursor.fetchone()[0]
    registar_log(utilizador_id, 'CRIAR', 'documentos', documento_id,
                 {'cliente_id': dados['cliente_id'], 'categoria': dados['categoria']})
    return documento_id


def atualizar_documento(documento_id: int, dados: dict[str, Any], utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE documentos SET categoria=%s, titulo=%s, descricao=%s, privado=%s WHERE id=%s",
            [dados['categoria'], dados['titulo'], dados.get('descricao') or None,
             bool(dados.get('privado', True)), documento_id],
        )
    registar_log(utilizador_id, 'ATUALIZAR', 'documentos', documento_id)


def eliminar_documento(documento_id: int, utilizador_id: int | None = None) -> dict[str, Any] | None:
    documento = obter_documento(documento_id)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM documentos WHERE id=%s", [documento_id])
    registar_log(utilizador_id, 'ELIMINAR', 'documentos', documento_id)
    return documento


# ---------------------------------------------------------------------------
# Pedidos, mensagens e historico
# ---------------------------------------------------------------------------

def listar_estados_pedidos() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, codigo, nome, estado_final, ordem FROM estados_pedidos ORDER BY ordem")
        return _dictfetchall(cursor)


def listar_pedidos(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE p.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT p.*, c.nome AS cliente_nome, ep.codigo AS estado_codigo,
                   ep.nome AS estado_nome, autor.nome AS criado_por_nome,
                   gestor.nome AS atribuido_a_nome
            FROM pedidos p
            JOIN clientes c ON c.id=p.cliente_id
            JOIN estados_pedidos ep ON ep.id=p.estado_id
            JOIN utilizadores autor ON autor.id=p.criado_por
            LEFT JOIN utilizadores gestor ON gestor.id=p.atribuido_a
            {filtro}
            ORDER BY p.criado_em DESC
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_pedido(pedido_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, c.nome AS cliente_nome, ep.codigo AS estado_codigo,
                   ep.nome AS estado_nome, autor.nome AS criado_por_nome,
                   gestor.nome AS atribuido_a_nome
            FROM pedidos p
            JOIN clientes c ON c.id=p.cliente_id
            JOIN estados_pedidos ep ON ep.id=p.estado_id
            JOIN utilizadores autor ON autor.id=p.criado_por
            LEFT JOIN utilizadores gestor ON gestor.id=p.atribuido_a
            WHERE p.id=%s
            """,
            [pedido_id],
        )
        return _dictfetchone(cursor)


def criar_pedido(dados: dict[str, Any], utilizador_id: int) -> int:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM estados_pedidos WHERE codigo='ABERTO'")
            estado_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO pedidos
                    (cliente_id, criado_por, estado_id, assunto, descricao, prioridade)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                [dados['cliente_id'], utilizador_id, estado_id, dados['assunto'],
                 dados['descricao'], dados['prioridade']],
            )
            pedido_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO historico_estados_pedidos
                    (pedido_id, estado_anterior_id, estado_novo_id, alterado_por, observacao)
                VALUES (%s,NULL,%s,%s,'Pedido criado.')
                """,
                [pedido_id, estado_id, utilizador_id],
            )
        registar_log(utilizador_id, 'CRIAR', 'pedidos', pedido_id, {'cliente_id': dados['cliente_id']})
        return pedido_id


def atualizar_pedido(pedido_id: int, dados: dict[str, Any], utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pedidos SET assunto=%s, descricao=%s, prioridade=%s,
                atualizado_em=CURRENT_TIMESTAMP WHERE id=%s
            """,
            [dados['assunto'], dados['descricao'], dados['prioridade'], pedido_id],
        )
    registar_log(utilizador_id, 'ATUALIZAR', 'pedidos', pedido_id)


def eliminar_pedido(pedido_id: int, utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM pedidos WHERE id=%s", [pedido_id])
    registar_log(utilizador_id, 'ELIMINAR', 'pedidos', pedido_id)


def alterar_estado_pedido(
    pedido_id: int,
    estado_novo_id: int,
    alterado_por: int | None,
    observacao: str | None = None,
    atribuido_a: int | None = None,
) -> None:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT estado_id FROM pedidos WHERE id=%s FOR UPDATE", [pedido_id])
            linha = cursor.fetchone()
            if not linha:
                raise ValueError('Pedido inexistente.')
            estado_anterior_id = linha[0]
            cursor.execute(
                "SELECT codigo, estado_final FROM estados_pedidos WHERE id=%s",
                [estado_novo_id],
            )
            estado = cursor.fetchone()
            if not estado:
                raise ValueError('Estado inexistente.')
            codigo, estado_final = estado
            resolvido = codigo in ('RESOLVIDO', 'FECHADO')
            fechado = codigo == 'FECHADO'
            cursor.execute(
                """
                UPDATE pedidos SET estado_id=%s, atribuido_a=%s,
                    atualizado_em=CURRENT_TIMESTAMP,
                    resolvido_em=CASE WHEN %s THEN COALESCE(resolvido_em, CURRENT_TIMESTAMP) ELSE resolvido_em END,
                    fechado_em=CASE WHEN %s THEN COALESCE(fechado_em, CURRENT_TIMESTAMP) ELSE fechado_em END
                WHERE id=%s
                """,
                [estado_novo_id, atribuido_a, resolvido, fechado, pedido_id],
            )
            cursor.execute(
                """
                INSERT INTO historico_estados_pedidos
                    (pedido_id, estado_anterior_id, estado_novo_id, alterado_por, observacao)
                VALUES (%s,%s,%s,%s,%s)
                """,
                [pedido_id, estado_anterior_id, estado_novo_id, alterado_por, observacao or None],
            )
        registar_log(alterado_por, 'ALTERAR_ESTADO', 'pedidos', pedido_id,
                     {'estado_novo_id': estado_novo_id})


def listar_mensagens_pedido(pedido_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT m.*, u.nome AS autor_nome, p.nome AS autor_perfil
            FROM mensagens_pedidos m
            JOIN utilizadores u ON u.id=m.autor_id
            JOIN perfis p ON p.id=u.perfil_id
            WHERE m.pedido_id=%s
            ORDER BY m.criado_em
            """,
            [pedido_id],
        )
        return _dictfetchall(cursor)


def criar_mensagem_pedido(pedido_id: int, autor_id: int, mensagem: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO mensagens_pedidos (pedido_id, autor_id, mensagem) VALUES (%s,%s,%s) RETURNING id",
            [pedido_id, autor_id, mensagem.strip()],
        )
        mensagem_id = cursor.fetchone()[0]
    registar_log(autor_id, 'CRIAR', 'mensagens_pedidos', mensagem_id, {'pedido_id': pedido_id})
    return mensagem_id


def eliminar_mensagem_pedido(mensagem_id: int, utilizador_id: int | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM mensagens_pedidos WHERE id=%s", [mensagem_id])
    registar_log(utilizador_id, 'ELIMINAR', 'mensagens_pedidos', mensagem_id)


def listar_historico_pedido(pedido_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT h.*, ea.nome AS estado_anterior_nome, en.nome AS estado_novo_nome,
                   u.nome AS alterado_por_nome
            FROM historico_estados_pedidos h
            LEFT JOIN estados_pedidos ea ON ea.id=h.estado_anterior_id
            JOIN estados_pedidos en ON en.id=h.estado_novo_id
            LEFT JOIN utilizadores u ON u.id=h.alterado_por
            WHERE h.pedido_id=%s
            ORDER BY h.alterado_em
            """,
            [pedido_id],
        )
        return _dictfetchall(cursor)


# ---------------------------------------------------------------------------
# Importacoes Excel e linhas de importacao
# ---------------------------------------------------------------------------

def listar_importacoes(cliente_id: int | None = None) -> list[dict[str, Any]]:
    filtro = "WHERE ie.cliente_id=%s" if cliente_id else ""
    params = [cliente_id] if cliente_id else []
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT ie.*, c.nome AS cliente_nome, u.nome AS importado_por_nome
            FROM importacoes_excel ie
            JOIN clientes c ON c.id=ie.cliente_id
            LEFT JOIN utilizadores u ON u.id=ie.importado_por
            {filtro}
            ORDER BY ie.importado_em DESC
            """,
            params,
        )
        return _dictfetchall(cursor)


def obter_importacao(importacao_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM importacoes_excel WHERE id=%s", [importacao_id])
        return _dictfetchone(cursor)


def listar_linhas_importacao(importacao_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM linhas_importacao WHERE importacao_id=%s ORDER BY numero_linha",
            [importacao_id],
        )
        return _dictfetchall(cursor)


def eliminar_importacao(importacao_id: int, utilizador_id: int | None = None) -> None:
    """So e permitida quando nenhum ativo/incidente referencia a importacao."""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM importacoes_excel WHERE id=%s", [importacao_id])
    registar_log(utilizador_id, 'ELIMINAR', 'importacoes_excel', importacao_id)


def processar_importacao(
    *,
    cliente_id: int,
    tipo: str,
    nome_ficheiro_original: str,
    caminho_ficheiro: str,
    linhas: Iterable[dict[str, Any]],
    utilizador_id: int | None,
) -> dict[str, int]:
    """Persiste valid rows and errors atomically, producing an audit report."""
    linhas = list(linhas)
    importadas = 0
    rejeitadas = 0
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO importacoes_excel
                    (cliente_id, tipo, nome_ficheiro_original, caminho_ficheiro,
                     estado, total_linhas, linhas_importadas, linhas_rejeitadas, importado_por)
                VALUES (%s,%s,%s,%s,'PROCESSADO',%s,0,0,%s)
                RETURNING id
                """,
                [cliente_id, tipo, nome_ficheiro_original, caminho_ficheiro, len(linhas), utilizador_id],
            )
            importacao_id = cursor.fetchone()[0]

            for linha in linhas:
                numero_linha = int(linha['numero_linha'])
                dados = dict(linha.get('dados') or {})
                dados['cliente_id'] = cliente_id
                erro = linha.get('erro')
                estado = 'REJEITADA' if erro else 'IMPORTADA'
                if not erro:
                    try:
                        # O bloco atomic interno cria um savepoint por linha. Assim, uma
                        # constraint violada rejeita apenas essa linha e nao o lote inteiro.
                        with transaction.atomic():
                            if tipo == 'ATIVOS':
                                _inserir_ativo_cursor(cursor, dados, utilizador_id, importacao_id)
                            elif tipo == 'INCIDENTES':
                                _inserir_incidente_cursor(cursor, dados, utilizador_id, importacao_id)
                            else:
                                raise ValueError('Tipo de importacao desconhecido.')
                        importadas += 1
                    except Exception as exc:
                        erro = str(exc).splitlines()[0][:1000]
                        estado = 'REJEITADA'
                        rejeitadas += 1
                    else:
                        erro = None
                else:
                    rejeitadas += 1

                cursor.execute(
                    """
                    INSERT INTO linhas_importacao
                        (importacao_id, numero_linha, estado, erro, dados)
                    VALUES (%s,%s,%s,%s,%s::jsonb)
                    """,
                    [importacao_id, numero_linha, estado, erro,
                     json.dumps(dados, default=_json_default)],
                )

            estado_importacao = 'PROCESSADO' if rejeitadas == 0 else ('FALHADO' if importadas == 0 else 'PARCIAL')
            cursor.execute(
                """
                UPDATE importacoes_excel
                SET estado=%s, linhas_importadas=%s, linhas_rejeitadas=%s
                WHERE id=%s
                """,
                [estado_importacao, importadas, rejeitadas, importacao_id],
            )
        registar_log(utilizador_id, 'IMPORTAR_EXCEL', 'importacoes_excel', importacao_id,
                     {'tipo': tipo, 'importadas': importadas, 'rejeitadas': rejeitadas})
    return {'importacao_id': importacao_id, 'importadas': importadas, 'rejeitadas': rejeitadas}


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def listar_logs(limite: int = 200) -> list[dict[str, Any]]:
    limite = max(1, min(int(limite), 1000))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT l.*, u.nome AS utilizador_nome, u.email AS utilizador_email
            FROM logs_atividade l
            LEFT JOIN utilizadores u ON u.id=l.utilizador_id
            ORDER BY l.criado_em DESC
            LIMIT %s
            """,
            [limite],
        )
        return _dictfetchall(cursor)


def obter_log(log_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM logs_atividade WHERE id=%s", [log_id])
        return _dictfetchone(cursor)


def eliminar_log(log_id: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM logs_atividade WHERE id=%s", [log_id])


# ---------------------------------------------------------------------------
# Dashboard obrigatorio - Ficha 9
# ---------------------------------------------------------------------------

def dashboard_clientes_por_conformidade() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH ultima_avaliacao AS (
                SELECT DISTINCT ON (cliente_id)
                       cliente_id, estado_conformidade_id
                FROM avaliacoes_risco
                ORDER BY cliente_id, data_avaliacao DESC, id DESC
            )
            SELECT ec.codigo, ec.nome AS estado,
                   COUNT(ua.cliente_id)::INTEGER AS numero_clientes
            FROM estados_conformidade ec
            LEFT JOIN ultima_avaliacao ua ON ua.estado_conformidade_id=ec.id
            GROUP BY ec.id, ec.codigo, ec.nome, ec.ordem
            ORDER BY ec.ordem
            """
        )
        return _dictfetchall(cursor)


def dashboard_top_clientes_incidentes() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, c.nome, COUNT(i.id)::INTEGER AS total_incidentes
            FROM clientes c
            JOIN incidentes i ON i.cliente_id=c.id
            GROUP BY c.id, c.nome
            ORDER BY total_incidentes DESC, c.nome
            LIMIT 5
            """
        )
        return _dictfetchall(cursor)


def dashboard_documentos_por_cliente_mes() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, c.nome,
                   DATE_TRUNC('month', d.submetido_em)::DATE AS mes,
                   COUNT(d.id)::INTEGER AS total_documentos
            FROM clientes c
            JOIN documentos d ON d.cliente_id=c.id
            GROUP BY c.id, c.nome, DATE_TRUNC('month', d.submetido_em)::DATE
            ORDER BY mes DESC, c.nome
            """
        )
        return _dictfetchall(cursor)


def dashboard_utilizadores_por_perfil() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.codigo, p.nome AS perfil,
                   COUNT(u.id)::INTEGER AS total_utilizadores,
                   COUNT(u.id) FILTER (WHERE u.ativo)::INTEGER AS utilizadores_ativos
            FROM perfis p
            LEFT JOIN utilizadores u ON u.perfil_id=p.id
            GROUP BY p.id, p.codigo, p.nome
            ORDER BY p.id
            """
        )
        return _dictfetchall(cursor)


def dashboard_estado_pedidos_tempo_medio() -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ep.codigo, ep.nome AS estado,
                   COUNT(p.id)::INTEGER AS total_pedidos,
                   ROUND(
                       AVG(EXTRACT(EPOCH FROM (p.resolvido_em-p.criado_em))/3600.0)
                       FILTER (WHERE p.resolvido_em IS NOT NULL),
                       2
                   ) AS tempo_medio_resolucao_horas
            FROM estados_pedidos ep
            LEFT JOIN pedidos p ON p.estado_id=ep.id
            GROUP BY ep.id, ep.codigo, ep.nome, ep.ordem
            ORDER BY ep.ordem
            """
        )
        return _dictfetchall(cursor)


def obter_dashboard() -> dict[str, list[dict[str, Any]]]:
    return {
        'conformidade': dashboard_clientes_por_conformidade(),
        'top_incidentes': dashboard_top_clientes_incidentes(),
        'documentos_mes': dashboard_documentos_por_cliente_mes(),
        'utilizadores_perfil': dashboard_utilizadores_por_perfil(),
        'pedidos_estado': dashboard_estado_pedidos_tempo_medio(),
    }


def obter_resumo_cliente(cliente_id: int) -> dict[str, Any]:
    """Resumo seguro da area privada de um unico cliente."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, c.nome,
                   (SELECT COUNT(*) FROM ativos_tecnologicos a WHERE a.cliente_id=c.id) AS total_ativos,
                   (SELECT COUNT(*) FROM incidentes i WHERE i.cliente_id=c.id) AS total_incidentes,
                   (SELECT COUNT(*) FROM documentos d WHERE d.cliente_id=c.id) AS total_documentos,
                   (SELECT COUNT(*) FROM pedidos p WHERE p.cliente_id=c.id) AS total_pedidos,
                   (SELECT ec.nome
                    FROM avaliacoes_risco ar JOIN estados_conformidade ec ON ec.id=ar.estado_conformidade_id
                    WHERE ar.cliente_id=c.id ORDER BY ar.data_avaliacao DESC, ar.id DESC LIMIT 1) AS estado_conformidade,
                   (SELECT ar.nivel_risco
                    FROM avaliacoes_risco ar WHERE ar.cliente_id=c.id
                    ORDER BY ar.data_avaliacao DESC, ar.id DESC LIMIT 1) AS nivel_risco,
                   (SELECT ar.pontuacao
                    FROM avaliacoes_risco ar WHERE ar.cliente_id=c.id
                    ORDER BY ar.data_avaliacao DESC, ar.id DESC LIMIT 1) AS pontuacao
            FROM clientes c WHERE c.id=%s
            """,
            [cliente_id],
        )
        return _dictfetchone(cursor) or {}
