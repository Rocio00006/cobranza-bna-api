"""Parte 3: prueba de integracion END TO END por RED (HTTP real, a traves del Bus de Servicios),
NO llamadas directas a app/servicio.py. Cubre: Desembolso activa -> Home Banking paga parcial ->
duplicado -> fondos insuficientes -> Cuentas sin respuesta (INC-01) -> resolver pendiente -> conciliacion.

Requiere que ya esten corriendo (ver levantar_todo.bat o el README):
  - Cobranza API       puerto 8000  (CUENTAS_URL apuntando al Bus)
  - Cuentas (simulado) puerto 8001
  - Bus de Servicios   puerto 8080

Guarda la evidencia de cada paso (peticion, respuesta y codigo) en
evidencias/integracion_<fecha>.json y un resumen legible en evidencias/integracion_<fecha>.md.

Uso: python simuladores/prueba_integracion.py
"""
import json
import os
import sys
import time
from datetime import date, datetime

import httpx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta cobranza/
sys.path.insert(0, RAIZ)
from app.db import cargar_env  # noqa: E402

BUS_URL = os.environ.get("BUS_URL", "http://127.0.0.1:8080")

SUFIJO = datetime.now().strftime("%H%M%S")
COD_CREDITO = f"CR-INTEG-{SUFIJO}"
ID_CLIENTE = f"CLI-INTEG-{SUFIJO}"
TOKEN_SEGURIDAD = "TOKEN-DEMO-INTEGRACION"

PASOS = []


def _redactar(headers):
    return {k: ("***" if k.lower() in ("x-api-key", "x-token-seguridad") else v) for k, v in headers.items()}


def _llamar(paso, descripcion, metodo, ruta, headers=None, json_body=None, timeout=20):
    headers = headers or {}
    url = f"{BUS_URL}{ruta}"
    t0 = time.perf_counter()
    try:
        r = httpx.request(metodo, url, headers=headers, json=json_body, timeout=timeout)
    except Exception as e:
        print(f"[{paso}] {descripcion}: ERROR al conectar ({e})")
        PASOS.append({"paso": paso, "descripcion": descripcion,
                      "peticion": {"metodo": metodo, "url": url, "headers": _redactar(headers), "body": json_body},
                      "respuesta": {"codigo": None, "body": str(e), "tiempoMs": None}})
        return None, None
    ms = round((time.perf_counter() - t0) * 1000, 1)
    try:
        cuerpo_resp = r.json()
    except Exception:
        cuerpo_resp = r.text
    PASOS.append({
        "paso": paso, "descripcion": descripcion,
        "peticion": {"metodo": metodo, "url": url, "headers": _redactar(headers), "body": json_body},
        "respuesta": {"codigo": r.status_code, "body": cuerpo_resp, "tiempoMs": ms},
    })
    print(f"[{paso}] {descripcion}: HTTP {r.status_code} ({ms} ms)")
    return r, cuerpo_resp


def verificar_servicios_arriba():
    objetivos = (("Cobranza", "/cobranza/salud"), ("Cuentas", "/cuentas/salud"), ("Bus", "/bus/salud"))
    ok = True
    for nombre, ruta in objetivos:
        try:
            r = httpx.get(f"{BUS_URL}{ruta}", timeout=5)
            if r.status_code != 200:
                print(f"ADVERTENCIA: {nombre} respondio {r.status_code} en {ruta}")
                ok = False
        except Exception as e:
            print(f"ERROR: no se pudo contactar {nombre} via {ruta}: {e}")
            ok = False
    if not ok:
        print("\nLevanta los 3 servicios primero (ver levantar_todo.bat) y vuelve a intentar.")
        sys.exit(1)


def pagar(api_key_bus, ref, monto, cuenta, descripcion):
    return _llamar(
        "pago", descripcion, "POST", "/cobranza/cr-int-08/pagos",
        headers={"X-API-Key": api_key_bus, "X-Token-Seguridad": TOKEN_SEGURIDAD},
        json_body={"codCliente": ID_CLIENTE, "codCredito": COD_CREDITO, "montoPago": monto,
                   "cuentaOrigen": cuenta, "referenciaTransaccion": ref, "idCanal": "HB"})


