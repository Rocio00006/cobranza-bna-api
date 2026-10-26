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
| RF-COB-011 / INC-01 | `GET /pagos/pendientes` | Pagos en `PENDIENTE` con su antigüedad en horas |
| RF-COB-011 / INC-01 | `POST /pagos/{ref}/resolver` | Consulta a Cuentas el estado de un pago `PENDIENTE` (nunca repite el cargo) y lo resuelve |
| RF-COB-018 | `GET /conciliacion?fecha=AAAA-MM-DD` | Total cobrado vs aplicado del día, diferencia y detalle de pendientes/rechazados/`REQUIERE_REVISION` |
| I-05 | `GET /metricas` | Tasa de fallas de operación, pagos pendientes y p95 de `POST /cr-int-08/pagos` (sin metas) |
| CR-INT-10 | `GET /auditoria` | Eventos de trazabilidad, con `resultado` (registro local) |

### Autenticación y roles (I-04)
Todo endpoint (excepto `/salud`) exige el header `X-API-Key`. Sin clave → `401`; clave de un rol sin permiso → `403`. El botón **Authorize** de Swagger (`/docs`) pide la clave una sola vez para toda la sesión.

| Rol | Clave de entorno | Acceso |
|---|---|---|
| `COBRANZA_LEER` | `API_KEY_COBRANZA_LEER` | Consultas, auditoría, conciliación, métricas |
| `COBRANZA_EJECUTAR` | `API_KEY_COBRANZA_EJECUTAR` | Mora, `recalcular-estado`, `resolver` pagos pendientes |
| `INTEGRACION_BUS` | `API_KEY_INTEGRACION_BUS` | `POST /cr-int-06/obligaciones`, `POST /cr-int-08/pagos` |

`POST /cr-int-08/pagos` exige además el header `X-Token-Seguridad` (RF-COB-004, ver Supuestos).

## Reglas implementadas
| Regla | Comportamiento |
|---|---|
| RN-COB-001 | Solo se cobran créditos desembolsados y activados (no `CANCELADO`) |
| RN-COB-002 | Solo canales habilitados (hoy solo Home Banking, `HB`) |
| RN-COB-003 / 004 | Pago en cualquier momento y en montos fraccionados |
| RN-COB-005 | La mora se guarda separada del capital (`CUOTA.moraPendiente`); un recálculo reemplaza el valor vigente y conserva el historial en `MORA` |
| RN-COB-006 | El pago confirmado se aplica a la cuota pendiente más antigua (capital y/o mora) |
| RN-COB-009 | La cuota no se cierra sin confirmación de Cuentas |
| RN-COB-010 | La mora solo se acepta si la cuota ya venció (y `diasAtraso` 0 no admite monto > 0) |
| RN-COB-011 | Un pago mayor al saldo adeudado (capital + mora vigente) de la cuota se rechaza (el tratamiento del excedente está pendiente del Comité) |
| RN-COB-012 / RN-CR-GEN-004 | Cada pago y cambio de estado (incluido AL_DIA/EN_MORA/CANCELADO) deja un evento de auditoría |
| RN-INT-CR-006 | Idempotencia: la misma `referenciaTransaccion` no genera un segundo pago |
| RF-COB-007 | Catálogo provisional de estados del crédito: `AL_DIA`, `EN_MORA`, `CANCELADO` (ver Supuestos) |
| RF-COB-008 / 013 | El comprobante muestra `montoAplicadoMora` y `montoAplicadoCapital` del pago |
| RF-COB-011 / INC-01 | Un pago `PENDIENTE` se resuelve consultando a Cuentas por su `idOperacion`, nunca repitiendo el cargo; si Cuentas confirma pero la cuota ya cambió, queda `REQUIERE_REVISION` |
| RF-COB-018 / INC-02 | La conciliación compara lo cobrado (`CONFIRMADO` + `REQUIERE_REVISION`) contra lo aplicado (`APLICACION_PAGO`); la diferencia delata pagos `REQUIERE_REVISION` |
| RF-COB-004 (PROPUESTA) | `POST /cr-int-08/pagos` exige `X-Token-Seguridad`; `TOKEN-INVALIDO` se rechaza y 3 rechazos seguidos del mismo cliente bloquean sus pagos temporalmente |
| RN-CR-GEN-004 | `usuarioOperador` de la auditoría es el rol (`X-API-Key`) que hizo la llamada |

