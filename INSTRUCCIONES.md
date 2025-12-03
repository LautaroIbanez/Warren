# Instrucciones para Ejecutar Warren

## Problema: "Service Unavailable"

Si ves errores de "Service Unavailable" en el frontend, significa que el **backend no está corriendo**.

## Solución: Iniciar el Backend

### Paso 1: Abre una nueva ventana de PowerShell

### Paso 2: Ejecuta estos comandos:

```powershell
# Navegar al directorio del proyecto
cd C:\Users\lauta\OneDrive\Desktop\Trading\Warren

# Iniciar el backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Paso 3: Verifica que el backend esté corriendo

Deberías ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using WatchFiles
INFO:     Started server process [XXXX]
INFO:     Application startup complete.
```

### Paso 4: Prueba el backend en el navegador

Abre: http://localhost:8000/

Deberías ver:
```json
{
  "app": "Warren",
  "status": "ok",
  "symbol": "BTCUSDT",
  "interval": "1d"
}
```

## Orden de Inicio

1. **Primero**: Iniciar el backend (Terminal 1)
2. **Segundo**: Iniciar el frontend (Terminal 2)
3. **Tercero**: Abrir http://localhost:5173 en el navegador

## Comandos Completos

### Terminal 1 - Backend:
```powershell
cd C:\Users\lauta\OneDrive\Desktop\Trading\Warren
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2 - Frontend:
```powershell
cd C:\Users\lauta\OneDrive\Desktop\Trading\Warren\frontend
npm run dev
```

## Verificación Rápida

Si ambos están corriendo, puedes probar:

```powershell
# Backend
Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing

# Frontend (después de unos segundos)
Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing
```

## Solución de Problemas

### Error: "uvicorn no se reconoce"
Usa: `python -m uvicorn` en lugar de solo `uvicorn`

### Error: "ModuleNotFoundError"
Ejecuta: `pip install -r requirements.txt`

### Error: Puerto 8000 ocupado
Cambia el puerto: `--port 8001` (y actualiza el frontend)

