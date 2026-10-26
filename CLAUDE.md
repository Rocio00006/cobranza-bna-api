# CLAUDE.md — Módulo Cobranza (BNA, Línea de Créditos)

Proyecto académico (UCSM, curso GSTI). Banco ficticio "Banco Nacional de Arequipa" (BNA).
Este repositorio es la API del **módulo Cobranza (COB)**, servicio TI **SRV-CR-05 "Servicio de Cobro de Cuotas de Crédito"**.
Estamos en la **Fase II (ITIL 4)**. Escribe código, comentarios, mensajes de error y documentación en **español**.

## Stack
- Python 3.10+, FastAPI, Pydantic v2, MySQL 8 (PyMySQL). Swagger en `/docs`.
- SQLite en memoria SOLO para pruebas automáticas (`python -m unittest discover -s tests -v`).
- Capas: `app/main.py` (endpoints y modelos Pydantic), `app/servicio.py` (lógica de negocio, sin FastAPI),
  `app/db.py` (acceso a datos MySQL/SQLite), `app/cuentas.py` (cliente de Cuentas, simulado o HTTP).
- Base de datos propia de Cobranza. Nunca acceder a tablas de otros módulos (RN-INT-CR-008).

## Flujo de la Línea de Créditos
Captación → Solicitud → Evaluación → Desembolso → **Cobranza**. Cobranza solo cobra créditos ya desembolsados y activados.

## Interfaces (matriz CR-INT oficial)
| ID | Emisor → Receptor | Datos oficiales | Endpoint en esta API |
|---|---|---|---|
| CR-INT-06 | Desembolso → Cobranza | codCredito, fechaDesembolso, monto, calendarioPagos | `POST /cr-int-06/obligaciones` |
| CR-INT-07 | Cobranza → Cuentas | codCredito, numCuentaAhorro, montoCuota, moneda | cliente HTTP en `app/cuentas.py` |
| CR-INT-08 | Home Banking → Cobranza | codCliente, codCredito, montoPago, cuentaOrigen | `POST /cr-int-08/pagos` |
| CR-INT-10 | Créditos → Seguridad/Auditoría | timestamp, moduloEmisor, usuario/operador, tipoEvento, resultado | tabla EVENTO_AUDITORIA, `GET /auditoria` |

Campos que la API usa y NO están en la matriz (marcar siempre como "propuesta a coordinar con el Comité", regla RN-CR-GEN-007):
- CR-INT-06: idCliente, idSolicitud, moneda.
- CR-INT-07: idOperacion (justificado por RN-INT-CR-006, idempotencia).
- CR-INT-08: referenciaTransaccion, idCanal.
No crear interfaces nuevas (CORE, Solicitud, Tarjetas, Clientes) sin indicarlo como pendiente.
Todas las integraciones son REST/JSON vía Bus de Servicios.

## Reglas de negocio que el código debe respetar (Diccionario de Reglas, Créditos v2.0)
- RN-COB-001: solo créditos desembolsados y activados (crédito llega por CR-INT-06).
- RN-COB-002: solo canales habilitados (hoy solo Home Banking `HB`).
- RN-COB-003 / 004: pago en cualquier momento y en montos fraccionados.
- RN-COB-005: intereses por retraso. **Fórmula, tasa y responsable PENDIENTES.** Cobranza NO calcula ni inventa tasa:
  recibe la mora (RGN-15 dice que la calcula CORE) y la guarda con historial (tabla MORA, campo `vigente`).
- RN-COB-006: cada pago confirmado actualiza la cuota y deja traza (saldo y estado).
- RN-COB-009: la cuota no se cierra sin confirmación de Cuentas. Un cargo incierto NO se reintenta.
- RN-COB-010: el atraso se calcula con el calendario vigente recibido, no con fechas propias. `registrar_mora`
  rechaza (422) si la cuota aun no vencio respecto de la fecha actual (acepta `fechaReferencia` opcional para
  demostrarlo) o si `diasAtraso` es 0 con `montoCalculado` mayor a cero.
- RN-COB-011 (= RF-COB-017): pago mayor al saldo de la cuota → se rechaza / aísla. **No decidir el tratamiento**.
- RN-COB-012 / RN-CR-GEN-004: todo pago y cambio de estado deja evento de auditoría.
- RN-INT-CR-006 (= RF-COB-016): idempotencia por referenciaTransaccion/idOperacion.
Cada error de negocio debe devolver `{"detalle": ..., "regla": "RN-..."}` (clase `ErrorNegocio`).

## Modelo de datos (7 tablas, ver diccionario de Fase II)
CREDITO, CUOTA, PAGO, CANAL_PAGO, APLICACION_PAGO, MORA, EVENTO_AUDITORIA.
El diccionario oficial usa: montos DECIMAL(14,2); idSolicitud NOT NULL; referenciaTransaccion VARCHAR(40);
idEntidad VARCHAR(20); usuarioOperador VARCHAR(30); tipoIntegracion VARCHAR(30). El código debe alinearse a esto
o documentar la diferencia.

