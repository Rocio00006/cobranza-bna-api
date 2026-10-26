"""Cliente del modulo Cuentas (CR-INT-07). Por defecto SIMULADO: no hay conexion con el modulo real."""
import os


class CuentasSimulado:
    """Simula la respuesta de Cuentas. Se controla con el valor de cuentaOrigen para poder demostrar casos."""

    def cargar(self, codCredito, cuentaOrigen, monto, moneda, referencia):
        if cuentaOrigen == "SIN-FONDOS":
            return "RECHAZADO", "Fondos insuficientes (Cuentas simulado)"
        if cuentaOrigen == "SIN-RESPUESTA":
            return "SIN_RESPUESTA", "Cuentas no respondio (simulado)"
        return "CONFIRMADO", "Cargo confirmado (Cuentas simulado)"

    def consultar(self, referencia):
        """RF-COB-011 / INC-01: consulta posterior del estado de una operacion por su idOperacion
        (referenciaTransaccion), para resolver un pago que quedo PENDIENTE sin repetir el cargo
        (RN-COB-009). Simulado: por defecto ya hay respuesta (CONFIRMADO), para poder demostrar que un
        pago que quedo "SIN-RESPUESTA" se resuelve al consultarlo de nuevo. La referencia admite sufijos
        para demostrar los otros desenlaces."""
        if referencia.endswith("-RECHAZA"):
            return "RECHAZADO", "Fondos insuficientes al consultar (Cuentas simulado)"
        if referencia.endswith("-SIGUESIN"):
            return "SIN_RESPUESTA", "Cuentas aun no responde (simulado)"
        return "CONFIRMADO", "Cargo confirmado al consultar (Cuentas simulado)"


class CuentasHTTP:
    """Llama al modulo Cuentas real si se define CUENTAS_URL. Usa los campos de CR-INT-07.
    El formato de la respuesta debe acordarse con el equipo de Cuentas."""

    def __init__(self, url, timeout=5):
        self.url = url
        self.timeout = timeout

    def cargar(self, codCredito, cuentaOrigen, monto, moneda, referencia):
        import httpx
        try:
            r = httpx.post(
                self.url,
                json={"codCredito": codCredito, "numCuentaAhorro": cuentaOrigen,
                      "montoCuota": float(monto), "moneda": moneda, "idOperacion": referencia},
                timeout=self.timeout,
            )
        except Exception:
            return "SIN_RESPUESTA", "Cuentas no respondio"
        if r.status_code >= 500:
            return "SIN_RESPUESTA", "Cuentas devolvio un error del servidor"
        try:
            data = r.json()
        except Exception:
            return "SIN_RESPUESTA", "Respuesta de Cuentas no valida"
        ok = data.get("confirmado") is True or str(data.get("estado", "")).upper() in ("CONFIRMADO", "OK", "EXITOSO")
        return ("CONFIRMADO" if ok else "RECHAZADO"), str(data.get("mensaje") or data.get("detalle") or "")

    def consultar(self, referencia):
        """RF-COB-011 / INC-01. Formato de la consulta por acordar con el equipo de Cuentas; aqui se
        asume un GET por idOperacion."""
        import httpx
        try:
            r = httpx.get(f"{self.url}/{referencia}", timeout=self.timeout)
        except Exception:
            return "SIN_RESPUESTA", "Cuentas no respondio"
        if r.status_code >= 500:
            return "SIN_RESPUESTA", "Cuentas devolvio un error del servidor"
        try:
            data = r.json()
        except Exception:
            return "SIN_RESPUESTA", "Respuesta de Cuentas no valida"
        estado = str(data.get("estado", "")).upper()
        if data.get("confirmado") is True or estado in ("CONFIRMADO", "OK", "EXITOSO"):
            return "CONFIRMADO", str(data.get("mensaje") or data.get("detalle") or "")
        if estado in ("RECHAZADO", "FALLIDO"):
            return "RECHAZADO", str(data.get("mensaje") or data.get("detalle") or "")
        return "SIN_RESPUESTA", "Cuentas aun no tiene una respuesta definitiva"


def crear_cliente_cuentas():
    url = os.environ.get("CUENTAS_URL", "").strip()
    return CuentasHTTP(url) if url else CuentasSimulado()
