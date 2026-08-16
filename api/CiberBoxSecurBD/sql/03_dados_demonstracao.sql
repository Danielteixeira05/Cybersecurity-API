-- Dados ficticios, suficientes para demonstrar todas as queries da Ficha 9.

BEGIN;

INSERT INTO clientes (nome, nif, email, telefone, morada, setor_atividade, numero_colaboradores, volume_negocios)
VALUES
    ('Alpha Saude, S.A.', '509111111', 'seguranca@alpha.local', '239100001', 'Coimbra', 'Saude', 185, 12500000.00),
    ('Beta Energia, Lda.', '509222222', 'it@beta.local', '232100002', 'Viseu', 'Energia', 75, 6900000.00),
    ('Gamma Transportes, S.A.', '509333333', 'ciso@gamma.local', '234100003', 'Aveiro', 'Transportes', 240, 21000000.00),
    ('Delta Tecnologia, Lda.', '509444444', 'security@delta.local', '231100004', 'Braga', 'Tecnologia', 42, 3700000.00),
    ('Epsilon Municipal, E.M.', '509555555', 'informatica@epsilon.local', '244100005', 'Leiria', 'Administracao Publica', 310, 15500000.00),
    ('Zeta Industria, S.A.', '509666666', 'soc@zeta.local', '255100006', 'Porto', 'Industria', 520, 44800000.00)
ON CONFLICT (nif) DO UPDATE SET
    nome = EXCLUDED.nome,
    email = EXCLUDED.email,
    telefone = EXCLUDED.telefone,
    morada = EXCLUDED.morada,
    setor_atividade = EXCLUDED.setor_atividade,
    numero_colaboradores = EXCLUDED.numero_colaboradores,
    volume_negocios = EXCLUDED.volume_negocios,
    atualizado_em = CURRENT_TIMESTAMP;

INSERT INTO utilizadores_clientes (utilizador_id, cliente_id, principal)
SELECT u.id, c.id, TRUE
FROM utilizadores u
JOIN clientes c ON c.nif = u.nif
WHERE u.email IN ('cliente1@ciberbox.local', 'cliente2@ciberbox.local')
ON CONFLICT (utilizador_id, cliente_id) DO UPDATE SET principal = EXCLUDED.principal;

INSERT INTO contactos_clientes (cliente_id, tipo, nome, cargo, email, telefone, comunicado_cncs)
SELECT c.id, v.tipo, v.nome, v.cargo, v.email, v.telefone, v.comunicado
FROM clientes c
JOIN (VALUES
    ('509111111', 'RESPONSAVEL_SEGURANCA', 'Ana Martins', 'Responsavel de Seguranca', 'ana.martins@alpha.local', '910000001', TRUE),
    ('509111111', 'CONTACTO_PERMANENTE', 'SOC Alpha', 'Equipa Operacional', 'soc@alpha.local', '910000002', TRUE),
    ('509222222', 'RESPONSAVEL_SEGURANCA', 'Bruno Costa', 'CISO', 'bruno.costa@beta.local', '910000003', TRUE),
    ('509222222', 'CONTACTO_PERMANENTE', 'NOC Beta', 'Operacao 24x7', 'noc@beta.local', '910000004', FALSE),
    ('509333333', 'RESPONSAVEL_SEGURANCA', 'Carla Lopes', 'Diretora de TI', 'carla.lopes@gamma.local', '910000005', TRUE),
    ('509444444', 'RESPONSAVEL_SEGURANCA', 'Diogo Reis', 'CTO', 'diogo.reis@delta.local', '910000006', FALSE),
    ('509555555', 'RESPONSAVEL_SEGURANCA', 'Eva Sousa', 'Chefe de Informatica', 'eva.sousa@epsilon.local', '910000007', TRUE),
    ('509666666', 'RESPONSAVEL_SEGURANCA', 'Filipe Neves', 'CISO', 'filipe.neves@zeta.local', '910000008', TRUE)
) AS v(nif, tipo, nome, cargo, email, telefone, comunicado)
ON c.nif = v.nif
ON CONFLICT (cliente_id, tipo, email) DO UPDATE SET
    nome = EXCLUDED.nome,
    cargo = EXCLUDED.cargo,
    telefone = EXCLUDED.telefone,
    comunicado_cncs = EXCLUDED.comunicado_cncs,
    atualizado_em = CURRENT_TIMESTAMP;