### Cambios respecto al diccionario de datos de Fase II (pendiente de trasladar al documento oficial)
Agregados en Parte 2A, no están en el diccionario de Fase II todavía. Son columnas internas de Cobranza
(no viajan en ninguna interfaz CR-INT), DECIMAL(14,2) para mantener la convención de montos del diccionario:
- `CUOTA.moraPendiente`: antes la mora recibida (RN-COB-005) se sumaba directo a `CUOTA.saldoPendiente`,
  mezclando capital y mora en un solo campo. Se separó porque RF-COB-003 (monto a pagar desglosado) y
  RF-COB-008/013 (comprobante con mora y capital por separado) necesitan distinguir cuánto de la deuda es
  capital y cuánto es mora vigente.
- `PAGO.montoMora` y `PAGO.montoCapital`: registran cómo se repartió cada pago entre mora y capital, según
  el orden de imputación (`ORDEN_IMPUTACION_MORA_PRIMERO` en `app/servicio.py`, SUPUESTO pendiente del
  Comité). Sin estas columnas el comprobante (RF-COB-008/013) no podría mostrar ese desglose después del
  pago, porque `APLICACION_PAGO.montoAplicado` solo guarda el total aplicado a la cuota.

En MySQL, `app/db.py` agrega estas columnas con una migración idempotente (`migrar_esquema`, consulta
`information_schema.columns`) porque `CREATE TABLE IF NOT EXISTS` no las agrega a una base ya creada en la
Parte 1. En SQLite no hace falta: las pruebas siempre parten de un esquema nuevo.

## Requerimientos funcionales (Fase I) y estado en el código
Hecho: RF-COB-001, 002 (por codCredito e idCliente; DNI pendiente, ver abajo), 003 (monto a pagar desglosado),
005, 007 (catálogo provisional AL_DIA/EN_MORA/CANCELADO), 008 / 013 (comprobante con mora y capital
desglosados), 010, 011 (pagos pendientes y su resolución, INC-01), 012 (por codCredito e idCliente),
015, 016, 017 (rechazo), 018 (conciliación diaria, I-04/I-05).
Parcial / falta:
- RF-COB-002 / 012: consulta por DNI (hoy solo por idCliente; requiere interfaz con Clientes, aún no existe).
- RF-COB-004: validación de identidad (PROPUESTA; simular token de Seguridad, no implementar antifraude real).
- RF-COB-011: política de reversión/reasignación del dinero de un pago REQUIERE_REVISION (hoy solo se marca).
- Roles (I-04): COBRANZA_LEER (consultas, auditoría) y COBRANZA_EJECUTAR (pagos, mora). Simple: API key por rol.
Fuera de alcance: RF-COB-006 (recordatorios) y RF-COB-014 (notificaciones).

Supuestos provisionales introducidos en Parte 2A, pendientes de definición del Comité (ver README):
catálogo de estados del crédito (AL_DIA/EN_MORA/CANCELADO) y orden de imputación del pago
(hoy: primero mora vigente, luego capital; constante `ORDEN_IMPUTACION_MORA_PRIMERO` en `app/servicio.py`).
En Parte 2B se agregó el estado PAGO.estadoConfirmacion = REQUIERE_REVISION (dinero ya cobrado por
Cuentas que no se pudo aplicar porque la cuota cambió mientras el pago estaba PENDIENTE) y la definición
de tasa de fallas de I-05 (ver "Prácticas ITIL" abajo): ambas son propuestas del equipo, no del Comité.

## Prácticas ITIL ya definidas (I-04 / I-05) que el código debe poder evidenciar
- INC-01 pago no confirmado: `GET /pagos/pendientes` (antigüedad) y `POST /pagos/{ref}/resolver` (consulta
  a Cuentas por idOperacion, RN-COB-009: nunca reintenta el cargo). INC-02 pago duplicado: idempotencia
  por referenciaTransaccion. INC-03 obligación no activada: RN-COB-001.
- Indicadores: disponibilidad (`/salud`), tiempo de respuesta p95 de `POST /cr-int-08/pagos` (middleware en
  memoria, `GET /metricas`), tasa de fallas de operación (`GET /metricas`; definición PROPUESTA: pagos no
  confirmados o fallidos / intentos válidos, excluyendo rechazos por datos inválidos y duplicados — ver
  README), tiempo de restauración (no implementado), pagos pendientes (`GET /metricas` y
  `/pagos/pendientes`) + conciliación diaria (`GET /conciliacion`, RF-COB-018). Metas numéricas: por
  definir (no inventarlas); los endpoints solo reportan el valor medido.

## Situación de integración
Ningún otro módulo tiene API todavía. Cuentas, Desembolso y Home Banking se prueban con **simuladores HTTP
separados** (otro proceso/puerto) que respetan el contrato CR-INT. Documentar siempre: "probado contra simulador;
con módulo real: pendiente porque el módulo aún no publica su API".

## Convenciones
- Lógica nueva en `servicio.py` con su prueba en `tests/`. No romper las pruebas existentes (43 a la fecha).
- Cada endpoint con `tags`, `summary` y ejemplo en Swagger, y citando la RN/RF que cumple.
- No guardar credenciales en el código ni en el repositorio (`.env` está en `.gitignore`).
- Decisiones pendientes del Comité: dejarlas como parámetro o rechazo explícito, nunca como valor inventado.
