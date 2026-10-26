"""Bus de Servicios simulado (Parte 3): proxy simple que enruta `/cobranza/*` hacia la API de
Cobranza y `/cuentas/*` hacia el simulador de Cuentas, reenviando metodo, query, headers (X-API-Key,
X-Token-Seguridad, etc.) y cuerpo tal cual, y registrando cada llamada (hora, origen, destino,
codigo de respuesta). Asi se cumple RNF-04: toda la comunicacion entre modulos pasa por el Bus, nunca
de forma directa.

Ejecutar: uvicorn simuladores.bus_app:app --port 8080   (desde la carpeta cobranza/)
"""
from datetime import datetime

import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI(title="Bus de Servicios (simulado)", version="0.1.0")

# Puertos por defecto; override con las variables de entorno si alguno esta ocupado.
DESTINOS = {
    "cobranza": os.environ.get("BUS_DESTINO_COBRANZA", "http://127.0.0.1:8000"),
    "cuentas": os.environ.get("BUS_DESTINO_CUENTAS", "http://127.0.0.1:8001"),
}

_HEADERS_NO_REENVIAR = {"host", "content-length"}

REGISTRO = []  # RNF-04: bitacora en memoria de cada llamada enrutada (hora, origen, destino, codigo)
_MAX_REGISTRO = 1000


@app.get("/bus/salud")
def salud():
    return {"estado": "ok", "destinos": DESTINOS}


@app.get("/bus/registro")
def ver_registro(limite: int = 50):
    return REGISTRO[-limite:]


@app.api_route("/{destino}/{resto:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def enrutar(destino: str, resto: str, request: Request):
    entrada = {
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "origen": request.client.host if request.client else "desconocido",
        "destino": destino, "ruta": f"/{resto}", "metodo": request.method,
    }
    base = DESTINOS.get(destino)
    if not base:
        entrada["codigo"] = 404
        REGISTRO.append(entrada)
        return Response(
            content=f'{{"detalle": "El Bus no conoce el destino \\"{destino}\\"", "regla": "RNF-04"}}',
            status_code=404, media_type="application/json")

    url = f"{base}/{resto}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HEADERS_NO_REENVIAR}
    cuerpo = await request.body()
    try:
        async with httpx.AsyncClient(timeout=30) as cliente:
            r = await cliente.request(request.method, url, params=request.query_params,
                                       headers=headers, content=cuerpo)
    except Exception as e:
        entrada["codigo"] = 502
        entrada["error"] = str(e)
        REGISTRO[:] = REGISTRO[-(_MAX_REGISTRO - 1):] + [entrada]
        return Response(
            content=f'{{"detalle": "El Bus no pudo contactar a {destino}: {e}", "regla": "RNF-04"}}',
            status_code=502, media_type="application/json")

    entrada["codigo"] = r.status_code
    REGISTRO[:] = REGISTRO[-(_MAX_REGISTRO - 1):] + [entrada]
    print(f"[BUS] {entrada['hora']} {request.method} /{destino}/{resto} -> {r.status_code}")
    return Response(content=r.content, status_code=r.status_code,
                     media_type=r.headers.get("content-type"))