INSERT INTO avaliacoes_risco
(cliente_id, estado_conformidade_id, data_avaliacao, nivel_risco, pontuacao, resumo, recomendacoes, criado_por)
SELECT c.id, v.estado_id, v.data_avaliacao, v.nivel, v.pontuacao, v.resumo, v.recomendacoes, u.id
FROM clientes c
JOIN (VALUES
    ('509111111', 1, DATE '2026-06-01', 'BAIXO', 82.50, 'Controlos principais implementados.', 'Manter revisoes trimestrais.'),
    ('509222222', 2, DATE '2026-06-05', 'MEDIO', 61.00, 'Avaliacao em curso.', 'Concluir inventario e plano de continuidade.'),
    ('509333333', 3, DATE '2026-06-07', 'ALTO', 43.00, 'Existem pendencias relevantes.', 'Corrigir segmentacao e rever acessos privilegiados.'),
    ('509444444', 1, DATE '2026-06-09', 'BAIXO', 88.00, 'Boa maturidade global.', 'Formalizar testes de recuperacao.'),
    ('509555555', 2, DATE '2026-06-10', 'MEDIO', 57.50, 'Documentacao ainda em avaliacao.', 'Atualizar politicas e evidencias.'),
    ('509666666', 3, DATE '2026-06-11', 'CRITICO', 28.00, 'Pendencias criticas em sistemas industriais.', 'Aplicar plano de remediacao prioritario.')
) AS v(nif, estado_id, data_avaliacao, nivel, pontuacao, resumo, recomendacoes)
ON c.nif = v.nif
CROSS JOIN LATERAL (SELECT id FROM utilizadores WHERE email = 'colaborador@ciberbox.local') u
ON CONFLICT (cliente_id, data_avaliacao) DO UPDATE SET
    estado_conformidade_id = EXCLUDED.estado_conformidade_id,
    nivel_risco = EXCLUDED.nivel_risco,
    pontuacao = EXCLUDED.pontuacao,
    resumo = EXCLUDED.resumo,
    recomendacoes = EXCLUDED.recomendacoes,
    criado_por = EXCLUDED.criado_por;

INSERT INTO ativos_tecnologicos
(cliente_id, numero_inventario, tipo_equipamento, nome, tipologia, modelo_versao, numero_serie,
 fabricante, localizacao, sistema_operativo, criticidade, endereco_ip, endereco_mac, fqdn,
 servico_suportado, responsavel_nome, responsavel_contacto, unidade_organica, aplicacoes_servicos,
 comunicado_cncs, programa_gestao_risco, criado_por)
SELECT c.id, v.numero, v.tipo, v.nome, v.tipologia, v.modelo, v.serie, v.fabricante, v.localizacao,
       v.so, v.criticidade, v.ip::inet, v.mac::macaddr, v.fqdn, v.servico, v.responsavel,
       v.contacto, v.unidade, v.aplicacoes, v.cncs, v.risco, u.id