## Instalación
Requisitos: Python 3.10 o superior y MySQL 8.
```
pip install -r requirements.txt
```
En MySQL: `CREATE DATABASE cobranza_bna CHARACTER SET utf8mb4;`
Copia `.env.example` como `.env`, ajusta `DATABASE_URL` y define tus propias `API_KEY_COBRANZA_LEER` /
`API_KEY_COBRANZA_EJECUTAR` / `API_KEY_INTEGRACION_BUS` (nunca las subas al repositorio). Las tablas se
crean solas al iniciar. (`schema_mysql.sql` queda como alternativa manual.)

## Ejecución
```
uvicorn app.main:app --reload --port 8000
```
Swagger: http://localhost:8000/docs (`/salud` confirma que la API está arriba, sin clave). En **Authorize**
pega el valor de una de las `API_KEY_*` del `.env` para probar el resto de endpoints.

## Integración por red (Parte 3)
Ningún otro módulo publica API todavía, así que cada interfaz se prueba contra un **simulador HTTP
propio**, en su propio puerto, hablando por red real (no llamadas directas a `app/servicio.py`) y
**siempre a través de un Bus de Servicios** (RNF-04: ningún módulo llama a otro directo).

| Servicio | Carpeta/archivo | Puerto |
|---|---|---|
| Cobranza API | `app/main.py` | 8002 |
| Cuentas (simulado, CR-INT-07) | `simuladores/cuentas_app.py` | 8001 |
| Bus de Servicios | `simuladores/bus_app.py` | 8090 (enruta `/cobranza/*` y `/cuentas/*`) |

> Para correr solo Cobranza (sin Cuentas ni Bus) usa el puerto 8000 de la sección "Ejecución" arriba.
> Para la integración completa, Cobranza se levanta en el 8002 (`levantar_todo.bat` ya lo hace así):
> en nuestro entorno de desarrollo el 8000 quedó ocupado por un socket que Windows no liberaba tras
> varios reinicios seguidos del servidor; si el tuyo está libre, puedes usar 8000 también — solo
> ajusta `BUS_DESTINO_COBRANZA` al levantar el Bus.
| Desembolso (script cliente, CR-INT-06) | `simuladores/desembolso_cliente.py` | — (no es servidor) |
| Home Banking (script cliente, CR-INT-08) | `simuladores/home_banking_cliente.py` | — (no es servidor) |

**Para levantar todo en Windows:**
```
levantar_todo.bat
```
Abre 3 ventanas (Cobranza, Cuentas, Bus) y define `CUENTAS_URL=http://127.0.0.1:8090/cuentas/cargos`
para que Cobranza llame a Cuentas **a través del Bus** (sin tocar la lógica de `app/cuentas.py`, solo
la variable de entorno). Si prefieres hacerlo a mano, abre 3 terminales:
```
uvicorn app.main:app --port 8002          (en una terminal con CUENTAS_URL seteada, ver arriba)
uvicorn simuladores.cuentas_app:app --port 8001
uvicorn simuladores.bus_app:app --port 8090
```

**Prueba de integración completa** (Desembolso activa → Home Banking paga parcial → duplicado → fondos
insuficientes → Cuentas sin respuesta (INC-01) → resolver pendiente → conciliación), con los 3
servicios ya arriba:
```
python simuladores/prueba_integracion.py
```
Guarda la evidencia de cada paso en `evidencias/integracion_<fecha>.json` (JSON completo) y
`evidencias/integracion_<fecha>.md` (resumen legible). El estado de cada módulo está en
`docs/estado-integracion.md`, y el contrato JSON exacto de cada interfaz (para compartir con los otros
equipos) en `docs/contratos-cr-int.md`.

## Prototipo de interfaz
Prototipo navegable de Home Banking (pago de cuotas), un solo archivo HTML sin dependencias:
**https://rocio00006.github.io/cobranza-bna-api/prototipo/**

Prototipo con datos ficticios, todavía no conectado a la API. El código fuente está en
`prototipo/index.html` (ver `prototipo/README.md` para el detalle de qué pantalla corresponde a
cada endpoint/regla).

## Guion del video (4 a 5 minutos)
Muestra en pantalla Swagger y un cliente MySQL (Workbench o consola) lado a lado. No muestres la clave
de MySQL ni el valor real de las `API_KEY_*` (usa el botón **Authorize** fuera de cámara o difumínalas).
Desde el paso 2, cada llamada necesita la `X-API-Key` del rol correspondiente (ver tabla de roles); los
pagos (`POST /cr-int-08/pagos`) necesitan además `X-Token-Seguridad` (cualquier valor que no sea
`TOKEN-INVALIDO` ni esté vacío, por ejemplo `TOKEN-DEMO-0001`).

