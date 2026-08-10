# Modelo físico PostgreSQL

O modelo físico encontra-se integralmente em `sql/01_criacao.sql`.

## Convenções

- nomes em português, plural e `snake_case`;
- PK artificial `BIGSERIAL`, exceto tabelas pequenas de referência com `SMALLSERIAL`;
- timestamps como `TIMESTAMPTZ`;
- emails como `CITEXT`, garantindo unicidade sem distinguir maiúsculas;
- endereços de rede como `INET` e `MACADDR`;
- montantes como `NUMERIC`, nunca `FLOAT`;
- textos livres como `TEXT`;
- `JSONB` apenas para auditoria.

## Integridade

- `PRIMARY KEY` garante integridade de entidade;
- `FOREIGN KEY` garante integridade referencial;
- `NOT NULL` identifica participação obrigatória;
- `UNIQUE` implementa chaves candidatas;
- `CHECK` limita NIF, perfis, estados, criticidade, pontuações, datas e contagens;
- `ON DELETE RESTRICT` protege dados históricos de negócio;
- `ON DELETE CASCADE` é usado apenas em entidades estritamente dependentes, como mensagens e linhas de importação;
- `ON DELETE SET NULL` preserva histórico quando o autor deixa de existir.

## Índices

Os índices foram definidos a partir das operações esperadas:

- FK e filtros por cliente;
- avaliação mais recente por cliente e data;
- incidentes por cliente/data;
- documentos por cliente/mês;
- pedidos por estado/data;
- mensagens e histórico por pedido;
- logs por utilizador/data e entidade.

## Ficheiros

O conteúdo dos documentos é guardado em `media/private_uploads/documentos`, que não é servido como conteúdo estático. A tabela guarda nome original, nome físico aleatório, caminho, MIME, tamanho e SHA-256. O download passa por uma view que volta a verificar a autorização.

## Passwords

A tabela guarda apenas `password_hash`, produzido por PBKDF2-SHA256. A autenticação usa `check_password`; nunca existe comparação de passwords em SQL nem armazenamento em texto simples.