FROM clientes c
JOIN (VALUES
    ('509111111', 'ALP-SRV-001', 'Servidor', 'Servidor Clinico', 'Servidor fisico', 'Dell PowerEdge R750', 'SN-ALP-001', 'Dell', 'Datacenter Coimbra', 'Ubuntu Server 24.04', 'CRITICA', '10.10.1.10', '02:00:00:00:01:10', 'clinico.alpha.local', 'Sistema clinico', 'Ana Martins', '910000001', 'TI', 'ERP Clinico', TRUE, TRUE),
    ('509111111', 'ALP-FW-001', 'Firewall', 'Firewall Perimetral', 'Seguranca de rede', 'FortiGate 200F', 'SN-ALP-002', 'Fortinet', 'Datacenter Coimbra', NULL, 'CRITICA', '10.10.0.1', '02:00:00:00:01:01', 'fw.alpha.local', 'Acesso Internet', 'Ana Martins', '910000001', 'TI', 'VPN e filtragem', TRUE, TRUE),
    ('509222222', 'BET-SRV-001', 'Servidor', 'Servidor SCADA', 'Servidor virtual', 'VMware VM', 'SN-BET-001', 'VMware', 'Centro Operacional', 'Windows Server 2022', 'CRITICA', '10.20.1.20', '02:00:00:00:02:20', 'scada.beta.local', 'Supervisao energetica', 'Bruno Costa', '910000003', 'Operacoes', 'SCADA', TRUE, TRUE),
    ('509333333', 'GAM-SW-001', 'Switch', 'Core Switch', 'Rede', 'Cisco Catalyst 9500', 'SN-GAM-001', 'Cisco', 'Sede', 'IOS-XE', 'ALTA', '10.30.0.2', '02:00:00:00:03:02', 'core.gamma.local', 'Rede corporativa', 'Carla Lopes', '910000005', 'Infraestruturas', 'Routing', TRUE, FALSE),
    ('509444444', 'DEL-NAS-001', 'NAS', 'Repositorio de Backups', 'Armazenamento', 'Synology RS3621', 'SN-DEL-001', 'Synology', 'Sala Tecnica', 'DSM', 'ALTA', '10.40.2.15', '02:00:00:00:04:15', 'backup.delta.local', 'Backups', 'Diogo Reis', '910000006', 'TI', 'Backup', FALSE, TRUE),
    ('509555555', 'EPS-SRV-001', 'Servidor', 'Portal Municipal', 'Servidor virtual', 'Proxmox VM', 'SN-EPS-001', 'Proxmox', 'Municipio', 'Debian 12', 'ALTA', '10.50.1.12', '02:00:00:00:05:12', 'portal.epsilon.local', 'Portal do municipio', 'Eva Sousa', '910000007', 'Informatica', 'Portal web', TRUE, FALSE),
    ('509666666', 'ZET-FW-001', 'Firewall', 'Firewall Industrial', 'OT', 'Palo Alto PA-460', 'SN-ZET-001', 'Palo Alto', 'Fabrica 1', NULL, 'CRITICA', '10.60.0.1', '02:00:00:00:06:01', 'fw-ot.zeta.local', 'Rede industrial', 'Filipe Neves', '910000008', 'OT', 'Segmentacao industrial', TRUE, TRUE)
) AS v(nif, numero, tipo, nome, tipologia, modelo, serie, fabricante, localizacao, so, criticidade,
       ip, mac, fqdn, servico, responsavel, contacto, unidade, aplicacoes, cncs, risco)
ON c.nif = v.nif
CROSS JOIN LATERAL (SELECT id FROM utilizadores WHERE email = 'colaborador@ciberbox.local') u
ON CONFLICT (cliente_id, numero_inventario) DO UPDATE SET
    nome = EXCLUDED.nome,
    modelo_versao = EXCLUDED.modelo_versao,
    criticidade = EXCLUDED.criticidade,
    atualizado_em = CURRENT_TIMESTAMP;

-- Incidentes: quantidades diferentes para construir o Top 5.
INSERT INTO incidentes
(cliente_id, codigo, data_hora_incidente, registado_por, departamento, tipo_incidente, descricao,
 utilizadores_afetados, dados_comprometidos, sistemas_afetados, origem_ataque, ip_atacante,
 resposta_imediata, medidas_corretivas, gravidade, probabilidade_reincidencia, recomendacoes,
 estado, encerrado_em, responsavel_encerramento, criado_por)
SELECT c.id, v.codigo, v.data_hora, v.registado_por, v.departamento, v.tipo, v.descricao,
       v.afetados, v.dados, v.sistemas, v.origem, v.ip::inet, v.resposta, v.medidas,
       v.gravidade, v.probabilidade, v.recomendacoes, v.estado, v.encerrado_em,
       v.responsavel_encerramento, u.id