1. **Base vacía:** `SELECT COUNT(*) FROM CREDITO;` da 0.
2. **Desembolso activa el crédito:** `POST /cr-int-06/obligaciones` con el ejemplo de Swagger.
   En MySQL: `SELECT * FROM CREDITO;` y `SELECT numeroCuota, saldoPendiente, estadoCuota FROM CUOTA ORDER BY numeroCuota;`
3. **Pago parcial:** `POST /cr-int-08/pagos` con `montoPago 150.00` y `OP-0001`. Resultado: `CONFIRMADO`, cuota 1 `PARCIAL`, saldo 250.
   En MySQL: `SELECT * FROM PAGO;`, `SELECT * FROM APLICACION_PAGO;` y la cuota actualizada.
4. **Idempotencia:** repite el mismo cuerpo (`OP-0001`). Resultado: `idempotente: true`. En MySQL: `SELECT COUNT(*) FROM PAGO;` sigue en 1.
5. **Pago que completa la cuota:** `montoPago 250.00` con `OP-0002`. Cuota 1 `PAGADA`.
6. **Cuentas rechaza:** `montoPago 100.00`, `cuentaOrigen "SIN-FONDOS"`, `OP-0003`. Resultado: `RECHAZADO`; la cuota 2 no cambia (RN-COB-009).
7. **Excedente:** `montoPago 9999` con `OP-0004`. Responde 422 con la regla RN-COB-011.
8. **Mora recibida (RN-COB-005 / RN-COB-010):** `POST /creditos/CR-0001/cuotas/2/mora?fechaReferencia=2026-12-10` con `5` días y `12.50` (la cuota 2 vence 2026-12-05; `fechaReferencia` simula que ya pasó esa fecha, ya que RN-COB-010 rechaza la mora de una cuota que aún no venció). La cuota 2 mantiene `saldoPendiente` (capital) en 400 y muestra `moraPendiente 12.50`.
   En MySQL: `SELECT * FROM MORA;` y `SELECT numeroCuota, saldoPendiente, moraPendiente FROM CUOTA;`
9. **Monto a pagar desglosado (RF-COB-003):** `GET /creditos/CR-0001/monto-a-pagar` devuelve la cuota 2 con `saldoCapital 400`, `moraVigente 12.50` y `totalAPagar 412.50`.
10. **Pago cubre mora y capital (RF-COB-008/013):** paga la cuota 2 con `montoPago 412.50` y `OP-0005`. El comprobante (`GET /pagos/OP-0005/comprobante`) muestra `montoAplicadoMora 12.50` y `montoAplicadoCapital 400.00`.
11. **Comprobante:** `GET /pagos/OP-0001/comprobante`.
12. **Estado del crédito (RF-COB-007):** `POST /creditos/CR-0001/recalcular-estado?fechaReferencia=2026-12-10` fuerza `EN_MORA` (demuestra la transición sin esperar la fecha real); sin el parámetro, vuelve a evaluar con la fecha de hoy.
13. **Consulta por cliente (RF-COB-002/012):** `GET /clientes/CLI-0001/creditos` y `GET /clientes/CLI-0001/pagos`.
14. **Pago pendiente (RF-COB-011/INC-01):** `montoPago 100.00`, `cuentaOrigen "SIN-RESPUESTA"`, `OP-0006`. Queda `PENDIENTE`. `GET /pagos/pendientes` lo lista con su antigüedad en horas.
15. **Resolver el pendiente:** `POST /pagos/OP-0006/resolver` consulta a Cuentas (nunca repite el cargo) y lo deja `CONFIRMADO`, aplicado a la cuota 3.
16. **REQUIERE_REVISION:** repite el caso 14 con `OP-0007` sobre una cuota que luego se termina de pagar por otra vía mientras `OP-0007` sigue pendiente; al resolver `OP-0007`, Cuentas confirma pero el monto ya no cabe en lo adeudado → `REQUIERE_REVISION`.
17. **Conciliación (RF-COB-018):** `GET /conciliacion` (fecha de hoy) muestra `totalCobrado`, `totalAplicado`, la `diferencia` (el `REQUIERE_REVISION` del paso 16) y el detalle de pendientes/rechazados/`REQUIERE_REVISION`.
18. **Métricas (I-05):** `GET /metricas` muestra la tasa de fallas, los pagos pendientes y el p95 de `POST /cr-int-08/pagos` medido durante la grabación (sin metas numéricas).
19. **Auditoría:** `GET /auditoria` y en MySQL: ``SELECT tipoEvento, idEntidad, `timestamp`, resultado FROM EVENTO_AUDITORIA ORDER BY `timestamp`;``
20. **Sin clave (I-04):** quita la clave del botón Authorize y repite el paso 2. Responde `401`.
21. **Rol insuficiente:** pon la clave de `COBRANZA_LEER` y repite el paso 2 (`POST /cr-int-06/obligaciones`, que exige `INTEGRACION_BUS`). Responde `403`.
22. **Token de Seguridad inválido (RF-COB-004):** con la clave de `INTEGRACION_BUS`, repite un pago con `X-Token-Seguridad: TOKEN-INVALIDO`. Responde `401` con la regla RF-COB-004.
23. **Bloqueo temporal:** repite el paso 22 tres veces seguidas para el mismo `codCliente`. El tercer rechazo bloquea sus pagos; un cuarto intento, aunque mande un token válido, sigue bloqueado hasta que pase `SEGURIDAD_BLOQUEO_SEGUNDOS`.

