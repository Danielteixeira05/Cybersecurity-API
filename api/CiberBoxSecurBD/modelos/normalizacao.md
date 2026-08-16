# Análise de normalização até à Terceira Forma Normal

## Primeira Forma Normal (1FN)

Todos os atributos são atómicos no contexto da aplicação. Listas como contactos, utilizadores de clientes, ativos, incidentes, mensagens e mudanças de estado não são guardadas numa única coluna: possuem relações próprias. Os campos textuais longos representam descrições livres, não listas usadas para relacionamentos.

## Segunda Forma Normal (2FN)

A única relação com chave primária composta é `utilizadores_clientes`. O atributo `principal` depende da combinação completa `(utilizador_id, cliente_id)` e não apenas de uma parte. Nas restantes relações a chave primária é simples, pelo que não existem dependências parciais.

## Terceira Forma Normal (3FN)

Não são guardados atributos que dependam transitivamente da PK:

- o nome do perfil não é repetido em UTILIZADORES; é obtido por FK;
- o nome do cliente não é repetido em ATIVOS, INCIDENTES, DOCUMENTOS ou PEDIDOS;
- o nome do estado não é repetido nas avaliações e pedidos;
- os dados do autor não são repetidos em documentos, mensagens ou logs;
- os totais do dashboard não são armazenados, sendo calculados por `COUNT` e `AVG`;
- o estado atual de conformidade resulta da avaliação mais recente, preservando o histórico sem duplicação de descrições.

## Dependências funcionais principais

```text
perfil.id -> perfil.codigo, perfil.nome, perfil.descricao
utilizador.id -> perfil_id, nome, email, telefone, nif, password_hash, ativo, datas
utilizador.email -> utilizador.id, perfil_id, nome, ...
cliente.id -> nome, nif, email, telefone, ...
cliente.nif -> cliente.id, nome, email, ...
(cliente_id, numero_inventario) -> dados do ativo
(cliente_id, codigo) -> dados do incidente
pedido.id -> cliente_id, autores, estado_id, assunto, prioridade, datas
(importacao_id, numero_linha) -> estado, erro, dados
```

## Decisões conscientes

`detalhes` e `dados` usam JSONB apenas para auditoria e reprodução do conteúdo variável de logs/linhas importadas. Não substituem as colunas relacionais usadas pelo negócio nem são a fonte dos dashboards. Esta utilização não viola a normalização do núcleo transacional.
