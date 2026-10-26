@echo off
rem Parte 3: levanta Cobranza, el simulador de Cuentas y el Bus de Servicios, cada uno en su propia
rem ventana. Requiere haber hecho "pip install -r requirements.txt" antes.
cd /d %~dp0

rem Para esta corrida, Cobranza llama a Cuentas por HTTP a traves del Bus (CR-INT-07), en vez del
rem simulador en memoria. No cambia la logica de Cobranza, solo de donde viene la respuesta.
set CUENTAS_URL=http://127.0.0.1:8080/cuentas/cargos

echo Levantando Cobranza API (8000), Cuentas simulado (8001) y Bus de Servicios (8080)...
echo CUENTAS_URL=%CUENTAS_URL%
echo.

start "Cobranza API (via Bus)" cmd /k uvicorn app.main:app --port 8000
start "Cuentas simulado (CR-INT-07)" cmd /k uvicorn simuladores.cuentas_app:app --port 8001
start "Bus de Servicios" cmd /k uvicorn simuladores.bus_app:app --port 8080

echo.
echo Cuando las 3 ventanas digan "Application startup complete", corre en otra terminal:
echo   python simuladores\prueba_integracion.py