## Supuestos
- **Mora:** la fórmula y quién la calcula están pendientes del Comité (RN-COB-005). Cobranza no calcula ni asume tasa: guarda la mora que recibe en `CUOTA.moraPendiente`, **separada del capital** (`CUOTA.saldoPendiente`). Un recálculo reemplaza el valor vigente (no se suma) y el historial completo queda en la tabla `MORA` (campo `vigente`). **RN-COB-010:** se rechaza (422) si la cuota aún no venció respecto de la fecha de referencia (por defecto hoy; `fechaReferencia` opcional en el endpoint, igual que en `recalcular-estado`, para poder demostrarlo) o si `diasAtraso` es 0 con `montoCalculado` mayor a cero.
- **Orden de imputación del pago (RF-COB-008/013):** es un **SUPUESTO provisional, pendiente de definición del Comité**. Hoy el pago cubre primero la mora vigente de la cuota y el resto va a capital (constante `ORDEN_IMPUTACION_MORA_PRIMERO` en `app/servicio.py`; cambiarla a `False` invierte el orden). El comprobante y la respuesta del pago muestran `montoAplicadoMora` y `montoAplicadoCapital` por separado.
- **Estados del crédito (RF-COB-007):** catálogo **provisional, pendiente de definición del Comité**: `AL_DIA`, `EN_MORA` (alguna cuota con saldo —capital o mora— vencida respecto de la fecha de referencia) y `CANCELADO` (terminal, todas las cuotas saldadas). Se recalcula automáticamente tras cada pago y cada registro de mora, y manualmente con `POST /creditos/{cod}/recalcular-estado?fechaReferencia=AAAA-MM-DD` (parámetro opcional, pensado para demostrar la transición sin esperar al vencimiento real).
- **Cuentas:** por defecto está simulado en memoria (`app/cuentas.py:CuentasSimulado`). `cuentaOrigen = "SIN-FONDOS"` simula un rechazo y `"SIN-RESPUESTA"` simula que Cuentas no responde (el pago queda `PENDIENTE`). Con `CUENTAS_URL` seteada, Cobranza llama por HTTP (`CuentasHTTP`) — en la Parte 3 eso apunta al Bus, que enruta a `simuladores/cuentas_app.py` (puerto 8001), un segundo simulador que sí maneja saldos ficticios y demora real por red. Cuando Cuentas publique su API real, solo cambia `CUENTAS_URL`; el formato de respuesta exacto queda por acordar con ese equipo (ver `docs/contratos-cr-int.md`).
- **Calendario:** se recibe completo en CR-INT-06. Quién lo mantiene después está pendiente del Comité.
- **Aplicación del pago:** un pago se aplica a la cuota pendiente más antigua (capital y/o mora) y no puede superar su saldo adeudado total.
- **Consulta por DNI (RF-COB-002/012):** Cobranza guarda `idCliente`, no el DNI. La consulta por DNI requeriría una interfaz con el módulo Clientes que aún no existe (pendiente, fuera de alcance de esta fase).
- **Resolución de pagos pendientes (RF-COB-011/INC-01):** `POST /pagos/{ref}/resolver` solo **consulta** a Cuentas (`consultar(referencia)`), nunca vuelve a llamar `cargar` (RN-COB-009: un cargo incierto no se reintenta). Si Cuentas confirma pero, mientras el pago estuvo pendiente, la cuota cambió y el monto ya no cabe en lo adeudado, el dinero ya fue cobrado pero no se puede aplicar sin más: el pago queda `REQUIERE_REVISION` con su evento de auditoría. **La política de reversión/reasignación de ese dinero está pendiente del Comité** (hoy el pago simplemente se marca, no se decide su destino). El simulador de Cuentas (`CuentasSimulado.consultar`) responde `CONFIRMADO` por defecto (para poder demostrar que un pago "SIN-RESPUESTA" se resuelve); una `referenciaTransaccion` terminada en `-RECHAZA` o `-SIGUESIN` fuerza los otros dos desenlaces.
- **Conciliación (RF-COB-018):** compara `totalCobrado` (pagos `CONFIRMADO` + `REQUIERE_REVISION` del día, dinero que Cuentas sí cargó) contra `totalAplicado` (suma de `APLICACION_PAGO` de pagos `CONFIRMADO`). Si ambos no coinciden es porque hay pagos `REQUIERE_REVISION` (cobrados, no aplicados a ninguna cuota). `pagosPendientes` no se filtra por día: es un backlog abierto (lo importante es su antigüedad, no cuándo se creó).
- **Tasa de fallas (I-05):** `pagosFallidos / intentosValidos`, donde `intentosValidos` es la cantidad de filas en `PAGO` (los rechazos por datos inválidos no llegan a crear una fila, y un duplicado idempotente tampoco crea una fila nueva) y `pagosFallidos` cuenta `RECHAZADO` + `PENDIENTE` + `REQUIERE_REVISION`. Es una definición propuesta por el equipo de desarrollo, no una fórmula del Comité; **sin metas numéricas**, solo se reporta el valor medido.
- **Roles (I-04):** autenticación **simple** por `X-API-Key` (una clave por rol, no por usuario individual), PROPUESTA del equipo de desarrollo para evidenciar el requerimiento; no reemplaza una autenticación real (OAuth, usuarios con contraseña, etc.) que debería definir el Comité/Seguridad. Las claves solo viven en `.env` (nunca en el código ni en el repositorio).
- **Token de Seguridad (RF-COB-004):** PROPUESTA pendiente del Comité. `app/seguridad.py` simula el validador (igual que `app/cuentas.py` simula Cuentas): no es antifraude real. `TOKEN-INVALIDO` o un token vacío se rechazan; tras `SEGURIDAD_LIMITE_RECHAZOS` (3 por defecto) rechazos **consecutivos** del mismo `codCliente`, sus pagos quedan bloqueados por `SEGURIDAD_BLOQUEO_SEGUNDOS` (300 por defecto, configurable en `.env`). Un token válido reinicia el contador. El estado de bloqueo vive en memoria del proceso (se pierde si la API se reinicia) y cada rechazo queda en `EVENTO_AUDITORIA` (`TOKEN_SEGURIDAD_RECHAZADO`).
- **Campo `resultado` (CR-INT-10):** la matriz oficial lo pide y `EVENTO_AUDITORIA` no lo tenía; se agregó como `EXITOSO` por defecto, con `RECHAZADO`/`PENDIENTE`/`REVISION` para los eventos que no son un éxito liso y llano (ver CLAUDE.md, "Cambios respecto al diccionario de datos de Fase II").

