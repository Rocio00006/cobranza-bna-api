# Prueba de integracion por red (Bus de Servicios) — 2026-10-25

Credito de prueba: `CR-INTEG-213034`  ·  Cliente: `CLI-INTEG-213034`

## Paso `1-activar`: Desembolso activa la obligacion (CR-INT-06)
- `POST http://127.0.0.1:8090/cobranza/cr-int-06/obligaciones`
- Respuesta: **HTTP 201** (1830.9 ms)

```json
{
  "codCredito": "CR-INTEG-213034",
  "idCliente": "CLI-INTEG-213034",
  "montoAprobado": 1000.0,
  "moneda": "PEN",
  "fechaDesembolso": "2026-10-05 10:00:00",
  "estadoCredito": "AL_DIA",
  "saldoTotalPendiente": 1000.0,
  "cuotas": [
    {
      "idCuota": "CU-7DB6C241",
      "numeroCuota": 1,
      "fechaVencimiento": "2026-11-05",
      "montoCuota": 1000.0,
      "saldoPendiente": 1000.0,
      "moraPendiente": 0.0,
      "totalAdeudado": 1000.0,
      "estadoCuota": "PENDIENTE"
    }
  ]
}
```

## Paso `pago`: Home Banking paga parcial (CR-INT-08)
- `POST http://127.0.0.1:8090/cobranza/cr-int-08/pagos`
- Respuesta: **HTTP 200** (2509.8 ms)

```json
{
  "idPago": "PAG-BEA743F9",
  "referenciaTransaccion": "OP-INTEG-1",
  "estado": "CONFIRMADO",
  "idempotente": false,
  "motivo": "Cargo de 150.0 PEN aplicado a AH-001-123456",
  "codCredito": "CR-INTEG-213034",
  "idCanal": "HB",
  "montoPago": 150.0,
  "fechaHora": "2026-10-25 21:30:40",
  "aplicacion": {
    "idCuota": "CU-7DB6C241",
    "numeroCuota": 1,
    "montoAplicado": 150.0,
    "montoAplicadoMora": 0.0,
    "montoAplicadoCapital": 150.0,
    "saldoPendienteCuota": 850.0,
    "moraPendienteCuota": 0.0,
    "estadoCuota": "PARCIAL"
  },
  "estadoCredito": "AL_DIA"
}
```

## Paso `pago`: Home Banking repite el mismo pago (idempotencia)
- `POST http://127.0.0.1:8090/cobranza/cr-int-08/pagos`
- Respuesta: **HTTP 200** (1262.8 ms)

```json
{
  "idPago": "PAG-BEA743F9",
  "referenciaTransaccion": "OP-INTEG-1",
  "estado": "CONFIRMADO",
  "idempotente": true,
  "motivo": null,
  "codCredito": "CR-INTEG-213034",
  "idCanal": "HB",
  "montoPago": 150.0,
  "fechaHora": "2026-10-25 21:30:40",
  "aplicacion": {
    "idCuota": "CU-7DB6C241",
    "numeroCuota": 1,
    "montoAplicado": 150.0,
    "montoAplicadoMora": 0.0,
    "montoAplicadoCapital": 150.0,
    "saldoPendienteCuota": 850.0,
    "moraPendienteCuota": 0.0,
    "estadoCuota": "PARCIAL"
  },
  "estadoCredito": "AL_DIA"
}
```

## Paso `pago`: Pago con fondos insuficientes en Cuentas
- `POST http://127.0.0.1:8090/cobranza/cr-int-08/pagos`
- Respuesta: **HTTP 200** (2279.3 ms)

```json
{
  "idPago": "PAG-EFB3D10B",
  "referenciaTransaccion": "OP-INTEG-2",
  "estado": "RECHAZADO",
  "idempotente": false,
  "motivo": "Fondos insuficientes en AH-SIN-FONDOS (saldo 10.00, requerido 50.0)",
  "codCredito": "CR-INTEG-213034",
  "idCanal": "HB",
  "montoPago": 50.0,
  "fechaHora": "2026-10-25 21:30:44",
  "aplicacion": null,
  "estadoCredito": "AL_DIA"
}
```

## Paso `pago`: Pago donde Cuentas demora mas que el timeout del cliente (INC-01)
- `POST http://127.0.0.1:8090/cobranza/cr-int-08/pagos`
- Respuesta: **HTTP 200** (6836.3 ms)

```json
{
  "idPago": "PAG-D2A88CC2",
  "referenciaTransaccion": "OP-INTEG-3",
  "estado": "PENDIENTE",
  "idempotente": false,
  "motivo": "Cuentas no respondio",
  "codCredito": "CR-INTEG-213034",
  "idCanal": "HB",
  "montoPago": 100.0,
  "fechaHora": "2026-10-25 21:30:46",
  "aplicacion": null,
  "estadoCredito": "AL_DIA"
}
```

## Paso `6-resolver`: Resolver el pago PENDIENTE consultando a Cuentas (RF-COB-011 / RN-COB-009)
- `POST http://127.0.0.1:8090/cobranza/pagos/OP-INTEG-3/resolver`
- Respuesta: **HTTP 200** (2079.8 ms)

```json
{
  "idPago": "PAG-D2A88CC2",
  "referenciaTransaccion": "OP-INTEG-3",
  "estado": "CONFIRMADO",
  "idempotente": false,
  "motivo": "Cargo de 100.0 PEN aplicado a SIN-RESPUESTA",
  "codCredito": "CR-INTEG-213034",
  "idCanal": "HB",
  "montoPago": 100.0,
  "fechaHora": "2026-10-25 21:30:46",
  "aplicacion": {
    "idCuota": "CU-7DB6C241",
    "numeroCuota": 1,
    "montoAplicado": 100.0,
    "montoAplicadoMora": 0.0,
    "montoAplicadoCapital": 100.0,
    "saldoPendienteCuota": 750.0,
    "moraPendienteCuota": 0.0,
    "estadoCuota": "PARCIAL"
  },
  "estadoCredito": "AL_DIA"
}
```

## Paso `7-conciliacion`: Conciliacion del dia
- `GET http://127.0.0.1:8090/cobranza/conciliacion`
- Respuesta: **HTTP 200** (1526.7 ms)

```json
{
  "fecha": "2026-10-25",
  "totalCobrado": 250.0,
  "totalAplicado": 250.0,
  "diferencia": 0.0,
  "cantidadPagosCobrados": 2,
  "pagosPendientes": [],
  "pagosRechazados": [
    {
      "idPago": "PAG-EFB3D10B",
      "codCredito": "CR-INTEG-213034",
      "referenciaTransaccion": "OP-INTEG-2",
      "fechaHora": "2026-10-25 21:30:44",
      "montoPago": 50.0
    }
  ],
  "pagosRequierenRevision": []
}
```
