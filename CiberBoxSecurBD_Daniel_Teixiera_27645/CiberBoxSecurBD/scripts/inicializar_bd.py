#!/usr/bin/env python
from pathlib import Path
import argparse
import os
import sys

from dotenv import load_dotenv
import psycopg

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def executar_script(conexao, caminho: Path) -> None:
    sql = caminho.read_text(encoding='utf-8')
    with conexao.cursor() as cursor:
        cursor.execute(sql)
    print(f'[OK] {caminho.name}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Inicializa a base de dados CiberBoxSecurBD.')
    parser.add_argument('--limpar', action='store_true', help='Executa a limpeza opcional antes da criação.')
    args = parser.parse_args()

    dsn = {
        'dbname': os.getenv('POSTGRES_DB', 'ciberbox_bd'),
        'user': os.getenv('POSTGRES_USER', 'ciberbox_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'ciberbox_password'),
        'host': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
    }
    try:
        with psycopg.connect(**dsn, autocommit=True) as conexao:
            if args.limpar:
                executar_script(conexao, ROOT / 'sql' / '00_limpeza_opcional.sql')
            executar_script(conexao, ROOT / 'sql' / '01_criacao.sql')
            executar_script(conexao, ROOT / 'sql' / '02_inicializacao.sql')
            executar_script(conexao, ROOT / 'sql' / '03_dados_demonstracao.sql')
    except Exception as exc:
        print(f'[ERRO] {exc}', file=sys.stderr)
        return 1
    print('Base de dados inicializada com sucesso.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
