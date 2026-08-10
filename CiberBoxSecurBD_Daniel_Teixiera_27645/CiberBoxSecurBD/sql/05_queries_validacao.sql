-- Verificacoes rapidas apos a criacao e inicializacao.
SELECT 'perfis' AS tabela, COUNT(*) AS total FROM perfis
UNION ALL SELECT 'utilizadores', COUNT(*) FROM utilizadores
UNION ALL SELECT 'clientes', COUNT(*) FROM clientes
UNION ALL SELECT 'ativos_tecnologicos', COUNT(*) FROM ativos_tecnologicos
UNION ALL SELECT 'incidentes', COUNT(*) FROM incidentes
UNION ALL SELECT 'documentos', COUNT(*) FROM documentos
UNION ALL SELECT 'pedidos', COUNT(*) FROM pedidos;

-- FKs orfas (todos os resultados devem ser zero).
SELECT COUNT(*) AS ativos_sem_cliente
FROM ativos_tecnologicos a LEFT JOIN clientes c ON c.id = a.cliente_id
WHERE c.id IS NULL;

SELECT COUNT(*) AS incidentes_sem_cliente
FROM incidentes i LEFT JOIN clientes c ON c.id = i.cliente_id
WHERE c.id IS NULL;

SELECT COUNT(*) AS pedidos_sem_estado
FROM pedidos p LEFT JOIN estados_pedidos e ON e.id = p.estado_id
WHERE e.id IS NULL;
