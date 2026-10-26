"""Logica de negocio del modulo Cobranza. No depende de FastAPI."""
import uuid
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0.00")


class ErrorNegocio(Exception):
    def __init__(self, status, detalle, regla=None):
        super().__init__(detalle)
        self.status = status
        self.detalle = detalle
        self.regla = regla


def D(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fecha(v, solo_fecha=False):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d" if solo_fecha else "%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        base = v.strftime("%Y-%m-%d")
        return base if solo_fecha else base + " 00:00:00"
    s = str(v).replace("T", " ")
    if solo_fecha:
        return s[:10]
    return s[:19] if len(s) >= 19 else s[:10] + " 00:00:00"


def nuevo_id(prefijo):
    return f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"


def registrar_evento(db, id_entidad, tipo, usuario="sistema", modulo="COBRANZA"):
    """RN-CR-GEN-004 / CR-INT-10: trazabilidad de cada cambio de estado (registro local)."""
    db.ejecutar(
        "INSERT INTO EVENTO_AUDITORIA (idEvento, idEntidad, tipoEvento, `timestamp`, moduloEmisor, usuarioOperador) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (nuevo_id("EVT"), id_entidad, tipo, ahora(), modulo, usuario),
    )


# ------------------------------------------------------------------ CR-INT-06
def activar_obligacion(db, d):
    """CR-INT-06 (Desembolso a Cobranza). RN-COB-001: solo se cobran creditos desembolsados y activados."""
    cod = d["codCredito"]
    monto = D(d["montoAprobado"])
    moneda = d.get("moneda") or "PEN"
    cal = d.get("calendarioPagos") or []
    if monto <= 0:
        raise ErrorNegocio(422, "montoAprobado debe ser mayor a cero", "CR-INT-06")
    if moneda not in ("PEN", "USD"):
        raise ErrorNegocio(422, "moneda debe ser PEN o USD", "CR-INT-06")
    if not cal:
        raise ErrorNegocio(422, "calendarioPagos no puede estar vacio", "CR-INT-06")
    numeros = [int(c["numeroCuota"]) for c in cal]
    if min(numeros) < 1 or len(set(numeros)) != len(numeros):
        raise ErrorNegocio(422, "numeroCuota debe ser mayor a cero y no repetirse", "CR-INT-06")
    if any(D(c["montoCuota"]) <= 0 for c in cal):
        raise ErrorNegocio(422, "montoCuota debe ser mayor a cero", "CR-INT-06")
    if db.uno("SELECT codCredito FROM CREDITO WHERE codCredito = %s", (cod,)):
        raise ErrorNegocio(409, "El credito ya fue activado en Cobranza", "RN-COB-001")
    try:
        db.ejecutar(
            "INSERT INTO CREDITO (codCredito, idCliente, idSolicitud, montoAprobado, moneda, fechaDesembolso, estadoCredito) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (cod, d["idCliente"], d["idSolicitud"], monto, moneda, _fecha(d["fechaDesembolso"]), "ACTIVO"),
        )
        for c in sorted(cal, key=lambda x: int(x["numeroCuota"])):
            mc = D(c["montoCuota"])
            db.ejecutar(
                "INSERT INTO CUOTA (idCuota, codCredito, numeroCuota, fechaVencimiento, montoCuota, saldoPendiente, estadoCuota) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (nuevo_id("CU"), cod, int(c["numeroCuota"]), _fecha(c["fechaVencimiento"], True), mc, mc, "PENDIENTE"),
            )
        registrar_evento(db, cod, "OBLIGACION_ACTIVADA", usuario="DESEMBOLSO (CR-INT-06)")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return obtener_credito(db, cod)


# ------------------------------------------------------------------ consultas
def obtener_credito(db, cod):
    cred = db.uno("SELECT * FROM CREDITO WHERE codCredito = %s", (cod,))
    if not cred:
        raise ErrorNegocio(404, "Credito no encontrado en Cobranza", "RN-COB-001")
    filas = db.todos("SELECT * FROM CUOTA WHERE codCredito = %s ORDER BY numeroCuota", (cod,))
    cuotas = [{
        "idCuota": f["idCuota"], "numeroCuota": f["numeroCuota"],
        "fechaVencimiento": str(f["fechaVencimiento"])[:10],
        "montoCuota": D(f["montoCuota"]), "saldoPendiente": D(f["saldoPendiente"]),
        "estadoCuota": f["estadoCuota"],
    } for f in filas]
    return {
        "codCredito": cred["codCredito"], "idCliente": cred["idCliente"],
        "montoAprobado": D(cred["montoAprobado"]), "moneda": cred["moneda"],
        "fechaDesembolso": str(cred["fechaDesembolso"])[:19], "estadoCredito": cred["estadoCredito"],
        "saldoTotalPendiente": sum((c["saldoPendiente"] for c in cuotas), CERO),
        "cuotas": cuotas,
    }


def _resultado(db, id_pago, idempotente):
    p = db.uno("SELECT * FROM PAGO WHERE idPago = %s", (id_pago,))
    ap = db.uno(
        "SELECT a.idCuota, a.montoAplicado, c.numeroCuota, c.saldoPendiente, c.estadoCuota "
        "FROM APLICACION_PAGO a JOIN CUOTA c ON c.idCuota = a.idCuota WHERE a.idPago = %s", (id_pago,))
    cred = db.uno("SELECT estadoCredito FROM CREDITO WHERE codCredito = %s", (p["codCredito"],))
    aplicacion = None
    if ap:
        aplicacion = {"idCuota": ap["idCuota"], "numeroCuota": ap["numeroCuota"],
                      "montoAplicado": D(ap["montoAplicado"]),
                      "saldoPendienteCuota": D(ap["saldoPendiente"]), "estadoCuota": ap["estadoCuota"]}
    return {
        "idPago": p["idPago"], "referenciaTransaccion": p["referenciaTransaccion"],
        "estado": p["estadoConfirmacion"], "idempotente": idempotente, "motivo": None,
        "codCredito": p["codCredito"], "idCanal": p["idCanal"], "montoPago": D(p["montoPago"]),
        "fechaHora": str(p["fechaHora"])[:19], "aplicacion": aplicacion,
        "estadoCredito": cred["estadoCredito"],
    }


# ------------------------------------------------------------------ CR-INT-08 y CR-INT-07
def registrar_pago(db, d, cuentas):
    """CR-INT-08 (Home Banking a Cobranza). Aplica RN-COB-001/002/003/004/006/009/011/012 y RN-INT-CR-006."""
    ref = d["referenciaTransaccion"]
    previo = db.uno("SELECT idPago FROM PAGO WHERE referenciaTransaccion = %s", (ref,))
    if previo:  # idempotencia: el mismo identificador no genera un segundo pago
        return _resultado(db, previo["idPago"], True)

    monto = D(d["montoPago"])
    if monto <= 0:
        raise ErrorNegocio(422, "montoPago debe ser mayor a cero", "RN-COB-004")
    id_canal = d.get("idCanal") or "HB"
    if not db.uno("SELECT idCanal FROM CANAL_PAGO WHERE idCanal = %s", (id_canal,)):
        raise ErrorNegocio(422, f"Canal '{id_canal}' no habilitado. Solo Home Banking (HB) esta confirmado", "RN-COB-002")
    cred = db.uno("SELECT * FROM CREDITO WHERE codCredito = %s", (d["codCredito"],))
    if not cred:
        raise ErrorNegocio(404, "Credito no encontrado en Cobranza", "RN-COB-001")
    if cred["idCliente"] != d["codCliente"]:
        raise ErrorNegocio(403, "El credito no pertenece al cliente indicado", "CR-INT-08")
    if cred["estadoCredito"] != "ACTIVO":
        raise ErrorNegocio(409, f"El credito esta {cred['estadoCredito']}; solo se cobra un credito ACTIVO", "RN-COB-001")
    cuota = db.uno(
        "SELECT * FROM CUOTA WHERE codCredito = %s AND saldoPendiente > 0 ORDER BY numeroCuota LIMIT 1",
        (d["codCredito"],))
    if not cuota:
        raise ErrorNegocio(409, "El credito no tiene cuotas pendientes", "RN-COB-001")
    saldo = D(cuota["saldoPendiente"])
    if monto > saldo:
        raise ErrorNegocio(
            422, f"El monto {monto} excede el saldo de la cuota {saldo}. "
                 "El tratamiento del excedente esta pendiente de definicion del Comite", "RN-COB-011")

    id_pago = nuevo_id("PAG")
    try:
        db.ejecutar(
            "INSERT INTO PAGO (idPago, codCredito, idCanal, fechaHora, montoPago, referenciaTransaccion, estadoConfirmacion) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (id_pago, d["codCredito"], id_canal, ahora(), monto, ref, "PENDIENTE"))
        registrar_evento(db, id_pago, "PAGO_REGISTRADO", usuario="HOME BANKING (CR-INT-08)")
        db.commit()
    except Exception:
        db.rollback()
        raise

    # CR-INT-07: solicitar el cargo a Cuentas. Cobranza nunca mueve el dinero por si misma.
    estado, motivo = cuentas.cargar(d["codCredito"], d["cuentaOrigen"], monto, cred["moneda"], ref)

    try:
        if estado == "CONFIRMADO":
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s", ("CONFIRMADO", id_pago))
            db.ejecutar(
                "INSERT INTO APLICACION_PAGO (idAplicacion, idPago, idCuota, montoAplicado) VALUES (%s, %s, %s, %s)",
                (nuevo_id("APL"), id_pago, cuota["idCuota"], monto))
            nuevo_saldo = saldo - monto
            nuevo_estado = "PAGADA" if nuevo_saldo == 0 else "PARCIAL"
            db.ejecutar("UPDATE CUOTA SET saldoPendiente = %s, estadoCuota = %s WHERE idCuota = %s",
                        (nuevo_saldo, nuevo_estado, cuota["idCuota"]))
            registrar_evento(db, id_pago, "PAGO_APLICADO")
            registrar_evento(db, cuota["idCuota"], "CUOTA_" + nuevo_estado)
            pend = db.uno("SELECT COUNT(*) AS n FROM CUOTA WHERE codCredito = %s AND saldoPendiente > 0",
                          (d["codCredito"],))
            if pend["n"] == 0:
                db.ejecutar("UPDATE CREDITO SET estadoCredito = %s WHERE codCredito = %s",
                            ("CANCELADO", d["codCredito"]))
                registrar_evento(db, d["codCredito"], "CREDITO_CANCELADO")
        elif estado == "RECHAZADO":  # RN-COB-009: la cuota no se cierra sin confirmacion
            db.ejecutar("UPDATE PAGO SET estadoConfirmacion = %s WHERE idPago = %s", ("RECHAZADO", id_pago))
            registrar_evento(db, id_pago, "PAGO_RECHAZADO")
        else:  # sin respuesta: queda PENDIENTE, no se cierra la cuota ni se reintenta el cargo
            registrar_evento(db, id_pago, "PAGO_SIN_CONFIRMAR")
        db.commit()
    except Exception:
        db.rollback()
        raise
    r = _resultado(db, id_pago, False)
    r["motivo"] = motivo
    return r


def comprobante(db, ref):
    """RN-COB-012: trazabilidad del origen del pago."""
    p = db.uno(
        "SELECT p.*, c.nombreCanal FROM PAGO p JOIN CANAL_PAGO c ON c.idCanal = p.idCanal "
        "WHERE p.referenciaTransaccion = %s", (ref,))
    if not p:
        raise ErrorNegocio(404, "Pago no encontrado", "RN-COB-012")
    if p["estadoConfirmacion"] != "CONFIRMADO":
        raise ErrorNegocio(409, f"El pago esta {p['estadoConfirmacion']}; solo se emite comprobante de pagos confirmados", "RN-COB-009")
    r = _resultado(db, p["idPago"], False)
    cred = obtener_credito(db, p["codCredito"])
    return {
        "numeroOperacion": ref, "fechaHora": r["fechaHora"], "canal": p["nombreCanal"],
        "codCredito": p["codCredito"], "montoPagado": r["montoPago"],
        "cuotaNumero": r["aplicacion"]["numeroCuota"],
        "saldoRestanteCuota": r["aplicacion"]["saldoPendienteCuota"],
        "saldoRestanteCredito": cred["saldoTotalPendiente"], "estadoCredito": cred["estadoCredito"],
    }


def historial_pagos(db, cod):
    obtener_credito(db, cod)
    filas = db.todos("SELECT p.*, c.nombreCanal FROM PAGO p JOIN CANAL_PAGO c ON c.idCanal = p.idCanal "
                     "WHERE p.codCredito = %s ORDER BY p.fechaHora DESC, p.idPago", (cod,))
    return [{"idPago": f["idPago"], "referenciaTransaccion": f["referenciaTransaccion"],
             "fechaHora": str(f["fechaHora"])[:19], "canal": f["nombreCanal"],
             "montoPago": D(f["montoPago"]), "estado": f["estadoConfirmacion"]} for f in filas]


# ------------------------------------------------------------------ mora (valor recibido)
def _cuota_por_numero(db, cod, numero):
    cuota = db.uno("SELECT * FROM CUOTA WHERE codCredito = %s AND numeroCuota = %s", (cod, numero))
    if not cuota:
        raise ErrorNegocio(404, "Cuota no encontrada", "RN-COB-010")
    return cuota


def registrar_mora(db, cod, numero, dias_atraso, monto_calculado, origen="CORE (simulado)"):
    """Registra una mora RECIBIDA. La formula y quien la calcula estan pendientes del Comite (RN-COB-005):
    Cobranza no calcula ni asume tasa; solo guarda el valor que le llega."""
    cuota = _cuota_por_numero(db, cod, numero)
    if cuota["estadoCuota"] == "PAGADA":
        raise ErrorNegocio(409, "La cuota ya esta pagada; no admite mora", "RN-COB-010")
    monto = D(monto_calculado)
    if monto < 0 or int(dias_atraso) < 0:
        raise ErrorNegocio(422, "diasAtraso y montoCalculado no pueden ser negativos", "RN-COB-005")
    saldo = D(cuota["saldoPendiente"])
    prev = db.uno("SELECT idMora, montoCalculado FROM MORA WHERE idCuota = %s AND vigente = %s",
                  (cuota["idCuota"], 1))
    id_mora = nuevo_id("MOR")
    try:
        if prev:  # un recalculo reemplaza al vigente y conserva el historial
            saldo = max(saldo - D(prev["montoCalculado"]), CERO)
            db.ejecutar("UPDATE MORA SET vigente = %s WHERE idMora = %s", (0, prev["idMora"]))
        db.ejecutar(
            "INSERT INTO MORA (idMora, idCuota, diasAtraso, montoCalculado, fechaCalculo, vigente) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (id_mora, cuota["idCuota"], int(dias_atraso), monto, ahora(), 1))
        saldo = saldo + monto
        db.ejecutar("UPDATE CUOTA SET saldoPendiente = %s WHERE idCuota = %s", (saldo, cuota["idCuota"]))
        registrar_evento(db, cuota["idCuota"], "MORA_REGISTRADA", usuario=origen)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"idMora": id_mora, "codCredito": cod, "numeroCuota": numero, "diasAtraso": int(dias_atraso),
            "montoCalculado": monto, "vigente": True, "saldoPendienteCuota": saldo}


def historial_mora(db, cod, numero):
    cuota = _cuota_por_numero(db, cod, numero)
    filas = db.todos("SELECT * FROM MORA WHERE idCuota = %s ORDER BY fechaCalculo, idMora", (cuota["idCuota"],))
    return [{"idMora": f["idMora"], "diasAtraso": f["diasAtraso"], "montoCalculado": D(f["montoCalculado"]),
             "fechaCalculo": str(f["fechaCalculo"])[:19], "vigente": bool(f["vigente"])} for f in filas]


def auditoria(db, id_entidad=None, limite=50):
    if id_entidad:
        filas = db.todos("SELECT * FROM EVENTO_AUDITORIA WHERE idEntidad = %s ORDER BY `timestamp` DESC, idEvento LIMIT %s",
                         (id_entidad, int(limite)))
    else:
        filas = db.todos("SELECT * FROM EVENTO_AUDITORIA ORDER BY `timestamp` DESC, idEvento LIMIT %s", (int(limite),))
    return [{"idEvento": f["idEvento"], "idEntidad": f["idEntidad"], "tipoEvento": f["tipoEvento"],
             "timestamp": str(f["timestamp"])[:19], "moduloEmisor": f["moduloEmisor"],
             "usuarioOperador": f["usuarioOperador"]} for f in filas]
