-- Dados de referencia e utilizadores de demonstracao.
-- Password de todas as contas de demonstracao: Demo2026!
-- Os hashes sao PBKDF2-SHA256 e nao correspondem a credenciais reais.

BEGIN;

INSERT INTO perfis (id, codigo, nome, descricao) VALUES
    (1, 'ADMINISTRADOR', 'Administrador', 'Controlo global da aplicacao.'),
    (2, 'COLABORADOR', 'Colaborador', 'Gestao e acompanhamento dos clientes.'),
    (3, 'CLIENTE', 'Cliente', 'Acesso restrito aos dados da sua organizacao.')
ON CONFLICT (id) DO UPDATE SET
    codigo = EXCLUDED.codigo,
    nome = EXCLUDED.nome,
    descricao = EXCLUDED.descricao;
SELECT setval(pg_get_serial_sequence('perfis', 'id'), GREATEST((SELECT MAX(id) FROM perfis), 1));

INSERT INTO estados_conformidade (id, codigo, nome, ordem) VALUES
    (1, 'CONFORME', 'Conforme', 1),
    (2, 'EM_AVALIACAO', 'Em avaliacao', 2),
    (3, 'COM_PENDENCIAS', 'Com pendencias', 3)
ON CONFLICT (id) DO UPDATE SET
    codigo = EXCLUDED.codigo,
    nome = EXCLUDED.nome,
    ordem = EXCLUDED.ordem;
SELECT setval(pg_get_serial_sequence('estados_conformidade', 'id'), GREATEST((SELECT MAX(id) FROM estados_conformidade), 1));

INSERT INTO estados_pedidos (id, codigo, nome, estado_final, ordem) VALUES
    (1, 'ABERTO', 'Aberto', FALSE, 1),
    (2, 'EM_ANALISE', 'Em analise', FALSE, 2),
    (3, 'AGUARDA_CLIENTE', 'Aguarda cliente', FALSE, 3),
    (4, 'RESOLVIDO', 'Resolvido', TRUE, 4),
    (5, 'FECHADO', 'Fechado', TRUE, 5)
ON CONFLICT (id) DO UPDATE SET
    codigo = EXCLUDED.codigo,
    nome = EXCLUDED.nome,
    estado_final = EXCLUDED.estado_final,
    ordem = EXCLUDED.ordem;
SELECT setval(pg_get_serial_sequence('estados_pedidos', 'id'), GREATEST((SELECT MAX(id) FROM estados_pedidos), 1));

INSERT INTO utilizadores (perfil_id, nome, email, telefone, nif, password_hash, ativo)
VALUES
    (1, 'Administrador CiberBoxSecur', 'admin@ciberbox.local', '232000001', NULL,
     'pbkdf2_sha256$1000000$4bg18jGRXQA72HWb3YAZoQ$DE8X0DNeXUbBWmwHLggiLMzxVxB0p45OjRiBteNFBZw=', TRUE),
    (2, 'Daniel Gestor', 'colaborador@ciberbox.local', '232000002', NULL,
     'pbkdf2_sha256$1000000$IQyOLgFNMj2rJbF5vbLG66$wH5hgJCHmi3QZISfXxkOOc42ErcFtr7ylucd52zj7bY=', TRUE),
    (3, 'Cliente Alpha', 'cliente1@ciberbox.local', '232000003', '509111111',
     'pbkdf2_sha256$1000000$1H0LUrF8DXDpJQ0uY6SG8m$qNrF3fyfYzzDc1eMcSx0wVbFQZWgofXrma0cc/sD3IY=', TRUE),
    (3, 'Cliente Beta', 'cliente2@ciberbox.local', '232000004', '509222222',
     'pbkdf2_sha256$1000000$q6PlaTDu4h9LpzYM159608$EFpXa39MyRpZ/yf9EBRya1V6GJ2rt+7YGZYrZQSg8LE=', TRUE)
ON CONFLICT (email) DO UPDATE SET
    perfil_id = EXCLUDED.perfil_id,
    nome = EXCLUDED.nome,
    telefone = EXCLUDED.telefone,
    nif = EXCLUDED.nif,
    password_hash = EXCLUDED.password_hash,
    ativo = EXCLUDED.ativo,
    atualizado_em = CURRENT_TIMESTAMP;

COMMIT;
