#!/usr/bin/env python3
"""Verificação integrada do projeto CiberBoxSecurBD.

Não substitui uma suite de testes de produção. Confirma os pontos académicos
essenciais: ligação, esquema SQL, dados de demonstração, dashboard, autenticação,
controlo de acesso, CRUD temporário e leitura dos modelos Excel.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciberbox_bd.settings")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test import Client  # noqa: E402

from ciberbox import basededados as bd  # noqa: E402
from ciberbox.excel_import import analisar_excel  # noqa: E402


def ok(texto: str) -> None:
    print(f"[OK] {texto}")


def verificar(condicao: bool, texto: str) -> None:
    if not condicao:
        raise AssertionError(texto)
    ok(texto)


def main() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user, version()")
        db, user, version = cursor.fetchone()
    verificar(db == os.getenv("POSTGRES_DB", "ciberbox_bd"), f"ligação à base de dados {db} como {user}")
    print(f"     {version.split(',')[0]}")

    tabelas_esperadas = {
        "perfis", "utilizadores", "clientes", "utilizadores_clientes",
        "contactos_clientes", "estados_conformidade", "avaliacoes_risco",
        "importacoes_excel", "linhas_importacao", "ativos_tecnologicos",
        "incidentes", "documentos", "estados_pedidos", "pedidos",
        "mensagens_pedidos", "historico_estados_pedidos", "logs_atividade",
    }
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        tabelas = {row[0] for row in cursor.fetchall()}
    verificar(tabelas_esperadas.issubset(tabelas), f"17 tabelas do domínio encontradas")

    admin = bd.autenticar_utilizador("admin@ciberbox.local", "Demo2026!")
    verificar(bool(admin and admin["perfil_codigo"] == "ADMINISTRADOR"), "autenticação PBKDF2 do administrador")
    verificar(bd.autenticar_utilizador("admin@ciberbox.local", "errada") is None, "password errada é rejeitada")

    dashboard = bd.obter_dashboard()
    verificar({"conformidade", "top_incidentes", "documentos_mes", "utilizadores_perfil", "pedidos_estado"} == set(dashboard), "cinco consultas do dashboard executadas")
    verificar(len(dashboard["conformidade"]) == 3, "dashboard inclui os três estados NIS2")
    verificar(1 <= len(dashboard["top_incidentes"]) <= 5, "top 5 de clientes com incidentes")
    verificar(any(r["total_documentos"] > 0 for r in dashboard["documentos_mes"]), "documentos agregados por cliente e mês")
    verificar({r["codigo"] for r in dashboard["utilizadores_perfil"]} == {"ADMINISTRADOR", "COLABORADOR", "CLIENTE"}, "distribuição pelos três perfis")
    verificar(any(r["tempo_medio_resolucao_horas"] is not None for r in dashboard["pedidos_estado"]), "tempo médio de resolução calculado")

    # CRUD num bloco que é sempre revertido, para não poluir os dados de demonstração.
    with transaction.atomic():
        sufixo = str(uuid4().int)[-6:]
        nif = f"9{sufixo:0>8}"[-9:]
        dados = {
            "nome": "Cliente temporário de verificação",
            "nif": nif,
            "email": f"temporario-{sufixo}@example.test",
            "telefone": "910000000",
            "morada": "Morada de teste",
            "setor_atividade": "Testes",
            "numero_colaboradores": 1,
            "volume_negocios": 1000,
            "ativo": True,
        }
        cliente_id = bd.criar_cliente(dados, admin["id"])
        verificar(bd.obter_cliente(cliente_id)["nome"] == dados["nome"], "CREATE e SELECT de cliente por SQL direto")
        dados["nome"] = "Cliente temporário atualizado"
        bd.atualizar_cliente(cliente_id, dados, admin["id"])
        verificar(bd.obter_cliente(cliente_id)["nome"] == dados["nome"], "UPDATE de cliente por SQL direto")
        bd.eliminar_cliente(cliente_id, admin["id"])
        verificar(bd.obter_cliente(cliente_id) is None, "DELETE de cliente por SQL direto")
        transaction.set_rollback(True)

    excel_ativos = analisar_excel(BASE_DIR / "exemplos" / "modelo_importacao_ativos.xlsx", "ATIVOS")
    excel_incidentes = analisar_excel(BASE_DIR / "exemplos" / "modelo_importacao_incidentes.xlsx", "INCIDENTES")
    verificar(excel_ativos["validas"] >= 1 and excel_ativos["rejeitadas"] == 0, "modelo Excel de ativos analisado")
    verificar(excel_incidentes["validas"] >= 1 and excel_incidentes["rejeitadas"] == 0, "modelo Excel de incidentes analisado")

    # Persistência real de um lote, revertida no final para manter os dados limpos.
    with transaction.atomic():
        linhas_teste = excel_ativos["linhas"]
        for indice, linha in enumerate(linhas_teste, start=1):
            linha["dados"]["numero_inventario"] = f"VERIFICACAO-{uuid4().hex[:8]}-{indice}"
        resultado_importacao = bd.processar_importacao(
            cliente_id=1,
            tipo="ATIVOS",
            nome_ficheiro_original="verificacao.xlsx",
            caminho_ficheiro="temporario/verificacao.xlsx",
            linhas=linhas_teste,
            utilizador_id=admin["id"],
        )
        verificar(resultado_importacao["importadas"] == len(linhas_teste), "persistência transacional do lote Excel")
        verificar(len(bd.listar_linhas_importacao(resultado_importacao["importacao_id"])) == len(linhas_teste), "relatório por linha da importação")
        transaction.set_rollback(True)

    cliente_http = Client(HTTP_HOST="localhost")
    resposta = cliente_http.get("/login/")
    verificar(resposta.status_code == 200, "página de login responde")
    resposta = cliente_http.post(
        "/login/",
        {"email": "admin@ciberbox.local", "password": "Demo2026!"},
        follow=True,
    )
    verificar(resposta.status_code == 200 and resposta.request["PATH_INFO"] == "/", "login web e redirecionamento para dashboard")
    for caminho in ("/", "/clientes/", "/utilizadores/", "/ativos/", "/incidentes/", "/avaliacoes/", "/documentos/", "/pedidos/", "/importacoes/", "/logs/"):
        resposta = cliente_http.get(caminho)
        verificar(resposta.status_code == 200, f"rota autenticada {caminho}")

    cliente_restrito = Client(HTTP_HOST="localhost")
    cliente_restrito.post(
        "/login/",
        {"email": "cliente1@ciberbox.local", "password": "Demo2026!"},
        follow=True,
    )
    verificar(cliente_restrito.get("/clientes/1/").status_code == 200, "cliente acede à sua organização")
    request_logger = logging.getLogger("django.request")
    nivel_anterior = request_logger.level
    request_logger.setLevel(logging.CRITICAL)
    try:
        verificar(cliente_restrito.get("/clientes/2/").status_code == 404, "cliente não acede a outra organização")
    finally:
        request_logger.setLevel(nivel_anterior)
    verificar(cliente_restrito.get("/utilizadores/").status_code == 302, "perfil Cliente é impedido de gerir utilizadores")

    print("\nVerificação concluída sem erros.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        raise
