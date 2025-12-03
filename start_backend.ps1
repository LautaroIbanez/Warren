# Script para iniciar el backend de Warren
Write-Host "Iniciando backend de Warren en http://localhost:8000" -ForegroundColor Green
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