FROM clientes c
JOIN (VALUES
 ('509111111','ALP-2026-001','2026-01-15 10:20+00'::timestamptz,'Ana Martins','TI','Phishing','Campanha de phishing dirigida.',12,FALSE,'Correio eletronico','Externa','198.51.100.10','Bloqueio do remetente','Formacao adicional','MEDIA','MEDIA','Reforcar awareness','ENCERRADO','2026-01-16 16:00+00'::timestamptz,'Ana Martins'),
 ('509111111','ALP-2026-002','2026-03-11 08:40+00'::timestamptz,'Ana Martins','TI','Malware','Malware detetado num posto.',1,FALSE,'Posto de trabalho','Externa','203.0.113.20','Isolamento do posto','Reinstalacao e EDR','BAIXA','BAIXA','Rever politicas EDR','ENCERRADO','2026-03-11 13:20+00'::timestamptz,'Ana Martins'),
 ('509222222','BET-2026-001','2026-02-02 22:15+00'::timestamptz,'Bruno Costa','Operacoes','DDoS','Indisponibilidade temporaria do portal.',0,FALSE,'Portal externo','Externa','198.51.100.30','Ativacao de mitigacao','Ajuste de regras WAF','ALTA','MEDIA','Contratar protecao DDoS','ENCERRADO','2026-02-03 05:45+00'::timestamptz,'Bruno Costa'),
 ('509222222','BET-2026-002','2026-04-18 14:10+00'::timestamptz,'Bruno Costa','TI','Forca Bruta','Tentativas de acesso VPN.',0,FALSE,'VPN','Externa','203.0.113.40','Bloqueio do IP','MFA obrigatorio','MEDIA','BAIXA','Monitorizar acessos','ENCERRADO','2026-04-18 18:10+00'::timestamptz,'Bruno Costa'),
 ('509222222','BET-2026-003','2026-06-12 09:00+00'::timestamptz,'Bruno Costa','TI','Exploracao de Vulnerabilidades','Tentativa bloqueada pelo IPS.',0,FALSE,'Firewall','Externa','203.0.113.41','Bloqueio automatico','Atualizacao de assinaturas','MEDIA','MEDIA','Aplicar patches','EM_ANALISE',NULL,NULL),
 ('509333333','GAM-2026-001','2026-01-05 07:30+00'::timestamptz,'Carla Lopes','Operacoes','Ransomware','Ficheiros cifrados num servidor legado.',38,TRUE,'Servidor de ficheiros','Externa','198.51.100.50','Isolamento da rede','Restauro e segmentacao','CRITICA','MEDIA','Eliminar sistemas legados','ENCERRADO','2026-01-08 19:00+00'::timestamptz,'Carla Lopes'),
 ('509333333','GAM-2026-002','2026-02-17 16:25+00'::timestamptz,'Carla Lopes','TI','Phishing','Credencial comprometida.',1,TRUE,'Microsoft 365','Externa','198.51.100.51','Reset e revogacao de sessoes','MFA e formacao','ALTA','MEDIA','Rever regras de acesso','ENCERRADO','2026-02-18 10:30+00'::timestamptz,'Carla Lopes'),
 ('509333333','GAM-2026-003','2026-03-20 11:40+00'::timestamptz,'Carla Lopes','TI','Malware','Trojan num computador portatil.',1,FALSE,'Portatil','Externa','198.51.100.52','Isolamento','Reimagem','MEDIA','BAIXA','Melhorar controlo USB','ENCERRADO','2026-03-20 18:00+00'::timestamptz,'Carla Lopes'),
 ('509333333','GAM-2026-004','2026-05-09 03:15+00'::timestamptz,'Carla Lopes','Operacoes','DDoS','Ataque volumetrico.',0,FALSE,'Website','Externa','198.51.100.53','Mitigacao ISP','Rate limiting','ALTA','MEDIA','Teste de capacidade','ENCERRADO','2026-05-09 09:45+00'::timestamptz,'Carla Lopes'),
 ('509444444','DEL-2026-001','2026-04-01 12:00+00'::timestamptz,'Diogo Reis','TI','Violacao de Dados','Repositorio exposto temporariamente.',4,TRUE,'Repositorio Git','Interna',NULL,'Remocao do acesso','Rotacao de segredos','ALTA','BAIXA','Auditar repositorios','ENCERRADO','2026-04-01 16:00+00'::timestamptz,'Diogo Reis'),
 ('509555555','EPS-2026-001','2026-02-24 09:50+00'::timestamptz,'Eva Sousa','Informatica','Phishing','Mensagem fraudulenta recebida.',7,FALSE,'Correio eletronico','Externa','203.0.113.60','Bloqueio','Comunicacao interna','BAIXA','MEDIA','Campanha de awareness','ENCERRADO','2026-02-24 14:00+00'::timestamptz,'Eva Sousa'),
 ('509555555','EPS-2026-002','2026-05-30 20:05+00'::timestamptz,'Eva Sousa','Informatica','Exploracao de Vulnerabilidades','Tentativa num servico web.',0,FALSE,'Portal municipal','Externa','203.0.113.61','Bloqueio WAF','Patch aplicado','MEDIA','BAIXA','Rever scanner','ENCERRADO','2026-05-31 09:00+00'::timestamptz,'Eva Sousa'),
 ('509666666','ZET-2026-001','2026-01-12 01:25+00'::timestamptz,'Filipe Neves','OT','Malware','Detecao numa estacao de engenharia.',2,FALSE,'Estacao OT','Externa','198.51.100.70','Isolamento','Reimagem e segmentacao','CRITICA','MEDIA','Reforcar allow-listing','ENCERRADO','2026-01-13 20:00+00'::timestamptz,'Filipe Neves'),
 ('509666666','ZET-2026-002','2026-02-14 17:45+00'::timestamptz,'Filipe Neves','OT','Acesso Indevido','Conta de fornecedor usada fora do horario.',0,FALSE,'VPN OT','Externa','198.51.100.71','Bloqueio da conta','Janelas de acesso','ALTA','MEDIA','Acesso just-in-time','ENCERRADO','2026-02-15 11:00+00'::timestamptz,'Filipe Neves'),
 ('509666666','ZET-2026-003','2026-03-18 06:30+00'::timestamptz,'Filipe Neves','OT','DDoS','Saturacao de ligacao externa.',0,FALSE,'Ligacao WAN','Externa','198.51.100.72','Mitigacao ISP','Redundancia de ligacoes','ALTA','MEDIA','Teste de failover','ENCERRADO','2026-03-18 12:00+00'::timestamptz,'Filipe Neves'),
 ('509666666','ZET-2026-004','2026-04-22 15:10+00'::timestamptz,'Filipe Neves','TI','Phishing','Utilizador forneceu credenciais.',1,TRUE,'Microsoft 365','Externa','198.51.100.73','Reset e MFA','Formacao direcionada','ALTA','MEDIA','Rever conditional access','ENCERRADO','2026-04-22 21:00+00'::timestamptz,'Filipe Neves'),
 ('509666666','ZET-2026-005','2026-06-15 10:00+00'::timestamptz,'Filipe Neves','OT','Exploracao de Vulnerabilidades','Scanner externo detetado.',0,FALSE,'Gateway OT','Externa','198.51.100.74','Bloqueio','Analise em curso','MEDIA','MEDIA','Aplicar patch','EM_ANALISE',NULL,NULL)
) AS v(nif,codigo,data_hora,registado_por,departamento,tipo,descricao,afetados,dados,sistemas,origem,ip,resposta,medidas,gravidade,probabilidade,recomendacoes,estado,encerrado_em,responsavel_encerramento)
ON c.nif = v.nif
CROSS JOIN LATERAL (SELECT id FROM utilizadores WHERE email = 'colaborador@ciberbox.local') u
ON CONFLICT (cliente_id, codigo) DO UPDATE SET
    estado = EXCLUDED.estado,
    encerrado_em = EXCLUDED.encerrado_em,
    atualizado_em = CURRENT_TIMESTAMP;

