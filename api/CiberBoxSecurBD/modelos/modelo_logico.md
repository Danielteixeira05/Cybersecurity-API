# Modelo lógico relacional

## Relações

```text
PERFIS(id PK, codigo UQ, nome UQ, descricao, criado_em)
UTILIZADORES(id PK, perfil_id FK->PERFIS, nome, email UQ, telefone?, nif?, password_hash, ativo, ultimo_acesso_em?, criado_em, atualizado_em)
CLIENTES(id PK, nome, nif UQ, email, telefone?, morada?, setor_atividade?, numero_colaboradores?, volume_negocios?, ativo, criado_em, atualizado_em)
UTILIZADORES_CLIENTES(utilizador_id PK/FK->UTILIZADORES, cliente_id PK/FK->CLIENTES, principal, criado_em)
CONTACTOS_CLIENTES(id PK, cliente_id FK->CLIENTES, tipo, nome, cargo?, email, telefone?, comunicado_cncs, ativo, criado_em, atualizado_em)
ESTADOS_CONFORMIDADE(id PK, codigo UQ, nome UQ, ordem UQ)
AVALIACOES_RISCO(id PK, cliente_id FK->CLIENTES, estado_conformidade_id FK->ESTADOS_CONFORMIDADE, data_avaliacao, nivel_risco, pontuacao?, resumo, recomendacoes?, criado_por? FK->UTILIZADORES, criado_em)
IMPORTACOES_EXCEL(id PK, cliente_id FK->CLIENTES, tipo, nome_ficheiro_original, caminho_ficheiro, estado, total_linhas, linhas_importadas, linhas_rejeitadas, importado_por? FK->UTILIZADORES, importado_em)
LINHAS_IMPORTACAO(id PK, importacao_id FK->IMPORTACOES_EXCEL, numero_linha, estado, erro?, dados, criado_em)
ATIVOS_TECNOLOGICOS(id PK, cliente_id FK->CLIENTES, importacao_id? FK->IMPORTACOES_EXCEL, numero_inventario?, tipo_equipamento?, nome, ... , criticidade, criado_por? FK->UTILIZADORES, criado_em, atualizado_em)
INCIDENTES(id PK, cliente_id FK->CLIENTES, importacao_id? FK->IMPORTACOES_EXCEL, codigo, data_hora_incidente, tipo_incidente, descricao, ... , gravidade, estado, encerrado_em?, criado_por? FK->UTILIZADORES, criado_em, atualizado_em)
DOCUMENTOS(id PK, cliente_id FK->CLIENTES, categoria, titulo, descricao?, nome_ficheiro_original, nome_ficheiro_guardado UQ, caminho_ficheiro, tipo_mime, tamanho_bytes, hash_sha256, privado, submetido_por? FK->UTILIZADORES, submetido_em)
ESTADOS_PEDIDOS(id PK, codigo UQ, nome UQ, estado_final, ordem UQ)
PEDIDOS(id PK, cliente_id FK->CLIENTES, criado_por FK->UTILIZADORES, atribuido_a? FK->UTILIZADORES, estado_id FK->ESTADOS_PEDIDOS, assunto, descricao, prioridade, criado_em, atualizado_em, resolvido_em?, fechado_em?)
MENSAGENS_PEDIDOS(id PK, pedido_id FK->PEDIDOS, autor_id FK->UTILIZADORES, mensagem, criado_em)
HISTORICO_ESTADOS_PEDIDOS(id PK, pedido_id FK->PEDIDOS, estado_anterior_id? FK->ESTADOS_PEDIDOS, estado_novo_id FK->ESTADOS_PEDIDOS, alterado_por? FK->UTILIZADORES, observacao?, alterado_em)
LOGS_ATIVIDADE(id PK, utilizador_id? FK->UTILIZADORES, acao, entidade, entidade_id?, detalhes, endereco_ip?, criado_em)
```

## Chaves candidatas

- PERFIS: `codigo`, `nome`.
- UTILIZADORES: `email`.
- CLIENTES: `nif`.
- CONTACTOS_CLIENTES: `(cliente_id, tipo, email)`.
- AVALIACOES_RISCO: `(cliente_id, data_avaliacao)`.
- ATIVOS_TECNOLOGICOS: `(cliente_id, numero_inventario)` quando o número existe.
- INCIDENTES: `(cliente_id, codigo)`.
- DOCUMENTOS: `nome_ficheiro_guardado`.
- LINHAS_IMPORTACAO: `(importacao_id, numero_linha)`.

## Transformações do conceptual para o lógico

- O atributo multivalor “utilizadores de uma organização” foi transformado em `utilizadores_clientes`.
- O histórico multivalor dos estados dos pedidos foi transformado em `historico_estados_pedidos`.
- Os documentos foram separados do cliente e representados por metadados; o conteúdo permanece no sistema de ficheiros privado.
- Os estados de conformidade e de pedidos foram transformados em relações de referência para impedir valores inconsistentes.
- As linhas dos Excel foram separadas do cabeçalho da importação, formando uma relação 1:N.
