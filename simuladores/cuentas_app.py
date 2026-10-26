"""Simulador HTTP independiente del modulo Cuentas (CR-INT-07), para la Parte 3: probar la
integracion real por red (no llamadas directas a servicio.py). Corre en su propio puerto (8001).

Maneja saldos ficticios por cuenta en memoria, es idempotente por idOperacion (una misma operacion
repetida devuelve siempre el mismo resultado, sin volver a debitar) y tiene una cuenta especial para
simular demora / falta de respuesta (INC-01): "SIN-RESPUESTA" duerme mas que el timeout por defecto
del cliente HTTP de Cobranza (CuentasHTTP, 5s), para que ese cliente experimente un timeout real.

Ejecutar: uvicorn simuladores.cuentas_app:app --port 8001   (desde la carpeta cobranza/)
"""
from decimal import Decimal
import time

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Cuentas (simulador HTTP, CR-INT-07)", version="0.1.0")

SALDO_DEFAULT = Decimal("100000.00")

# Cuentas ficticias precargadas para la demo de integracion (Parte 3).
SALDOS = {
    "AH-001-123456": Decimal("100000.00"),
    "AH-SIN-FONDOS": Decimal("10.00"),
}

# INC-01: cuentas que simulan demora. El valor es cuantos segundos duerme el simulador ANTES de
# responder (mas que el timeout de 5s de app/cuentas.py:CuentasHTTP, para forzar un timeout real).
DEMORA_SEGUNDOS = {
    "SIN-RESPUESTA": 7,
}

OPERACIONES = {}  # idOperacion -> resultado ya resuelto (idempotencia)


class CargoIn(BaseModel):
    codCredito: str
    numCuentaAhorro: str
    montoCuota: Decimal
    moneda: str = "PEN"
    idOperacion: str


@app.get("/salud")
def salud():
    return {"estado": "ok", "cuentasRegistradas": len(SALDOS), "operacionesProcesadas": len(OPERACIONES)}


@app.post("/cargos", status_code=201)
def crear_cargo(body: CargoIn):
    """CR-INT-07: Cobranza -> Cuentas. Idempotente por idOperacion."""
    if body.idOperacion in OPERACIONES:
        return OPERACIONES[body.idOperacion]

    demora = DEMORA_SEGUNDOS.get(body.numCuentaAhorro)
    if demora:
        time.sleep(demora)

    saldo = SALDOS.get(body.numCuentaAhorro, SALDO_DEFAULT)
    monto = Decimal(str(body.montoCuota))
    if saldo >= monto:
        SALDOS[body.numCuentaAhorro] = saldo - monto
        resultado = {
            "idOperacion": body.idOperacion, "estado": "CONFIRMADO", "confirmado": True,
            "mensaje": f"Cargo de {monto} {body.moneda} aplicado a {body.numCuentaAhorro}",
        }
    else:
        resultado = {
            "idOperacion": body.idOperacion, "estado": "RECHAZADO", "confirmado": False,
            "mensaje": f"Fondos insuficientes en {body.numCuentaAhorro} (saldo {saldo}, requerido {monto})",
        }
    OPERACIONES[body.idOperacion] = resultado
    return resultado


@app.get("/cargos/{idOperacion}")
def consultar_cargo(idOperacion: str):
    """Consulta posterior de una operacion por idOperacion (usado por RF-COB-011 al resolver pagos
    PENDIENTE, en vez de reintentar el cargo)."""
    resultado = OPERACIONES.get(idOperacion)
    if resultado:
        return resultado
    return {"idOperacion": idOperacion, "estado": "NO_ENCONTRADO", "confirmado": False,
            "mensaje": "La operacion no fue registrada en Cuentas"}


@app.get("/saldos/{numCuentaAhorro}")
def ver_saldo(numCuentaAhorro: str):
    return {"numCuentaAhorro": numCuentaAhorro, "saldo": SALDOS.get(numCuentaAhorro, SALDO_DEFAULT)}


@app.post("/admin/saldos/{numCuentaAhorro}")
def fijar_saldo(numCuentaAhorro: str, saldo: Decimal):
    """Utilidad de prueba: fija el saldo de una cuenta ficticia para armar escenarios."""
    SALDOS[numCuentaAhorro] = saldo
    return {"numCuentaAhorro": numCuentaAhorro, "saldo": saldo}