-- Documentos: distribuidos por cliente e por mes.
INSERT INTO documentos
(cliente_id, categoria, titulo, descricao, nome_ficheiro_original, nome_ficheiro_guardado,
 caminho_ficheiro, tipo_mime, tamanho_bytes, hash_sha256, submetido_por, submetido_em)
SELECT c.id, v.categoria, v.titulo, v.descricao, v.original, v.guardado, v.caminho,
       'application/pdf', v.tamanho, v.hash, u.id, v.submetido_em
FROM clientes c
JOIN (VALUES
 ('509111111','RELATORIO','Relatorio de maturidade Alpha','Documento demonstrativo.','alpha-maturidade.pdf','demo-alpha-maturidade.pdf','private_uploads/documentos/demo-alpha-maturidade.pdf',1200,repeat('a',64),'2026-01-10 09:00+00'::timestamptz),
 ('509111111','EVIDENCIA','Evidencias janeiro Alpha','Documento demonstrativo.','alpha-evidencias.pdf','demo-alpha-evidencias.pdf','private_uploads/documentos/demo-alpha-evidencias.pdf',1300,repeat('b',64),'2026-01-20 09:00+00'::timestamptz),
 ('509111111','PENTEST','Pentest Alpha','Documento demonstrativo.','alpha-pentest.pdf','demo-alpha-pentest.pdf','private_uploads/documentos/demo-alpha-pentest.pdf',1400,repeat('c',64),'2026-02-15 09:00+00'::timestamptz),
 ('509222222','DOCUMENTACAO','Politica de seguranca Beta','Documento demonstrativo.','beta-politica.pdf','demo-beta-politica.pdf','private_uploads/documentos/demo-beta-politica.pdf',1500,repeat('d',64),'2026-02-05 09:00+00'::timestamptz),
 ('509222222','RELATORIO','Relatorio Beta','Documento demonstrativo.','beta-relatorio.pdf','demo-beta-relatorio.pdf','private_uploads/documentos/demo-beta-relatorio.pdf',1600,repeat('e',64),'2026-03-08 09:00+00'::timestamptz),
 ('509333333','PENTEST','Pentest Gamma','Documento demonstrativo.','gamma-pentest.pdf','demo-gamma-pentest.pdf','private_uploads/documentos/demo-gamma-pentest.pdf',1700,repeat('f',64),'2026-03-10 09:00+00'::timestamptz),
 ('509333333','EVIDENCIA','Plano de remediacao Gamma','Documento demonstrativo.','gamma-remediacao.pdf','demo-gamma-remediacao.pdf','private_uploads/documentos/demo-gamma-remediacao.pdf',1800,repeat('1',64),'2026-03-22 09:00+00'::timestamptz),
 ('509444444','RELATORIO','Relatorio Delta','Documento demonstrativo.','delta-relatorio.pdf','demo-delta-relatorio.pdf','private_uploads/documentos/demo-delta-relatorio.pdf',1900,repeat('2',64),'2026-04-01 09:00+00'::timestamptz),
 ('509555555','DOCUMENTACAO','Politicas Epsilon','Documento demonstrativo.','epsilon-politicas.pdf','demo-epsilon-politicas.pdf','private_uploads/documentos/demo-epsilon-politicas.pdf',2000,repeat('3',64),'2026-05-11 09:00+00'::timestamptz),
 ('509666666','RELATORIO','Relatorio Zeta','Documento demonstrativo.','zeta-relatorio.pdf','demo-zeta-relatorio.pdf','private_uploads/documentos/demo-zeta-relatorio.pdf',2100,repeat('4',64),'2026-06-01 09:00+00'::timestamptz),
 ('509666666','PENTEST','Pentest OT Zeta','Documento demonstrativo.','zeta-pentest.pdf','demo-zeta-pentest.pdf','private_uploads/documentos/demo-zeta-pentest.pdf',2200,repeat('5',64),'2026-06-12 09:00+00'::timestamptz)
) AS v(nif,categoria,titulo,descricao,original,guardado,caminho,tamanho,hash,submetido_em)
ON c.nif = v.nif
CROSS JOIN LATERAL (SELECT id FROM utilizadores WHERE email = 'colaborador@ciberbox.local') u
ON CONFLICT (nome_ficheiro_guardado) DO NOTHING;

