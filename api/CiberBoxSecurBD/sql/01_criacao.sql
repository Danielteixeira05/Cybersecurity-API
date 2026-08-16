-- CiberBoxSecurBD - modelo fisico PostgreSQL
-- UC Bases de Dados, ano letivo 2025/2026
-- Autor: Daniel Teixiera, n.o 27645

BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS perfis (
    id SMALLSERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nome VARCHAR(60) NOT NULL UNIQUE,
    descricao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_perfis_codigo
        CHECK (codigo IN ('ADMINISTRADOR', 'COLABORADOR', 'CLIENTE'))
);

CREATE TABLE IF NOT EXISTS utilizadores (
    id BIGSERIAL PRIMARY KEY,
    perfil_id SMALLINT NOT NULL,
    nome VARCHAR(120) NOT NULL,
    email CITEXT NOT NULL UNIQUE,
    telefone VARCHAR(30),
    nif CHAR(9),
    password_hash VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acesso_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_utilizadores_perfis
        FOREIGN KEY (perfil_id) REFERENCES perfis(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_utilizadores_nif
        CHECK (nif IS NULL OR nif ~ '^[0-9]{9}$')
);

CREATE TABLE IF NOT EXISTS clientes (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(160) NOT NULL,
    nif CHAR(9) NOT NULL UNIQUE,
    email CITEXT NOT NULL,
    telefone VARCHAR(30),
    morada TEXT,
    setor_atividade VARCHAR(100),
    numero_colaboradores INTEGER,
    volume_negocios NUMERIC(14,2),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_clientes_nif CHECK (nif ~ '^[0-9]{9}$'),
    CONSTRAINT ck_clientes_numero_colaboradores
        CHECK (numero_colaboradores IS NULL OR numero_colaboradores >= 0),
    CONSTRAINT ck_clientes_volume_negocios
        CHECK (volume_negocios IS NULL OR volume_negocios >= 0)
);

CREATE TABLE IF NOT EXISTS utilizadores_clientes (
    utilizador_id BIGINT NOT NULL,
    cliente_id BIGINT NOT NULL,
    principal BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (utilizador_id, cliente_id),
    CONSTRAINT fk_utilizadores_clientes_utilizadores
        FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_utilizadores_clientes_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_utilizadores_clientes_principal
    ON utilizadores_clientes (cliente_id)
    WHERE principal = TRUE;

CREATE TABLE IF NOT EXISTS contactos_clientes (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    nome VARCHAR(120) NOT NULL,
    cargo VARCHAR(100),
    email CITEXT NOT NULL,
    telefone VARCHAR(30),
    comunicado_cncs BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contactos_clientes_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_contactos_clientes_tipo
        CHECK (tipo IN ('RESPONSAVEL_SEGURANCA', 'CONTACTO_PERMANENTE', 'OUTRO')),
    CONSTRAINT uq_contactos_clientes_tipo_email
        UNIQUE (cliente_id, tipo, email)
);

CREATE TABLE IF NOT EXISTS estados_conformidade (
    id SMALLSERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(80) NOT NULL UNIQUE,
    ordem SMALLINT NOT NULL UNIQUE,
    CONSTRAINT ck_estados_conformidade_codigo
        CHECK (codigo IN ('CONFORME', 'EM_AVALIACAO', 'COM_PENDENCIAS')),
    CONSTRAINT ck_estados_conformidade_ordem CHECK (ordem > 0)
);

CREATE TABLE IF NOT EXISTS avaliacoes_risco (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    estado_conformidade_id SMALLINT NOT NULL,
    data_avaliacao DATE NOT NULL,
    nivel_risco VARCHAR(20) NOT NULL,
    pontuacao NUMERIC(5,2),
    resumo TEXT NOT NULL,
    recomendacoes TEXT,
    criado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_avaliacoes_risco_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_avaliacoes_risco_estados
        FOREIGN KEY (estado_conformidade_id) REFERENCES estados_conformidade(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_avaliacoes_risco_utilizadores
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_avaliacoes_risco_nivel
        CHECK (nivel_risco IN ('BAIXO', 'MEDIO', 'ALTO', 'CRITICO')),
    CONSTRAINT ck_avaliacoes_risco_pontuacao
        CHECK (pontuacao IS NULL OR (pontuacao >= 0 AND pontuacao <= 100)),
    CONSTRAINT uq_avaliacoes_risco_cliente_data
        UNIQUE (cliente_id, data_avaliacao)
);

CREATE TABLE IF NOT EXISTS importacoes_excel (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    nome_ficheiro_original VARCHAR(255) NOT NULL,
    caminho_ficheiro VARCHAR(500) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PROCESSADO',
    total_linhas INTEGER NOT NULL DEFAULT 0,
    linhas_importadas INTEGER NOT NULL DEFAULT 0,
    linhas_rejeitadas INTEGER NOT NULL DEFAULT 0,
    importado_por BIGINT,
    importado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_importacoes_excel_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_importacoes_excel_utilizadores
        FOREIGN KEY (importado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_importacoes_excel_tipo CHECK (tipo IN ('ATIVOS', 'INCIDENTES')),
    CONSTRAINT ck_importacoes_excel_estado CHECK (estado IN ('PROCESSADO', 'PARCIAL', 'FALHADO')),
    CONSTRAINT ck_importacoes_excel_contagens CHECK (
        total_linhas >= 0 AND linhas_importadas >= 0 AND linhas_rejeitadas >= 0
        AND linhas_importadas + linhas_rejeitadas <= total_linhas
    )
);

CREATE TABLE IF NOT EXISTS ativos_tecnologicos (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    importacao_id BIGINT,
    numero_inventario VARCHAR(80),
    tipo_equipamento VARCHAR(100),
    nome VARCHAR(160) NOT NULL,
    tipologia VARCHAR(100),
    modelo_versao VARCHAR(160),
    numero_serie VARCHAR(120),
    fabricante VARCHAR(120),
    localizacao VARCHAR(160),
    sistema_operativo VARCHAR(120),
    criticidade VARCHAR(20) NOT NULL DEFAULT 'MEDIA',
    endereco_ip INET,
    endereco_mac MACADDR,
    fqdn VARCHAR(255),
    servico_suportado TEXT,
    responsavel_nome VARCHAR(120),
    responsavel_contacto VARCHAR(120),
    unidade_organica VARCHAR(120),
    aplicacoes_servicos TEXT,
    observacoes TEXT,
    comunicado_cncs BOOLEAN NOT NULL DEFAULT FALSE,
    programa_gestao_risco BOOLEAN NOT NULL DEFAULT FALSE,
    criado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ativos_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_ativos_importacoes
        FOREIGN KEY (importacao_id) REFERENCES importacoes_excel(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_ativos_utilizadores
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_ativos_criticidade
        CHECK (criticidade IN ('RESIDUAL', 'BAIXA', 'MEDIA', 'ALTA', 'CRITICA')),
    CONSTRAINT uq_ativos_cliente_inventario
        UNIQUE (cliente_id, numero_inventario)
);

CREATE TABLE IF NOT EXISTS incidentes (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    importacao_id BIGINT,
    codigo VARCHAR(40) NOT NULL,
    data_hora_incidente TIMESTAMPTZ NOT NULL,
    registado_por VARCHAR(120),
    departamento VARCHAR(120),
    tipo_incidente VARCHAR(100) NOT NULL,
    descricao TEXT NOT NULL,
    utilizadores_afetados INTEGER NOT NULL DEFAULT 0,
    dados_comprometidos BOOLEAN NOT NULL DEFAULT FALSE,
    sistemas_afetados TEXT,
    origem_ataque VARCHAR(160),
    ip_atacante INET,
    analise_log TEXT,
    resposta_imediata TEXT,
    medidas_corretivas TEXT,
    entidades_internas TEXT,
    entidades_externas TEXT,
    gravidade VARCHAR(20) NOT NULL,
    probabilidade_reincidencia VARCHAR(20),
    recomendacoes TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'ABERTO',
    encerrado_em TIMESTAMPTZ,
    responsavel_encerramento VARCHAR(120),
    criado_por BIGINT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_incidentes_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_incidentes_importacoes
        FOREIGN KEY (importacao_id) REFERENCES importacoes_excel(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_incidentes_utilizadores
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT uq_incidentes_cliente_codigo UNIQUE (cliente_id, codigo),
    CONSTRAINT ck_incidentes_utilizadores_afetados CHECK (utilizadores_afetados >= 0),
    CONSTRAINT ck_incidentes_gravidade
        CHECK (gravidade IN ('RESIDUAL', 'BAIXA', 'MEDIA', 'ALTA', 'CRITICA')),
    CONSTRAINT ck_incidentes_probabilidade
        CHECK (probabilidade_reincidencia IS NULL OR probabilidade_reincidencia IN ('BAIXA', 'MEDIA', 'ALTA')),
    CONSTRAINT ck_incidentes_estado CHECK (estado IN ('ABERTO', 'EM_ANALISE', 'ENCERRADO')),
    CONSTRAINT ck_incidentes_datas CHECK (encerrado_em IS NULL OR encerrado_em >= data_hora_incidente)
);

CREATE TABLE IF NOT EXISTS documentos (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    categoria VARCHAR(30) NOT NULL,
    titulo VARCHAR(180) NOT NULL,
    descricao TEXT,
    nome_ficheiro_original VARCHAR(255) NOT NULL,
    nome_ficheiro_guardado VARCHAR(255) NOT NULL UNIQUE,
    caminho_ficheiro VARCHAR(500) NOT NULL,
    tipo_mime VARCHAR(120) NOT NULL,
    tamanho_bytes BIGINT NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    privado BOOLEAN NOT NULL DEFAULT TRUE,
    submetido_por BIGINT,
    submetido_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_documentos_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_documentos_utilizadores
        FOREIGN KEY (submetido_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_documentos_categoria
        CHECK (categoria IN ('DOCUMENTACAO', 'RELATORIO', 'PENTEST', 'EVIDENCIA', 'OUTRO')),
    CONSTRAINT ck_documentos_tamanho CHECK (tamanho_bytes >= 0),
    CONSTRAINT ck_documentos_hash CHECK (hash_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS estados_pedidos (
    id SMALLSERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(80) NOT NULL UNIQUE,
    estado_final BOOLEAN NOT NULL DEFAULT FALSE,
    ordem SMALLINT NOT NULL UNIQUE,
    CONSTRAINT ck_estados_pedidos_codigo CHECK (
        codigo IN ('ABERTO', 'EM_ANALISE', 'AGUARDA_CLIENTE', 'RESOLVIDO', 'FECHADO')
    ),
    CONSTRAINT ck_estados_pedidos_ordem CHECK (ordem > 0)
);

CREATE TABLE IF NOT EXISTS pedidos (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    criado_por BIGINT NOT NULL,
    atribuido_a BIGINT,
    estado_id SMALLINT NOT NULL,
    assunto VARCHAR(180) NOT NULL,
    descricao TEXT NOT NULL,
    prioridade VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolvido_em TIMESTAMPTZ,
    fechado_em TIMESTAMPTZ,
    CONSTRAINT fk_pedidos_clientes
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pedidos_criado_por
        FOREIGN KEY (criado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pedidos_atribuido_a
        FOREIGN KEY (atribuido_a) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_pedidos_estados
        FOREIGN KEY (estado_id) REFERENCES estados_pedidos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_pedidos_prioridade CHECK (prioridade IN ('BAIXA', 'NORMAL', 'ALTA', 'URGENTE')),
    CONSTRAINT ck_pedidos_datas CHECK (
        (resolvido_em IS NULL OR resolvido_em >= criado_em)
        AND (fechado_em IS NULL OR fechado_em >= criado_em)
    )
);

CREATE TABLE IF NOT EXISTS mensagens_pedidos (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL,
    autor_id BIGINT NOT NULL,
    mensagem TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensagens_pedidos_pedidos
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_mensagens_pedidos_utilizadores
        FOREIGN KEY (autor_id) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_mensagens_pedidos_mensagem CHECK (length(trim(mensagem)) > 0)
);

CREATE TABLE IF NOT EXISTS historico_estados_pedidos (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL,
    estado_anterior_id SMALLINT,
    estado_novo_id SMALLINT NOT NULL,
    alterado_por BIGINT,
    observacao TEXT,
    alterado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_historico_pedidos
        FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_historico_estado_anterior
        FOREIGN KEY (estado_anterior_id) REFERENCES estados_pedidos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_historico_estado_novo
        FOREIGN KEY (estado_novo_id) REFERENCES estados_pedidos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_historico_alterado_por
        FOREIGN KEY (alterado_por) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS logs_atividade (
    id BIGSERIAL PRIMARY KEY,
    utilizador_id BIGINT,
    acao VARCHAR(80) NOT NULL,
    entidade VARCHAR(80) NOT NULL,
    entidade_id BIGINT,
    detalhes JSONB NOT NULL DEFAULT '{}'::jsonb,
    endereco_ip INET,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_logs_atividade_utilizadores
        FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS linhas_importacao (
    id BIGSERIAL PRIMARY KEY,
    importacao_id BIGINT NOT NULL,
    numero_linha INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL,
    erro TEXT,
    dados JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_linhas_importacao_importacoes
        FOREIGN KEY (importacao_id) REFERENCES importacoes_excel(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_linhas_importacao_linha UNIQUE (importacao_id, numero_linha),
    CONSTRAINT ck_linhas_importacao_numero CHECK (numero_linha > 0),
    CONSTRAINT ck_linhas_importacao_estado CHECK (estado IN ('IMPORTADA', 'REJEITADA'))
);

-- Indices orientados aos filtros, joins e queries do dashboard.
CREATE INDEX IF NOT EXISTS ix_utilizadores_perfil_id ON utilizadores(perfil_id);
CREATE INDEX IF NOT EXISTS ix_utilizadores_ativo ON utilizadores(ativo);
CREATE INDEX IF NOT EXISTS ix_contactos_cliente_id ON contactos_clientes(cliente_id);
CREATE INDEX IF NOT EXISTS ix_avaliacoes_cliente_data ON avaliacoes_risco(cliente_id, data_avaliacao DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_avaliacoes_estado ON avaliacoes_risco(estado_conformidade_id);
CREATE INDEX IF NOT EXISTS ix_importacoes_cliente_data ON importacoes_excel(cliente_id, importado_em DESC);
CREATE INDEX IF NOT EXISTS ix_ativos_cliente ON ativos_tecnologicos(cliente_id);
CREATE INDEX IF NOT EXISTS ix_ativos_criticidade ON ativos_tecnologicos(criticidade);
CREATE INDEX IF NOT EXISTS ix_incidentes_cliente_data ON incidentes(cliente_id, data_hora_incidente DESC);
CREATE INDEX IF NOT EXISTS ix_incidentes_estado ON incidentes(estado);
CREATE INDEX IF NOT EXISTS ix_documentos_cliente_mes ON documentos(cliente_id, submetido_em);
CREATE INDEX IF NOT EXISTS ix_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS ix_pedidos_estado_criado ON pedidos(estado_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_mensagens_pedido ON mensagens_pedidos(pedido_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_historico_pedido ON historico_estados_pedidos(pedido_id, alterado_em);
CREATE INDEX IF NOT EXISTS ix_logs_utilizador_data ON logs_atividade(utilizador_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS ix_logs_entidade ON logs_atividade(entidade, entidade_id);

COMMIT;
