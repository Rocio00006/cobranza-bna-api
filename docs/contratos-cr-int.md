# Contratos CR-INT, tal como los usa Cobranza

Documento para compartir con los equipos de Desembolso, Cuentas, Home Banking y Seguridad: el JSON
exacto de petición y respuesta de cada interfaz, según está implementado hoy en el módulo Cobranza
(`app/main.py`, `app/servicio.py`, `app/cuentas.py`).

Los campos marcados **PROPUESTA** no están en la matriz CR-INT oficial de Fase II: Cobranza los usa,
pero quedan **a coordinar con el Comité de Créditos** (regla RN-CR-GEN-007) antes de darlos por
definitivos. Todas las integraciones son REST/JSON vía el Bus de Servicios (RNF-04): ningún módulo
llama a otro de forma directa (ver `simuladores/bus_app.py`).

---

## CR-INT-06 — Desembolso → Cobranza

`POST /cr-int-06/obligaciones` (vía Bus: `POST /cobranza/cr-int-06/obligaciones`)
Header: `X-API-Key` (rol `INTEGRACION_BUS`).

**Campos oficiales de la matriz:** `codCredito`, `fechaDesembolso`, `monto` (→ `montoAprobado`),
`calendarioPagos`.
**Campos PROPUESTA:** `idCliente`, `idSolicitud`, `moneda`.

### Petición
```json
{
  "codCredito": "CR-0001",
  "idCliente": "CLI-0001",
  "idSolicitud": "SOL-0001",
  "montoAprobado": 1200.00,
  "moneda": "PEN",
  "fechaDesembolso": "2026-10-05T10:00:00",
  "calendarioPagos": [
    {"numeroCuota": 1, "fechaVencimiento": "2026-11-05", "montoCuota": 400.00},
    {"numeroCuota": 2, "fechaVencimiento": "2026-12-05", "montoCuota": 400.00},
    {"numeroCuota": 3, "fechaVencimiento": "2027-01-05", "montoCuota": 400.00}
  ]
}
```

### Respuesta (201)
```json
{
  "codCredito": "CR-0001",
  "idCliente": "CLI-0001",
  "montoAprobado": 1200.00,
  "moneda": "PEN",
  "fechaDesembolso": "2026-10-05 10:00:00",
  "estadoCredito": "AL_DIA",
  "saldoTotalPendiente": 1200.00,
  "cuotas": [
    {
      "idCuota": "CU-9B2F231E",
      "numeroCuota": 1,
      "fechaVencimiento": "2026-11-05",
      "montoCuota": 400.00,
      "saldoPendiente": 400.00,
      "moraPendiente": 0.00,
      "totalAdeudado": 400.00,
      "estadoCuota": "PENDIENTE"
    }
  ]
}
```
`estadoCredito` (`AL_DIA` / `EN_MORA` / `CANCELADO`) y los campos de cuota `moraPendiente` /
`totalAdeudado` son un catálogo y un desglose **PROPUESTA** de Cobranza (RF-COB-007, RF-COB-003), no
forman parte del payload que envía Desembolso.

### Errores de negocio (forma común a toda la API)
```json
{"detalle": "El credito ya fue activado en Cobranza", "regla": "RN-COB-001"}
```

---

## CR-INT-07 — Cobranza → Cuentas

Llamado interno (`app/cuentas.py:CuentasHTTP`), vía Bus: `POST /cuentas/cargos` y
`GET /cuentas/cargos/{idOperacion}` (ver `simuladores/cuentas_app.py`). Sin header de rol: Cuentas no
participa de la autenticación por rol de Cobranza (es una interfaz entre módulos, no un cliente externo).

**Campos oficiales de la matriz:** `codCredito`, `numCuentaAhorro`, `montoCuota`, `moneda`.
**Campo PROPUESTA:** `idOperacion` (justificado por RN-INT-CR-006, idempotencia).

### Petición — `POST /cargos`
```json
{
  "codCredito": "CR-0001",
  "numCuentaAhorro": "AH-001-123456",
  "montoCuota": 150.00,
  "moneda": "PEN",
  "idOperacion": "OP-0001"
}
```

### Respuesta
```json
{
  "idOperacion": "OP-0001",
  "estado": "CONFIRMADO",
  "confirmado": true,
  "mensaje": "Cargo de 150.00 PEN aplicado a AH-001-123456"
}
```
`estado` puede ser `CONFIRMADO` o `RECHAZADO`; `confirmado` (booleano) y `mensaje` son el formato que
Cobranza sabe interpretar (`app/cuentas.py`), a coordinar con el formato real que publique Cuentas.

