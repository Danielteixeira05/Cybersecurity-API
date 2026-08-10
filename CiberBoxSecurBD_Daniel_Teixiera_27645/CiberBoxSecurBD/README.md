# CiberBoxSecurBD

**Unidade Curricular:** Bases de Dados  
**Curso:** Tecnologias e Design de Multimédia  
**Ano letivo:** 2025/2026  
**Estudante:** Daniel Teixiera - n.º 27645

## Objetivo

Aplicação Django para o domínio CiberBoxSecur, com PostgreSQL e persistência exclusivamente por SQL direto. O projeto inclui os modelos conceptual, lógico e físico, scripts SQL, CRUD, dashboard da Ficha 9 e a funcionalidade extra de importação de ativos/incidentes a partir de Excel.

## Cumprimento do enunciado

- Modelo conceptual explicado e justificado: `modelos/modelo_conceptual.md` e diagramas.
- Modelo lógico explicado e justificado: `modelos/modelo_logico.md`.
- Modelo físico explicado e justificado: `modelos/modelo_fisico.md` e `sql/01_criacao.sql`.
- Criação e inicialização: pasta `sql/`.
- Aplicação Django: pasta `ciberbox/`.
- SQL direto sem ORM: `ciberbox/basededados.py`.
- Dashboard com as cinco consultas da Ficha 9: `sql/04_queries_dashboard.sql` e funções `dashboard_*`.
- Extra de Excel: `ciberbox/excel_import.py`, páginas de pré-visualização e relatório.

## Tecnologias

- Python 3.11 ou superior;
- Django 5.2;
- PostgreSQL 15 ou superior;
- Psycopg 3;
- OpenPyXL apenas para ler ficheiros Excel;
- HTML e CSS próprios para a interface.

Não existem ficheiros `models.py` com entidades do domínio e não são usados `Model`, `QuerySet`, `ModelForm` ou métodos do ORM para persistir informação.

## Instalação rápida

### 1. Criar a base de dados e utilizador

No pgAdmin ou em `psql`, executar como utilizador administrador:

```sql
CREATE USER ciberbox_user WITH PASSWORD 'ciberbox_password';
CREATE DATABASE ciberbox_bd OWNER ciberbox_user ENCODING 'UTF8';
```

Estas credenciais são apenas locais e devem ser alteradas num ambiente real.

### 2. Criar ambiente Python

No PowerShell:

```powershell
cd CiberBoxSecurBD
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 3. Criar e inicializar as tabelas

Forma recomendada, independente do `psql`:

```powershell
python scripts/inicializar_bd.py --limpar
```

O script executa, por ordem:

1. `00_limpeza_opcional.sql`, quando usado `--limpar`;
2. `01_criacao.sql`;
3. `02_inicializacao.sql`;
4. `03_dados_demonstracao.sql`.

### 4. Executar a aplicação

```powershell
python manage.py check
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`.

## Contas de demonstração

Todas usam a password `Demo2026!`:

| Perfil | Email |
|---|---|
| Administrador | `admin@ciberbox.local` |
| Colaborador | `colaborador@ciberbox.local` |
| Cliente Alpha | `cliente1@ciberbox.local` |
| Cliente Beta | `cliente2@ciberbox.local` |

Os hashes são PBKDF2-SHA256. A password em texto simples não é guardada na base de dados.

## Estrutura

```text
CiberBoxSecurBD/
├── ciberbox/                  aplicação Django
│   ├── basededados.py         SQL direto e parametrizado
│   ├── excel_import.py        análise e validação de Excel
│   ├── forms.py               formulários Django sem ModelForm
│   ├── views.py               chamadas à camada de dados
│   ├── templates/             interface
│   └── static/                CSS e logótipo
├── ciberbox_bd/               configuração Django
├── sql/                       criação, dados e queries
├── modelos/                   modelos e normalização
├── documentacao/              relatório e defesa
├── exemplos/                  modelos Excel para testes
├── scripts/                   inicialização e verificação
├── .env.example
├── requirements.txt
└── manage.py
```

## Dashboard obrigatório

O dashboard de Administrador e Colaborador mostra:

1. clientes por estado de conformidade NIS2;
2. top 5 de clientes por número de incidentes;
3. documentos por cliente e por mês;
4. utilizadores por perfil;
5. pedidos por estado e tempo médio de resolução.

As consultas completas estão em `sql/04_queries_dashboard.sql`. Na aplicação são executadas por funções do ficheiro `basededados.py`.

## Importação Excel

O menu **Importar Excel** implementa o extra do enunciado:

1. upload de `.xlsx` até 5 MB;
2. deteção da folha e do cabeçalho;
3. mapeamento das colunas dos exemplos fornecidos;
4. validação de campos obrigatórios, IP, MAC, datas e valores controlados;
5. pré-visualização antes de persistir;
6. confirmação explícita;
7. transação com savepoint por linha;
8. relatório de linhas importadas e rejeitadas;
9. rastreabilidade através de `importacoes_excel` e `linhas_importacao`.

Modelos simplificados estão em `exemplos/modelo_importacao_ativos.xlsx` e `exemplos/modelo_importacao_incidentes.xlsx`.

## Segurança implementada

- passwords com hash PBKDF2-SHA256;
- queries parametrizadas com `%s` e lista de parâmetros;
- proteção CSRF nas operações POST;
- autorização por perfil e por cliente;
- sessões em cookies assinados, HttpOnly e SameSite;
- documentos guardados fora da pasta estática;
- nomes físicos aleatórios para ficheiros;
- limite e lista de tipos permitidos;
- hash SHA-256 dos documentos;
- logs sem passwords ou conteúdo dos documentos;
- variáveis de ambiente para credenciais;
- constraints e transações PostgreSQL.

## Verificação automática

Com PostgreSQL iniciado e `.env` configurado:

```powershell
python scripts/verificar_projeto.py
```

O verificador confirma a ligação, tabelas, dados, queries do dashboard, autenticação, CRUD temporário e parser dos dois Excel.

## Preparação da entrega

Antes de comprimir:

- confirmar que `.env` não está incluído;
- remover `.venv`, `__pycache__`, `staticfiles` e uploads de teste;
- executar `python manage.py check`;
- executar `python scripts/verificar_projeto.py`;
- confirmar os diagramas e o relatório PDF;
- ensaiar a explicação das tabelas e das cinco queries.