-- Pedidos com diferentes estados e tempos de resolucao.
INSERT INTO pedidos
(cliente_id, criado_por, atribuido_a, estado_id, assunto, descricao, prioridade, criado_em, atualizado_em, resolvido_em, fechado_em)
SELECT c.id, uc.id, gestor.id, v.estado_id, v.assunto, v.descricao, v.prioridade,
       v.criado_em, COALESCE(v.fechado_em, v.resolvido_em, v.criado_em), v.resolvido_em, v.fechado_em
FROM clientes c
JOIN (VALUES
 ('509111111',4,'Validar relatorio mensal','Solicita-se validacao do relatorio.','NORMAL','2026-05-01 09:00+00'::timestamptz,'2026-05-02 15:00+00'::timestamptz,NULL::timestamptz),
 ('509222222',2,'Duvida sobre inventario','Esclarecimento sobre ativos OT.','ALTA','2026-05-04 10:00+00'::timestamptz,NULL::timestamptz,NULL::timestamptz),
 ('509333333',5,'Fecho de remediacao','Confirmacao das medidas aplicadas.','NORMAL','2026-04-10 08:00+00'::timestamptz,'2026-04-12 08:00+00'::timestamptz,'2026-04-13 10:00+00'::timestamptz),
 ('509444444',3,'Enviar evidencias','Aguardar ficheiros adicionais.','BAIXA','2026-06-01 14:00+00'::timestamptz,NULL::timestamptz,NULL::timestamptz),
 ('509555555',1,'Pedido de apoio','Apoio na atualizacao de politicas.','NORMAL','2026-06-15 11:00+00'::timestamptz,NULL::timestamptz,NULL::timestamptz),
 ('509666666',4,'Validar segmentacao OT','Revisao das evidencias de segmentacao.','URGENTE','2026-03-02 09:00+00'::timestamptz,'2026-03-05 21:00+00'::timestamptz,NULL::timestamptz)
) AS v(nif,estado_id,assunto,descricao,prioridade,criado_em,resolvido_em,fechado_em)
ON c.nif = v.nif
CROSS JOIN LATERAL (
    SELECT COALESCE(
        (SELECT u.id FROM utilizadores u JOIN utilizadores_clientes x ON x.utilizador_id=u.id WHERE x.cliente_id=c.id ORDER BY x.principal DESC LIMIT 1),
        (SELECT id FROM utilizadores WHERE email='admin@ciberbox.local')
    ) AS id
) uc
CROSS JOIN LATERAL (SELECT id FROM utilizadores WHERE email='colaborador@ciberbox.local') gestor
WHERE NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.cliente_id=c.id AND p.assunto=v.assunto);

