# Cobranza BNA: API del módulo (Línea de Créditos)

Servicio en **Python + FastAPI + MySQL**, según el lineamiento técnico del Comité de Créditos.
Implementa el flujo de pago de cuotas respetando las reglas RN-COB y las interfaces CR-INT-06, 07 y 08.

## Qué hace
| Interfaz | Endpoint | Función |
|---|---|---|
| CR-INT-06 | `POST /cr-int-06/obligaciones` | Desembolso activa el crédito y entrega su calendario de cuotas |
| CR-INT-08 | `POST /cr-int-08/pagos` | Home Banking envía un pago; Cobranza lo valida, pide el cargo a Cuentas y lo aplica |
| CR-INT-07 | (interno) | Cobranza solicita el cargo a Cuentas. **SIMULADO por defecto** |
| Consultas | `GET /creditos/{cod}`, `/cuotas`, `/pagos`, `/pagos/{ref}/comprobante` | Saldo, cronograma, historial y comprobante |
| Mora | `POST/GET /creditos/{cod}/cuotas/{n}/mora` | Registra la mora **recibida** y conserva el historial |
| CR-INT-10 | `GET /auditoria` | Eventos de trazabilidad (registro local) |

## Reglas implementadas
| Regla | Comportamiento |
|---|---|
| RN-COB-001 | Solo se cobran créditos desembolsados y activados |
| RN-COB-002 | Solo canales habilitados (hoy solo Home Banking, `HB`) |
| RN-COB-003 / 004 | Pago en cualquier momento y en montos fraccionados |
| RN-COB-006 | El pago confirmado se aplica a la cuota pendiente más antigua |
| RN-COB-009 | La cuota no se cierra sin confirmación de Cuentas |
| RN-COB-011 | Un pago mayor al saldo de la cuota se rechaza (el tratamiento del excedente está pendiente del Comité) |
| RN-COB-012 / RN-CR-GEN-004 | Cada pago y cambio de estado deja un evento de auditoría |
| RN-INT-CR-006 | Idempotencia: la misma `referenciaTransaccion` no genera un segundo pago |

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
8. **Mora recibida:** `POST /creditos/CR-0001/cuotas/2/mora` con `5` días y `12.50`. El saldo de la cuota 2 sube a 412.50.
   En MySQL: `SELECT * FROM MORA;`
9. **Comprobante:** `GET /pagos/OP-0001/comprobante`.
10. **Auditoría:** `GET /auditoria` y en MySQL: ``SELECT tipoEvento, idEntidad, `timestamp` FROM EVENTO_AUDITORIA ORDER BY `timestamp`;``

## Supuestos
- **Mora:** la fórmula y quién la calcula están pendientes del Comité (RN-COB-005). Cobranza no calcula ni asume tasa: guarda la mora que recibe y la suma al saldo de la cuota. Un recálculo reemplaza al vigente y conserva el historial.
- **Cuentas:** por defecto está simulado. `cuentaOrigen = "SIN-FONDOS"` simula un rechazo y `"SIN-RESPUESTA"` simula que Cuentas no responde (el pago queda `PENDIENTE`). Para conectarlo al módulo real, define `CUENTAS_URL` y acuerda el formato de respuesta con ese equipo.
- **Calendario:** se recibe completo en CR-INT-06. Quién lo mantiene después está pendiente del Comité.
- **Aplicación del pago:** un pago se aplica a la cuota pendiente más antigua y no puede superar su saldo.

## Qué falta
- Probar la integración con los módulos reales: Desembolso, Cuentas y Home Banking.
- Envío de eventos a Seguridad/Auditoría (hoy solo se registran localmente).
- Autenticación y permisos por rol (LIDER_COBRANZA).
- Conciliación diaria (RF-COB-018), recordatorios y notificaciones.
- Reglas pendientes del Comité: fórmula y responsable de la mora, propietario del calendario, tratamiento de excedentes, catálogos de estados.
- Pruebas de integración en el ambiente de Testing y despliegue.

## Pruebas automáticas
La lógica de negocio tiene 13 pruebas (con SQLite, sin necesidad de MySQL):
```
python -m unittest discover -s tests -v
```
