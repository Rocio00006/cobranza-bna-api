# Cobranza BNA: API del módulo (Línea de Créditos)

Servicio en **Python + FastAPI + MySQL**, según el lineamiento técnico del Comité de Créditos.
Implementa el flujo de pago de cuotas respetando las reglas RN-COB y las interfaces CR-INT-06, 07 y 08.

## Qué hace
| Interfaz | Endpoint | Función |
|---|---|---|
| CR-INT-06 | `POST /cr-int-06/obligaciones` | Desembolso activa el crédito y entrega su calendario de cuotas |
| CR-INT-08 | `POST /cr-int-08/pagos` | Home Banking envía un pago; Cobranza lo valida, pide el cargo a Cuentas y lo aplica |
| CR-INT-07 | (interno) | Cobranza solicita el cargo a Cuentas. **SIMULADO por defecto** |
| RF-COB-003 | `GET /creditos/{cod}/monto-a-pagar` | Próxima cuota pendiente, desglosada en saldo de capital + mora vigente + total |
| RF-COB-007 | `POST /creditos/{cod}/recalcular-estado` | Recalcula AL_DIA/EN_MORA del crédito; acepta `fechaReferencia` opcional para demostrarlo |
| Consultas | `GET /creditos/{cod}`, `/cuotas`, `/pagos`, `/pagos/{ref}/comprobante` | Saldo, cronograma, historial y comprobante (con desglose mora/capital) |
| RF-COB-002 / 012 | `GET /clientes/{idCliente}/creditos`, `/pagos` | Créditos (con cronograma) e historial de pagos, consultados por `idCliente` |
| Mora | `POST/GET /creditos/{cod}/cuotas/{n}/mora` | Registra la mora **recibida** y conserva el historial |
| CR-INT-10 | `GET /auditoria` | Eventos de trazabilidad (registro local) |

## Reglas implementadas
| Regla | Comportamiento |
|---|---|
| RN-COB-001 | Solo se cobran créditos desembolsados y activados (no `CANCELADO`) |
| RN-COB-002 | Solo canales habilitados (hoy solo Home Banking, `HB`) |
| RN-COB-003 / 004 | Pago en cualquier momento y en montos fraccionados |
| RN-COB-005 | La mora se guarda separada del capital (`CUOTA.moraPendiente`); un recálculo reemplaza el valor vigente y conserva el historial en `MORA` |
| RN-COB-006 | El pago confirmado se aplica a la cuota pendiente más antigua (capital y/o mora) |
| RN-COB-009 | La cuota no se cierra sin confirmación de Cuentas |
| RN-COB-011 | Un pago mayor al saldo adeudado (capital + mora vigente) de la cuota se rechaza (el tratamiento del excedente está pendiente del Comité) |
| RN-COB-012 / RN-CR-GEN-004 | Cada pago y cambio de estado (incluido AL_DIA/EN_MORA/CANCELADO) deja un evento de auditoría |
| RN-INT-CR-006 | Idempotencia: la misma `referenciaTransaccion` no genera un segundo pago |
| RF-COB-007 | Catálogo provisional de estados del crédito: `AL_DIA`, `EN_MORA`, `CANCELADO` (ver Supuestos) |
| RF-COB-008 / 013 | El comprobante muestra `montoAplicadoMora` y `montoAplicadoCapital` del pago |

## Instalación
Requisitos: Python 3.10 o superior y MySQL 8.
```
pip install -r requirements.txt
```
En MySQL: `CREATE DATABASE cobranza_bna CHARACTER SET utf8mb4;`
Copia `.env.example` como `.env` y ajusta `DATABASE_URL`. Las tablas se crean solas al iniciar.
(`schema_mysql.sql` queda como alternativa manual.)

## Ejecución
```
uvicorn app.main:app --reload --port 8000
```
Swagger: http://localhost:8000/docs  (`/salud` confirma que la API está arriba).

## Guion del video (4 a 5 minutos)
Muestra en pantalla Swagger y un cliente MySQL (Workbench o consola) lado a lado. No muestres la clave.

1. **Base vacía:** `SELECT COUNT(*) FROM CREDITO;` da 0.
2. **Desembolso activa el crédito:** `POST /cr-int-06/obligaciones` con el ejemplo de Swagger.
   En MySQL: `SELECT * FROM CREDITO;` y `SELECT numeroCuota, saldoPendiente, estadoCuota FROM CUOTA ORDER BY numeroCuota;`
3. **Pago parcial:** `POST /cr-int-08/pagos` con `montoPago 150.00` y `OP-0001`. Resultado: `CONFIRMADO`, cuota 1 `PARCIAL`, saldo 250.
   En MySQL: `SELECT * FROM PAGO;`, `SELECT * FROM APLICACION_PAGO;` y la cuota actualizada.
