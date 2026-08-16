# Checklist final de entrega

## Conteúdo obrigatório

- [x] Modelo conceptual explicado e justificado.
- [x] Diagrama conceptual em PNG/SVG/DOT.
- [x] Modelo lógico explicado e justificado.
- [x] Diagrama lógico em PNG/SVG/DOT.
- [x] Modelo físico PostgreSQL.
- [x] Normalização até 3FN.
- [x] Script de criação das tabelas.
- [x] Script de inicialização.
- [x] Dados de demonstração.
- [x] Cinco queries do dashboard.
- [x] Aplicação Django.
- [x] Persistência por SQL direto em `basededados.py`.
- [x] CRUD das entidades principais.
- [x] Dashboard da Ficha 9.
- [x] Importação Excel de ativos e incidentes.
- [x] Relatório PDF e DOCX.
- [x] README com instruções.
- [x] Guião de defesa.

## Verificações técnicas

- [x] `python manage.py check` sem erros.
- [x] `python scripts/verificar_projeto.py` sem erros.
- [x] Login dos três perfis testado.
- [x] Isolamento entre clientes testado.
- [x] Queries do dashboard executadas.
- [x] Parser dos dois modelos Excel testado.
- [x] Documento DOCX renderizado e revisto página a página.
- [x] PDF renderizado e revisto.

## Antes de comprimir/entregar

- [ ] Confirmar que o PostgreSQL está desligado ou não há processos desnecessários.
- [x] Excluir `.env` real.
- [x] Excluir `.venv`.
- [x] Excluir `__pycache__` e `.pyc`.
- [x] Excluir `.git`.
- [x] Excluir uploads e previews de teste.
- [x] Incluir `.env.example` sem segredos reais.
- [x] Incluir os modelos Excel simplificados.
- [x] Incluir contas de demonstração no README.
- [ ] Testar o ZIP num diretório novo antes da submissão.
- [ ] Confirmar no Moodle o nome/formato final exigido.