INSERT INTO historico_estados_pedidos (pedido_id, estado_anterior_id, estado_novo_id, alterado_por, observacao, alterado_em)
SELECT p.id, NULL, 1, p.criado_por, 'Pedido criado.', p.criado_em
FROM pedidos p
WHERE NOT EXISTS (
    SELECT 1 FROM historico_estados_pedidos h WHERE h.pedido_id=p.id AND h.estado_anterior_id IS NULL
);

INSERT INTO historico_estados_pedidos (pedido_id, estado_anterior_id, estado_novo_id, alterado_por, observacao, alterado_em)
SELECT p.id, 1, p.estado_id, p.atribuido_a, 'Estado atualizado durante o acompanhamento.', p.atualizado_em
FROM pedidos p
WHERE p.estado_id <> 1
  AND NOT EXISTS (
      SELECT 1 FROM historico_estados_pedidos h
      WHERE h.pedido_id=p.id AND h.estado_novo_id=p.estado_id
  );

INSERT INTO mensagens_pedidos (pedido_id, autor_id, mensagem, criado_em)
SELECT p.id, p.criado_por, 'Mensagem inicial associada ao pedido.', p.criado_em
FROM pedidos p
WHERE NOT EXISTS (SELECT 1 FROM mensagens_pedidos m WHERE m.pedido_id=p.id);

COMMIT;
