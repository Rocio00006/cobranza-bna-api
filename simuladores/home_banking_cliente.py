"""Script CLIENTE (no servidor) que simula Home Banking: envia CR-INT-08 a Cobranza, con su
X-Token-Seguridad (RF-COB-004), SIEMPRE a traves del Bus de Servicios (RNF-04).

Uso como script: python simuladores/home_banking_cliente.py
"""
import os
import sys

import httpx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta cobranza/
sys.path.insert(0, RAIZ)
from app.db import cargar_env  # noqa: E402

BUS_URL = os.environ.get("BUS_URL", "http://127.0.0.1:8090")


def pagar(api_key, token_seguridad, codCliente, codCredito, montoPago, cuentaOrigen,
          referenciaTransaccion, idCanal="HB", timeout=15):
    """CR-INT-08: Home Banking -> Cobranza, via Bus (/cobranza/cr-int-08/pagos)."""
    body = {
        "codCliente": codCliente, "codCredito": codCredito, "montoPago": montoPago,
        "cuentaOrigen": cuentaOrigen, "referenciaTransaccion": referenciaTransaccion, "idCanal": idCanal,
    }
    headers = {"X-API-Key": api_key, "X-Token-Seguridad": token_seguridad}
    return httpx.post(f"{BUS_URL}/cobranza/cr-int-08/pagos", headers=headers, json=body, timeout=timeout)


if __name__ == "__main__":
    cargar_env(os.path.join(RAIZ, ".env"))
    api_key = os.environ.get("API_KEY_INTEGRACION_BUS", "")
    if not api_key:
        sys.exit("Falta API_KEY_INTEGRACION_BUS en .env")
    r = pagar(api_key, "TOKEN-DEMO-HOMEBANKING", "CLI-DESEMB-01", "CR-DESEMB-01", 150.00,
              "AH-001-123456", "OP-HB-DEMO-0001")
    print(r.status_code, r.text)