## Qué falta
- Probar la integración con los módulos **reales**: Desembolso, Cuentas, Home Banking y Seguridad (hoy
  probada por red contra simuladores propios vía el Bus; ver "Integración por red" y `docs/estado-integracion.md`).
- Envío de eventos a Seguridad/Auditoría (hoy solo se registran localmente).
- Autenticación real (hoy es una clave simple por rol, no por usuario; ver Supuestos) y antifraude real para RF-COB-004 (hoy simulado).
- Recordatorios y notificaciones (fuera de alcance, RF-COB-006/014).
- Consulta por DNI (hoy solo por `idCliente`; ver Supuestos).
- Política de reversión/reasignación del dinero de un pago `REQUIERE_REVISION` (RF-COB-011; hoy solo se marca, no se decide su destino).
- Reglas pendientes del Comité: fórmula y responsable de la mora, propietario del calendario, tratamiento de excedentes, orden de imputación del pago, catálogo definitivo de estados, umbral y duración del bloqueo de RF-COB-004.
- Metas numéricas de los indicadores de I-05 (hoy solo se mide, sin umbrales).
- Pruebas de integración en el ambiente de Testing y despliegue.

## Pruebas automáticas
La lógica de negocio tiene 53 pruebas (con SQLite, sin necesidad de MySQL):
```
python -m unittest discover -s tests -v
```