### Consulta posterior — `GET /cargos/{idOperacion}` (RF-COB-011, para resolver un pago PENDIENTE)
```json
{
  "idOperacion": "OP-0001",
  "estado": "CONFIRMADO",
  "confirmado": true,
  "mensaje": "Cargo de 150.00 PEN aplicado a AH-001-123456"
}
```

---

## CR-INT-08 — Home Banking → Cobranza

`POST /cr-int-08/pagos` (vía Bus: `POST /cobranza/cr-int-08/pagos`)
Headers: `X-API-Key` (rol `INTEGRACION_BUS`) y `X-Token-Seguridad` (RF-COB-004, **PROPUESTA**).

**Campos oficiales de la matriz:** `codCliente`, `codCredito`, `montoPago`, `cuentaOrigen`.
**Campos PROPUESTA:** `referenciaTransaccion`, `idCanal`.

### Petición
```json
{
  "codCliente": "CLI-0001",
  "codCredito": "CR-0001",
  "montoPago": 150.00,
  "cuentaOrigen": "AH-001-123456",
  "referenciaTransaccion": "OP-0001",
  "idCanal": "HB"
}
```

### Respuesta (200)
```json
{
  "idPago": "PAG-36D9DC4E",
  "referenciaTransaccion": "OP-0001",
  "estado": "CONFIRMADO",
  "idempotente": false,
  "motivo": "Cargo confirmado (Cuentas simulado)",
  "codCredito": "CR-0001",
  "idCanal": "HB",
  "montoPago": 150.00,
  "fechaHora": "2026-10-25 20:15:40",
  "aplicacion": {
    "idCuota": "CU-9B2F231E",
    "numeroCuota": 1,
    "montoAplicado": 150.00,
    "montoAplicadoMora": 0.00,
    "montoAplicadoCapital": 150.00,
    "saldoPendienteCuota": 250.00,
    "moraPendienteCuota": 0.00,
    "estadoCuota": "PARCIAL"
  },
  "estadoCredito": "AL_DIA"
}
```
`estado` también puede ser `RECHAZADO`, `PENDIENTE` (Cuentas no respondió, INC-01) o
`REQUIERE_REVISION` (Cuentas confirmó pero la cuota cambió mientras el pago esperaba, RF-COB-011).
`montoAplicadoMora` / `montoAplicadoCapital` (RF-COB-008/013) son desglose **PROPUESTA** de Cobranza.

### Rechazo por token de Seguridad (401, RF-COB-004)
```json
{"detalle": "Token de Seguridad invalido", "regla": "RF-COB-004"}
```

---

## CR-INT-10 — Cobranza → Seguridad/Auditoría

`GET /auditoria` (vía Bus: `GET /cobranza/auditoria`), rol `COBRANZA_LEER`. Hoy el registro queda
**local** en `EVENTO_AUDITORIA`; el envío a un servicio de Seguridad/Auditoría real está pendiente
(ver README, "Qué falta").

**Campos oficiales de la matriz:** `timestamp`, `moduloEmisor`, `usuario/operador` (→
`usuarioOperador`), `tipoEvento`, `resultado`. Sin campos PROPUESTA adicionales: Cobranza no agrega
nada fuera de lo que pide la matriz para esta interfaz.

### Respuesta
```json
[
  {
    "idEvento": "EVT-9F6C20EE",
    "idEntidad": "CR-0001",
    "tipoEvento": "OBLIGACION_ACTIVADA",
    "timestamp": "2026-10-25 21:08:01",
    "moduloEmisor": "COBRANZA",
    "usuarioOperador": "INTEGRACION_BUS",
    "resultado": "EXITOSO"
  }
]
```
`usuarioOperador` es el rol (`X-API-Key`) que hizo la llamada HTTP que originó el evento
(RN-CR-GEN-004). `resultado` es `EXITOSO` por defecto, o `RECHAZADO` / `PENDIENTE` / `REVISION` según
el evento (ver `CLAUDE.md`, sección "Cambios respecto al diccionario de datos de Fase II").
`idEntidad` no está en la matriz oficial con ese nombre exacto; es el identificador (código de
crédito, cuota, pago, etc.) al que se refiere el evento — **PROPUESTA** a confirmar con el Comité.
