"""Script CLIENTE (no servidor) que simula el modulo Desembolso: envia CR-INT-06 a Cobranza, SIEMPRE
a traves del Bus de Servicios (RNF-04), nunca llamando a Cobranza directamente.

Uso como script: python simuladores/desembolso_cliente.py
"""
import os
import sys

import httpx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta cobranza/
sys.path.insert(0, RAIZ)
from app.db import cargar_env  # noqa: E402

BUS_URL = os.environ.get("BUS_URL", "http://127.0.0.1:8090")


def activar_obligacion(api_key, codCredito, idCliente, idSolicitud, montoAprobado, calendarioPagos,
                        moneda="PEN", fechaDesembolso="2026-10-05T10:00:00", timeout=15):
    """CR-INT-06: Desembolso -> Cobranza, via Bus (/cobranza/cr-int-06/obligaciones)."""
    body = {
        "codCredito": codCredito, "idCliente": idCliente, "idSolicitud": idSolicitud,
        "montoAprobado": montoAprobado, "moneda": moneda, "fechaDesembolso": fechaDesembolso,
        "calendarioPagos": calendarioPagos,
    }
    return httpx.post(f"{BUS_URL}/cobranza/cr-int-06/obligaciones",
                       headers={"X-API-Key": api_key}, json=body, timeout=timeout)


if __name__ == "__main__":
    cargar_env(os.path.join(RAIZ, ".env"))
    api_key = os.environ.get("API_KEY_INTEGRACION_BUS", "")
    if not api_key:
        sys.exit("Falta API_KEY_INTEGRACION_BUS en .env")
    r = activar_obligacion(
        api_key, "CR-DESEMB-01", "CLI-DESEMB-01", "SOL-DESEMB-01", 500.00,
        [{"numeroCuota": 1, "fechaVencimiento": "2026-11-05", "montoCuota": 500.00}])
    print(r.status_code, r.text)