def main():
    cargar_env(os.path.join(RAIZ, ".env"))
    api_key_bus = os.environ.get("API_KEY_INTEGRACION_BUS", "")
    api_key_ejecutar = os.environ.get("API_KEY_COBRANZA_EJECUTAR", "")
    api_key_leer = os.environ.get("API_KEY_COBRANZA_LEER", "")
    if not (api_key_bus and api_key_ejecutar and api_key_leer):
        sys.exit("Faltan API_KEY_* en .env (COBRANZA_LEER, COBRANZA_EJECUTAR, INTEGRACION_BUS)")

    print(f"Credito de prueba: {COD_CREDITO} / cliente {ID_CLIENTE}\n")
    verificar_servicios_arriba()

    # 1. Desembolso activa la obligacion (CR-INT-06)
    _llamar(
        "1-activar", "Desembolso activa la obligacion (CR-INT-06)", "POST",
        "/cobranza/cr-int-06/obligaciones", headers={"X-API-Key": api_key_bus},
        json_body={
            "codCredito": COD_CREDITO, "idCliente": ID_CLIENTE, "idSolicitud": f"SOL-{SUFIJO}",
            "montoAprobado": 1000.00, "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
            "calendarioPagos": [{"numeroCuota": 1, "fechaVencimiento": "2026-11-05", "montoCuota": 1000.00}],
        })

    # 2. Home Banking paga parcial (CR-INT-08)
    pagar(api_key_bus, "OP-INTEG-1", 150.00, "AH-001-123456",
          "Home Banking paga parcial (CR-INT-08)")

    # 3. Duplicado (idempotencia, RN-INT-CR-006)
    pagar(api_key_bus, "OP-INTEG-1", 150.00, "AH-001-123456",
          "Home Banking repite el mismo pago (idempotencia)")

    # 4. Fondos insuficientes en Cuentas
    pagar(api_key_bus, "OP-INTEG-2", 50.00, "AH-SIN-FONDOS",
          "Pago con fondos insuficientes en Cuentas")

    # 5. Cuentas demora / sin respuesta (INC-01)
    pagar(api_key_bus, "OP-INTEG-3", 100.00, "SIN-RESPUESTA",
          "Pago donde Cuentas demora mas que el timeout del cliente (INC-01)")

    print("\nEsperando a que el simulador de Cuentas termine de procesar la operacion demorada...")
    time.sleep(9)

    # 6. Resolver el pago que quedo PENDIENTE (RF-COB-011)
    _llamar(
        "6-resolver", "Resolver el pago PENDIENTE consultando a Cuentas (RF-COB-011 / RN-COB-009)",
        "POST", "/cobranza/pagos/OP-INTEG-3/resolver", headers={"X-API-Key": api_key_ejecutar})

    # 7. Conciliacion del dia (RF-COB-018)
    _llamar(
        "7-conciliacion", "Conciliacion del dia", "GET", "/cobranza/conciliacion",
        headers={"X-API-Key": api_key_leer})

    guardar_evidencia()


def guardar_evidencia():
    hoy = date.today().isoformat()
    carpeta = os.path.join(RAIZ, "evidencias")
    os.makedirs(carpeta, exist_ok=True)
    ruta_json = os.path.join(carpeta, f"integracion_{hoy}.json")
    ruta_md = os.path.join(carpeta, f"integracion_{hoy}.md")

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump({"fecha": hoy, "codCredito": COD_CREDITO, "idCliente": ID_CLIENTE, "pasos": PASOS},
                   f, indent=2, ensure_ascii=False, default=str)

    lineas = [
        f"# Prueba de integracion por red (Bus de Servicios) — {hoy}", "",
        f"Credito de prueba: `{COD_CREDITO}`  ·  Cliente: `{ID_CLIENTE}`", "",
    ]
    for p in PASOS:
        lineas.append(f"## Paso `{p['paso']}`: {p['descripcion']}")
        lineas.append(f"- `{p['peticion']['metodo']} {p['peticion']['url']}`")
        lineas.append(f"- Respuesta: **HTTP {p['respuesta']['codigo']}** ({p['respuesta']['tiempoMs']} ms)")
        lineas.append("")
        lineas.append("```json")
        lineas.append(json.dumps(p["respuesta"]["body"], indent=2, ensure_ascii=False, default=str))
        lineas.append("```")
        lineas.append("")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    print(f"\nEvidencia guardada en:\n  {ruta_json}\n  {ruta_md}")


if __name__ == "__main__":
    main()