4. **Idempotencia:** repite el mismo cuerpo (`OP-0001`). Resultado: `idempotente: true`. En MySQL: `SELECT COUNT(*) FROM PAGO;` sigue en 1.
5. **Pago que completa la cuota:** `montoPago 250.00` con `OP-0002`. Cuota 1 `PAGADA`.
6. **Cuentas rechaza:** `montoPago 100.00`, `cuentaOrigen "SIN-FONDOS"`, `OP-0003`. Resultado: `RECHAZADO`; la cuota 2 no cambia (RN-COB-009).
7. **Excedente:** `montoPago 9999` con `OP-0004`. Responde 422 con la regla RN-COB-011.
8. **Mora recibida (RN-COB-005):** `POST /creditos/CR-0001/cuotas/2/mora` con `5` días y `12.50`. La cuota 2 mantiene `saldoPendiente` (capital) en 400 y muestra `moraPendiente 12.50`.
   En MySQL: `SELECT * FROM MORA;` y `SELECT numeroCuota, saldoPendiente, moraPendiente FROM CUOTA;`
9. **Monto a pagar desglosado (RF-COB-003):** `GET /creditos/CR-0001/monto-a-pagar` devuelve la cuota 2 con `saldoCapital 400`, `moraVigente 12.50` y `totalAPagar 412.50`.
10. **Pago cubre mora y capital (RF-COB-008/013):** paga la cuota 2 con `montoPago 412.50` y `OP-0005`. El comprobante (`GET /pagos/OP-0005/comprobante`) muestra `montoAplicadoMora 12.50` y `montoAplicadoCapital 400.00`.
11. **Comprobante:** `GET /pagos/OP-0001/comprobante`.
12. **Estado del crédito (RF-COB-007):** `POST /creditos/CR-0001/recalcular-estado?fechaReferencia=2026-12-10` fuerza `EN_MORA` (demuestra la transición sin esperar la fecha real); sin el parámetro, vuelve a evaluar con la fecha de hoy.
13. **Consulta por cliente (RF-COB-002/012):** `GET /clientes/CLI-0001/creditos` y `GET /clientes/CLI-0001/pagos`.
14. **Auditoría:** `GET /auditoria` y en MySQL: ``SELECT tipoEvento, idEntidad, `timestamp` FROM EVENTO_AUDITORIA ORDER BY `timestamp`;``

## Supuestos
- **Mora:** la fórmula y quién la calcula están pendientes del Comité (RN-COB-005). Cobranza no calcula ni asume tasa: guarda la mora que recibe en `CUOTA.moraPendiente`, **separada del capital** (`CUOTA.saldoPendiente`). Un recálculo reemplaza el valor vigente (no se suma) y el historial completo queda en la tabla `MORA` (campo `vigente`).
- **Orden de imputación del pago (RF-COB-008/013):** es un **SUPUESTO provisional, pendiente de definición del Comité**. Hoy el pago cubre primero la mora vigente de la cuota y el resto va a capital (constante `ORDEN_IMPUTACION_MORA_PRIMERO` en `app/servicio.py`; cambiarla a `False` invierte el orden). El comprobante y la respuesta del pago muestran `montoAplicadoMora` y `montoAplicadoCapital` por separado.
- **Estados del crédito (RF-COB-007):** catálogo **provisional, pendiente de definición del Comité**: `AL_DIA`, `EN_MORA` (alguna cuota con saldo —capital o mora— vencida respecto de la fecha de referencia) y `CANCELADO` (terminal, todas las cuotas saldadas). Se recalcula automáticamente tras cada pago y cada registro de mora, y manualmente con `POST /creditos/{cod}/recalcular-estado?fechaReferencia=AAAA-MM-DD` (parámetro opcional, pensado para demostrar la transición sin esperar al vencimiento real).
- **Cuentas:** por defecto está simulado. `cuentaOrigen = "SIN-FONDOS"` simula un rechazo y `"SIN-RESPUESTA"` simula que Cuentas no responde (el pago queda `PENDIENTE`). Para conectarlo al módulo real, define `CUENTAS_URL` y acuerda el formato de respuesta con ese equipo.
- **Calendario:** se recibe completo en CR-INT-06. Quién lo mantiene después está pendiente del Comité.
- **Aplicación del pago:** un pago se aplica a la cuota pendiente más antigua (capital y/o mora) y no puede superar su saldo adeudado total.
- **Consulta por DNI (RF-COB-002/012):** Cobranza guarda `idCliente`, no el DNI. La consulta por DNI requeriría una interfaz con el módulo Clientes que aún no existe (pendiente, fuera de alcance de esta fase).

## Qué falta
- Probar la integración con los módulos reales: Desembolso, Cuentas y Home Banking.
- Envío de eventos a Seguridad/Auditoría (hoy solo se registran localmente).
- Autenticación y permisos por rol (LIDER_COBRANZA).
- Conciliación diaria (RF-COB-018), recordatorios y notificaciones.
- Consulta por DNI (hoy solo por `idCliente`; ver Supuestos).
- Reglas pendientes del Comité: fórmula y responsable de la mora, propietario del calendario, tratamiento de excedentes, orden de imputación del pago, catálogo definitivo de estados.
- Pruebas de integración en el ambiente de Testing y despliegue.

## Pruebas automáticas
La lógica de negocio tiene 29 pruebas (con SQLite, sin necesidad de MySQL):
```
python -m unittest discover -s tests -v
```
