-- CiberBoxSecurBD - limpeza opcional e controlada
-- ATENCAO: este script remove apenas as tabelas do projeto, pela ordem inversa
-- das dependencias. Use-o apenas numa base de dados de desenvolvimento.

BEGIN;

DROP TABLE IF EXISTS linhas_importacao CASCADE;
DROP TABLE IF EXISTS logs_atividade CASCADE;
DROP TABLE IF EXISTS historico_estados_pedidos CASCADE;
DROP TABLE IF EXISTS mensagens_pedidos CASCADE;
DROP TABLE IF EXISTS pedidos CASCADE;
DROP TABLE IF EXISTS estados_pedidos CASCADE;
DROP TABLE IF EXISTS documentos CASCADE;
DROP TABLE IF EXISTS incidentes CASCADE;
DROP TABLE IF EXISTS ativos_tecnologicos CASCADE;
DROP TABLE IF EXISTS importacoes_excel CASCADE;
DROP TABLE IF EXISTS avaliacoes_risco CASCADE;
DROP TABLE IF EXISTS estados_conformidade CASCADE;
DROP TABLE IF EXISTS contactos_clientes CASCADE;
DROP TABLE IF EXISTS utilizadores_clientes CASCADE;
DROP TABLE IF EXISTS clientes CASCADE;
DROP TABLE IF EXISTS utilizadores CASCADE;
DROP TABLE IF EXISTS perfis CASCADE;

COMMIT;
