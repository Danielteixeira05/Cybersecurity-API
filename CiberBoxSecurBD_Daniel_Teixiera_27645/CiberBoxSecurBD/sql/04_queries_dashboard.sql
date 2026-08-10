-- Query 1 - numero de clientes por estado de conformidade NIS2.
WITH ultima_avaliacao AS (
    SELECT DISTINCT ON (cliente_id)
           cliente_id, estado_conformidade_id
    FROM avaliacoes_risco
    ORDER BY cliente_id, data_avaliacao DESC, id DESC
)
SELECT ec.codigo, ec.nome AS estado, COUNT(ua.cliente_id)::INTEGER AS numero_clientes
FROM estados_conformidade ec
LEFT JOIN ultima_avaliacao ua ON ua.estado_conformidade_id = ec.id
GROUP BY ec.id, ec.codigo, ec.nome, ec.ordem
ORDER BY ec.ordem;

-- Query 2 - top 5 clientes com mais incidentes de seguranca.
SELECT c.id, c.nome, COUNT(i.id)::INTEGER AS total_incidentes
FROM clientes c
JOIN incidentes i ON i.cliente_id = c.id
GROUP BY c.id, c.nome
ORDER BY total_incidentes DESC, c.nome
LIMIT 5;

-- Query 3 - total de documentos submetidos por cliente e por mes.
SELECT c.id,
       c.nome,
       DATE_TRUNC('month', d.submetido_em)::DATE AS mes,
       COUNT(d.id)::INTEGER AS total_documentos
FROM clientes c
JOIN documentos d ON d.cliente_id = c.id
GROUP BY c.id, c.nome, DATE_TRUNC('month', d.submetido_em)::DATE
ORDER BY mes DESC, c.nome;

-- Query 4 - distribuicao de utilizadores por perfil.
SELECT p.codigo,
       p.nome AS perfil,
       COUNT(u.id)::INTEGER AS total_utilizadores,
       COUNT(u.id) FILTER (WHERE u.ativo)::INTEGER AS utilizadores_ativos
FROM perfis p
LEFT JOIN utilizadores u ON u.perfil_id = p.id
GROUP BY p.id, p.codigo, p.nome
ORDER BY p.id;

-- Query 5 - estado dos pedidos e tempo medio de resolucao em horas.
SELECT ep.codigo,
       ep.nome AS estado,
       COUNT(p.id)::INTEGER AS total_pedidos,
       ROUND(
           AVG(EXTRACT(EPOCH FROM (p.resolvido_em - p.criado_em)) / 3600.0)
           FILTER (WHERE p.resolvido_em IS NOT NULL),
           2
       ) AS tempo_medio_resolucao_horas
FROM estados_pedidos ep
LEFT JOIN pedidos p ON p.estado_id = ep.id
GROUP BY ep.id, ep.codigo, ep.nome, ep.ordem
ORDER BY ep.ordem;
