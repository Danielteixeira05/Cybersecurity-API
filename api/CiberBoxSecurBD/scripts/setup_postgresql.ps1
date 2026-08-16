# Executar num PowerShell com psql disponível e adaptar o utilizador administrador.
$ErrorActionPreference = "Stop"

psql -U postgres -c "CREATE USER ciberbox_user WITH PASSWORD 'ciberbox_password';" 2>$null
psql -U postgres -c "CREATE DATABASE ciberbox_bd OWNER ciberbox_user ENCODING 'UTF8';" 2>$null

Copy-Item .env.example .env -ErrorAction SilentlyContinue
python scripts/inicializar_bd.py --limpar
python manage.py check
Write-Host "Abrir: http://127.0.0.1:8000/"
python manage.py runserver
