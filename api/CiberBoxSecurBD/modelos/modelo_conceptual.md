# Modelo conceptual de dados

## 1. Objetivo

O modelo conceptual representa os objetos do negócio CiberBoxSecur, sem depender ainda dos tipos físicos do PostgreSQL. O ponto de partida foram os requisitos do Projeto Integrado III usados como tema da UC de Bases de Dados: perfis de acesso, clientes, contactos, ativos, incidentes, documentos, avaliações, pedidos, interação e logs. O dashboard obrigatório da Ficha 9 obrigou ainda a conservar conformidade, datas de documentos, perfis e tempos de resolução.

O diagrama encontra-se em `modelo_conceptual.png` e `modelo_conceptual.svg`. A notação é uma adaptação legível de IDEF1X: entidades em caixas, relacionamentos com cardinalidades e linha forte para a entidade associativa cuja identificação depende dos pais.

## 2. Entidades e justificação

| Entidade | Tipo | Justificação funcional |
|---|---|---|
| PERFIS | Independente | Vocabulário controlado dos três perfis exigidos no dashboard. |
| UTILIZADORES | Independente | Autenticação, autorização e autoria de ações. |
| CLIENTES | Independente | Organizações acompanhadas pela empresa. |
| UTILIZADORES_CLIENTES | Dependente/associativa | Resolve a relação N:M entre utilizadores Cliente e organizações. A PK é composta pelas duas FKs. |
| CONTACTOS_CLIENTES | Dependente | Responsável de segurança, contacto permanente e outros contactos. |
| ESTADOS_CONFORMIDADE | Independente | Conforme, Em avaliação e Com pendências. |
| AVALIACOES_RISCO | Dependente | Histórico de avaliações e estado de conformidade de cada cliente. |
| IMPORTACOES_EXCEL | Dependente | Cabeçalho de cada lote importado. |
| LINHAS_IMPORTACAO | Dependente | Resultado auditável de cada linha do Excel. |
| ATIVOS_TECNOLOGICOS | Dependente | Inventário tecnológico exigido no domínio. |
| INCIDENTES | Dependente | Ocorrências de segurança e respetivo encerramento. |
| DOCUMENTOS | Dependente | Metadados de documentação, relatórios, pentests e evidências. |
| ESTADOS_PEDIDOS | Independente | Vocabulário controlado do ciclo de vida dos tickets. |
| PEDIDOS | Dependente | Questões e pedidos de clientes. |
| MENSAGENS_PEDIDOS | Dependente | Interação entre cliente e colaborador. |
| HISTORICO_ESTADOS_PEDIDOS | Dependente | Preserva as mudanças de estado e permite auditoria. |
| LOGS_ATIVIDADE | Dependente opcional | Regista ações de utilizadores ou do sistema. |

## 3. Relacionamentos e cardinalidades

1. Um PERFIL classifica zero ou muitos UTILIZADORES; cada UTILIZADOR tem exatamente um PERFIL.
2. Um UTILIZADOR pode estar associado a zero ou muitos CLIENTES e um CLIENTE pode ter zero ou muitos UTILIZADORES. A relação N:M é resolvida por UTILIZADORES_CLIENTES.
3. Um CLIENTE pode ter zero ou muitos CONTACTOS_CLIENTES; cada contacto pertence a um cliente.
4. Um CLIENTE recebe zero ou muitas AVALIACOES_RISCO; cada avaliação pertence a um cliente e a um ESTADO_CONFORMIDADE.
5. Um CLIENTE possui zero ou muitos ATIVOS, INCIDENTES, DOCUMENTOS e PEDIDOS.
6. Uma IMPORTACAO_EXCEL contém uma ou muitas LINHAS_IMPORTACAO. Um ativo ou incidente pode ter sido criado manualmente ou por uma importação, logo a ligação à importação é opcional.
7. Um PEDIDO tem exatamente um estado atual, zero ou muitas mensagens e pelo menos um registo de histórico (a criação).
8. UTILIZADORES podem criar avaliações, ativos, incidentes, documentos, pedidos, mensagens e logs. Algumas FKs são opcionais para preservar o histórico caso a conta seja removida.

## 4. Participação obrigatória e opcional

- Obrigatória: perfil de um utilizador; cliente de um ativo/incidente/documento/pedido; estado de uma avaliação; estado atual de um pedido.
- Opcional: importação de origem; utilizador que criou registos históricos; colaborador atribuído ao pedido; IP/MAC/FQDN do ativo; encerramento do incidente.
- A entidade UTILIZADORES_CLIENTES só existe quando há associação, sendo identificada pelas chaves dos dois pais.

## 5. Resolução de relações muitos-para-muitos

A relação UTILIZADORES-CLIENTES é N:M porque uma organização pode possuir várias contas e uma conta pode, no futuro, representar mais de uma organização. A entidade associativa `utilizadores_clientes` contém as duas FKs como PK composta e o atributo `principal`.

## 6. Regras do modelo

- O email de utilizador é único.
- O NIF de cliente é único e possui nove dígitos.
- Só pode existir um utilizador principal por cliente.
- A avaliação mais recente determina o estado atual apresentado no dashboard.
- O número de inventário é único dentro do cliente.
- O código de incidente é único dentro do cliente.
- Um pedido mantém o estado atual e o histórico completo das transições.
- Os ficheiros não são guardados na tabela; apenas os metadados e o caminho privado.
