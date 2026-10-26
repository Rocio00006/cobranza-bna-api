# Entrega Fase II — Módulo Cobranza (SRV-CR-05)

Proyecto académico UCSM, curso GSTI. Banco ficticio "Banco Nacional de Arequipa" (BNA). Este
documento responde los cuatro puntos del entregable de la Fase II (ITIL 4) para el módulo Cobranza
(COB), servicio TI **SRV-CR-05 "Servicio de Cobro de Cuotas de Crédito"**.

> Los textos oficiales de cada `RF-COB-NNN` provienen del diccionario de requerimientos de Fase I,
> que no está en este repositorio. La trazabilidad de este documento usa las descripciones que ya
> constaban en `CLAUDE.md` y lo que hace el código; donde no hay certeza del texto oficial exacto
> (p. ej. `RF-COB-009`, o la redacción literal de `RF-COB-006/014/015`), se indica explícitamente
> para que se confirme contra el documento del Comité.

---

## (a) APIs implementadas

Todas requieren el header `X-API-Key` (rol indicado), salvo `/salud`. Swagger: `GET /docs` (botón
**Authorize**). Postman: `postman/Cobranza-BNA.postman_collection.json`, organizada en las mismas
carpetas que la tabla de abajo.

| Endpoint | Método | Rol | RF / RN que demuestra | Verlo en Swagger / Postman |
|---|---|---|---|---|
| `/salud` | GET | — (libre) | — | Carpeta "Estado" en Swagger |
| `/cr-int-06/obligaciones` | POST | `INTEGRACION_BUS` | RF-COB-001, CR-INT-06 | Swagger "CR-INT-06"; Postman carpeta **CR-INT-06**, request 1 |
| `/creditos/{codCredito}` | GET | `COBRANZA_LEER` | RF-COB-002 | Postman **Consultas**, request 11 |
| `/creditos/{codCredito}/cuotas` | GET | `COBRANZA_LEER` | RF-COB-002 | Postman **Consultas**, request 12 |
| `/creditos/{codCredito}/monto-a-pagar` | GET | `COBRANZA_LEER` | RF-COB-003 | Postman **Consultas**, request 13 |
| `/creditos/{codCredito}/recalcular-estado` | POST | `COBRANZA_EJECUTAR` | RF-COB-007 | Swagger "Consultas" (acción) |
| `/creditos/{codCredito}/pagos` | GET | `COBRANZA_LEER` | RF-COB-002/012 | Postman **Consultas**, request 14 |
| `/clientes/{idCliente}/creditos` | GET | `COBRANZA_LEER` | RF-COB-002/012 | Postman **Consultas**, request 15 |
| `/clientes/{idCliente}/pagos` | GET | `COBRANZA_LEER` | RF-COB-002/012 | Postman **Consultas**, request 16 |
| `/cr-int-08/pagos` | POST | `INTEGRACION_BUS` (+ `X-Token-Seguridad`) | CR-INT-08; RN-COB-001/002/003/004/006/009/011/012; RF-COB-004 (token); RN-INT-CR-006 | Swagger "CR-INT-08"; Postman carpeta **CR-INT-08**, requests 5-10 |
| `/pagos/{ref}/comprobante` | GET | `COBRANZA_LEER` | RF-COB-008/013 | Postman **Consultas**, request 17 |
| `/pagos/pendientes` | GET | `COBRANZA_LEER` | RF-COB-011, INC-01 | Postman **Pendientes y conciliacion**, request 22 |
| `/pagos/{ref}/resolver` | POST | `COBRANZA_EJECUTAR` | RF-COB-011, RN-COB-009 | Postman **Pendientes y conciliacion**, request 23 |
| `/conciliacion` | GET | `COBRANZA_LEER` | RF-COB-018 | Postman **Pendientes y conciliacion**, request 24 |
| `/metricas` | GET | `COBRANZA_LEER` | Indicadores I-05 | Postman **Metricas**, request 30 |
| `/creditos/{cod}/cuotas/{n}/mora` | POST | `COBRANZA_EJECUTAR` | RF-COB-005, RN-COB-005/010 | Postman **Mora**, requests 18-19 |
| `/creditos/{cod}/cuotas/{n}/mora` | GET | `COBRANZA_LEER` | RF-COB-005 | Postman **Mora**, request 20 |
| `/auditoria` | GET | `COBRANZA_LEER` | CR-INT-10, RN-CR-GEN-004 | Postman **Seguridad y roles**, request 25; Swagger |

Autenticación por rol (`401` sin clave, `403` con rol insuficiente) y `X-Token-Seguridad` (`401`
`TOKEN-INVALIDO`, bloqueo tras 3 rechazos) se demuestran en la carpeta Postman **Seguridad y roles**
(requests 25-29) y en `evidencias/capturas/` (Swagger con el botón Authorize y candados cerrados).

---

## (b) Conexiones con otros módulos probadas y su resultado

Ningún módulo externo publica API todavía (ver `docs/estado-integracion.md`, tabla completa). Cada
interfaz se probó contra un **simulador HTTP propio** (`simuladores/`), por red real y siempre a
través de un Bus de Servicios simulado (RNF-04), no con llamadas directas a `app/servicio.py`.

| Módulo | Interfaz | Resultado obtenido |
|---|---|---|
| Desembolso | CR-INT-06 | `simuladores/desembolso_cliente.py` activa la obligación vía Bus: `HTTP 201`, cuotas creadas, crédito `AL_DIA`. |
| Cuentas | CR-INT-07 | `simuladores/cuentas_app.py` (puerto 8001): cargo confirmado, rechazo por fondos insuficientes (`AH-SIN-FONDOS`), demora real por red con timeout del cliente (`SIN-RESPUESTA`, INC-01) e idempotencia por `idOperacion`, todo verificado vía Bus. |
| Home Banking | CR-INT-08 | `simuladores/home_banking_cliente.py` paga parcial, repite el mismo pago (idempotente) y envía `X-Token-Seguridad`, todo vía Bus. |
| Seguridad | RF-COB-004 (token), CR-INT-10 (auditoría) | Validado con `app/seguridad.py` (simulado dentro de Cobranza, no es un módulo externo real): `TOKEN-INVALIDO` rechazado, bloqueo tras 3 rechazos y su expiración configurable, todo en `EVENTO_AUDITORIA`. |
| CORE | RN-COB-005 (mora) | Sin interfaz CR-INT definida para que CORE empuje la mora; se registra manualmente vía `POST /creditos/{cod}/cuotas/{n}/mora`, simulando el valor que CORE enviaría. No probado por red. |

**Evidencia de la corrida completa** (Desembolso activa → Home Banking paga parcial → duplicado →
fondos insuficientes → Cuentas sin respuesta (INC-01) → resolver pendiente → conciliación), contra
MySQL real:
- `evidencias/integracion_2026-10-25.json` / `.md` — petición, respuesta y código HTTP de cada paso.
- Verificado también directo en MySQL: el pago `CONFIRMADO`/`RECHAZADO`/`PENDIENTE` y los eventos de
  `EVENTO_AUDITORIA` (con `usuarioOperador` = rol real de la llamada) quedaron correctos.
- Colección Postman completa (30 requests, todas las interfaces + roles + Seguridad + métricas) vía
  Newman: `evidencias/newman_2026-10-25.txt` — **30/30 requests, 60/60 asserts**.
- Capturas de Swagger ejecutando CR-INT-06, CR-INT-08 y la auditoría (`/auditoria`, mostrando
  `resultado` y `usuarioOperador`): `evidencias/capturas/`.

---

## (c) Repositorio

**Enlace:** https://github.com/Rocio00006/cobranza-bna-api

**Estructura de carpetas:**
```
cobranza/
├── app/                  API de Cobranza (FastAPI)
│   ├── main.py           endpoints, modelos Pydantic, autenticacion por rol, middleware p95
│   ├── servicio.py       logica de negocio (sin FastAPI): reglas RN-COB, RF-COB
│   ├── db.py             acceso a datos MySQL/SQLite, migraciones idempotentes
│   ├── cuentas.py        cliente de Cuentas (simulado en memoria o HTTP via CUENTAS_URL)
│   ├── auth.py           dependencia de rol por X-API-Key (I-04)
│   └── seguridad.py      validador de X-Token-Seguridad simulado (RF-COB-004)
├── tests/                pruebas automaticas (unittest + SQLite en memoria)
├── simuladores/           Parte 3/4: simuladores HTTP de otros modulos y pruebas de integracion
│   ├── cuentas_app.py     simulador HTTP de Cuentas (CR-INT-07)
│   ├── bus_app.py         Bus de Servicios simulado (RNF-04)
│   ├── desembolso_cliente.py / home_banking_cliente.py   scripts cliente (CR-INT-06 / CR-INT-08)
│   ├── prueba_integracion.py   flujo completo por red, genera evidencias/integracion_*.{json,md}
│   └── capturas_swagger.py     capturas automaticas de Swagger con Playwright
├── postman/               coleccion y environment de Postman (Parte 4)
├── docs/                  contratos CR-INT, estado de integracion, este documento
├── evidencias/            salida de las pruebas de integracion, Newman y las capturas
├── schema_mysql.sql       esquema MySQL (alternativa manual; la API lo crea sola al iniciar)
├── requirements.txt
├── .env.example           variables de entorno de ejemplo (claves FICTICIAS)
└── levantar_todo.bat       levanta Cobranza + Cuentas simulado + Bus (Windows)
```

**Cómo ejecutarlo** (ver README para el detalle completo):
```bash
pip install -r requirements.txt
# En MySQL: CREATE DATABASE cobranza_bna CHARACTER SET utf8mb4;
# Copiar .env.example a .env, ajustar DATABASE_URL (usar 127.0.0.1, no localhost) y las API_KEY_*
uvicorn app.main:app --reload --port 8000
# Swagger en http://localhost:8000/docs — boton Authorize con una API_KEY_* del .env
```
Para la integración completa (Cobranza + Cuentas simulado + Bus): `levantar_todo.bat`, luego
`python simuladores/prueba_integracion.py`.

**Cómo correr las pruebas:**
```bash
python -m unittest discover -s tests -v      # 53 pruebas, SQLite en memoria, sin MySQL
npx newman run postman/Cobranza-BNA.postman_collection.json \
  -e postman/Cobranza-BNA.postman_environment.json \
  --env-var apiKeyLeer=... --env-var apiKeyEjecutar=... --env-var apiKeyBus=...   # contra MySQL real
```

---

## (d) Funcionalidades que faltan y decisiones pendientes del Comité

- **Mora: fórmula y quién la calcula (RN-COB-005).** Cobranza no calcula ni asume tasa: solo guarda
  el valor que recibe (`CUOTA.moraPendiente`, historial en `MORA`). Falta que el Comité defina quién
  la calcula (CORE, según el diccionario de reglas) y la fórmula.
- **Propietario del calendario de pagos.** El calendario se recibe completo en CR-INT-06; no está
  definido quién lo mantiene/actualiza después (reprogramaciones, refinanciamientos).
- **Tratamiento del excedente (RN-COB-011 / RF-COB-017).** Hoy un pago que excede el saldo adeudado
  de la cuota se **rechaza**; no está definido si debería aplicarse a la siguiente cuota, devolverse,
  o quedar a favor del cliente.
- **Catálogo definitivo de estados del crédito (RF-COB-007).** `AL_DIA` / `EN_MORA` / `CANCELADO` es
  un catálogo **provisional** propuesto por el equipo de desarrollo, no validado por el Comité.
- **Política de reversión del dinero de un pago `REQUIERE_REVISION` (RF-COB-011).** Cuando Cuentas
  confirma un cargo pero la cuota ya cambió mientras el pago estaba `PENDIENTE` (ya no cabe en lo
  adeudado), el pago queda marcado `REQUIERE_REVISION`: el dinero ya se cobró, pero Cobranza **no
  decide** qué hacer con él (aplicarlo a otra cuota, devolverlo, dejarlo a favor del cliente). Falta
  la política del Comité.
- **Bloqueo de pagos nuevos mientras hay uno pendiente.** Hoy Cobranza **no impide** registrar un
  nuevo pago sobre una cuota que ya tiene un pago `PENDIENTE` sin resolver; de hecho, ese es
  exactamente el escenario que produce un `REQUIERE_REVISION` (ver arriba). Falta decidir si el
  sistema debería bloquear nuevos pagos hasta resolver el pendiente, o si el comportamiento actual
  (dejar que ocurra y marcarlo para revisión manual) es el deseado.
- **Contratos con los módulos reales.** `docs/contratos-cr-int.md` documenta el JSON exacto que usa
  Cobranza hoy (incluidos los campos PROPUESTA que no están en la matriz oficial); falta validarlo
  con los equipos de Desembolso, Cuentas, Home Banking y Seguridad cuando publiquen su API.
- **Metas de SLA / indicadores de I-05.** `GET /metricas` mide tasa de fallas, pagos pendientes y
  p95 de `POST /cr-int-08/pagos`, pero **sin metas numéricas**: el Comité debe definir los umbrales
  (p. ej. "p95 < 500ms", "tasa de fallas < 2%").
- **Consulta por DNI (RF-COB-002/012).** Cobranza guarda `idCliente`, no el DNI; requeriría una
  interfaz con el módulo Clientes que todavía no existe.
- **Validación de identidad real (RF-COB-004) / antifraude real.** `app/seguridad.py` es un
  simulador (igual que `app/cuentas.py` para Cuentas), no un validador de Seguridad real; el umbral
  de rechazos y la duración del bloqueo son PROPUESTA del equipo, configurables pero no definidos
  por el Comité ni por Seguridad.
- **Autenticación real por usuario (I-04).** Hoy es una clave simple por **rol** (`X-API-Key`), no
  por usuario individual; no reemplaza un sistema de autenticación real (OAuth, usuarios con
  contraseña, etc.).
- **Envío de eventos a Seguridad/Auditoría real (CR-INT-10).** Hoy el registro de auditoría queda
  **local** en `EVENTO_AUDITORIA`; falta la interfaz real con el servicio de Seguridad/Auditoría.
- **Roles por API key (I-04), no por usuario.** Ver "Autenticación real" arriba.
- **Fuera de alcance (ya definido así, no pendiente):** RF-COB-006 (recordatorios) y RF-COB-014
  (notificaciones).

---

## Trazabilidad RF-COB-001 a RF-COB-018

| RF | Descripción (según CLAUDE.md / diccionario disponible) | Estado | Código | Prueba(s) |
|---|---|---|---|---|
| RF-COB-001 | Activar la obligación de cobro al recibir CR-INT-06; solo créditos desembolsados y activados (RN-COB-001) | Hecho | `app/servicio.py:activar_obligacion` | `tests/test_servicio.py: test_activacion_crea_credito_y_cuotas, test_activacion_duplicada_es_rechazada` |
| RF-COB-002 | Consultar crédito/cronograma/historial por `codCredito` y por `idCliente`; por DNI, pendiente | Parcial (DNI falta) | `obtener_credito`, `creditos_por_cliente`, `pagos_por_cliente` | `tests/test_parte2a.py: test_consulta_de_creditos_y_pagos_por_idCliente` |
| RF-COB-003 | Endpoint de monto a pagar desglosado (saldo de capital + mora vigente) | Hecho | `monto_a_pagar` | `tests/test_parte2a.py: test_monto_a_pagar_desglosa_capital_y_mora, test_monto_a_pagar_sin_cuotas_pendientes_es_rechazado` |
| RF-COB-004 | Validación de identidad del pago (PROPUESTA: token de Seguridad simulado) | Hecho (simulado) | `app/seguridad.py:SeguridadSimulada`, `servicio.registrar_pago` | `tests/test_parte2c.py` (8 pruebas: token inválido/vacío/válido, bloqueo, reinicio de contador, auditoría) |
| RF-COB-005 | Registrar la mora recibida, con historial (no se calcula en Cobranza) | Hecho | `registrar_mora`, `historial_mora` | `tests/test_servicio.py: test_mora_se_refleja_y_el_recalculo_conserva_historial`; `tests/test_parte2a.py` (RN-COB-010) |
| RF-COB-006 | Recordatorios | Fuera de alcance | — | — |
| RF-COB-007 | Estados del crédito (AL_DIA/EN_MORA/CANCELADO, catálogo provisional) | Hecho (provisional) | `recalcular_estado_credito`, `recalcular_estado`, endpoint `POST /creditos/{cod}/recalcular-estado` | `tests/test_parte2a.py: test_credito_en_mora_al_activar_con_cuota_ya_vencida, test_recalcular_estado_con_fecha_de_referencia_para_demostracion, test_estado_se_recalcula_tras_pago_y_evento_queda_en_auditoria` |
| RF-COB-008 | Comprobante del pago con línea de mora desglosada (junto con RF-COB-013) | Hecho | `comprobante` | `tests/test_parte2a.py: test_comprobante_desglosa_cuanto_fue_mora_y_cuanto_capital` |
| RF-COB-009 | No identificado explícitamente en el diccionario disponible en este repositorio | No verificado | — | Confirmar contra el documento oficial de Fase I |
| RF-COB-010 | El atraso se calcula con el calendario vigente recibido, no con fechas propias (RN-COB-010) | Hecho | `recalcular_estado_credito` (comparación de `fechaVencimiento`), `registrar_mora` (RN-COB-010) | `tests/test_parte2a.py: test_mora_rechazada_si_la_cuota_no_vencio, test_mora_rechazada_si_diasAtraso_es_cero_con_monto_mayor_a_cero, test_mora_aceptada_cuando_la_cuota_ya_vencio` |
| RF-COB-011 | Consultar y resolver pagos PENDIENTES sin reintentar el cargo (INC-01) | Hecho | `pagos_pendientes`, `resolver_pago` | `tests/test_parte2b.py` (7 pruebas de `resolver_pago`/`pagos_pendientes`) |
| RF-COB-012 | Consulta de historial por `codCredito` y por `idCliente` (junto con RF-COB-002) | Hecho | `historial_pagos`, `pagos_por_cliente` | `tests/test_servicio.py: test_comprobante_y_auditoria`; `tests/test_parte2a.py: test_consulta_de_creditos_y_pagos_por_idCliente` |
| RF-COB-013 | Comprobante con mora desglosada (junto con RF-COB-008) | Hecho | `comprobante` | `tests/test_parte2a.py: test_comprobante_desglosa_cuanto_fue_mora_y_cuanto_capital` |
| RF-COB-014 | Notificaciones | Fuera de alcance | — | — |
| RF-COB-015 | Aplicación del pago confirmado a la cuota, con traza (RN-COB-006/009) | Hecho | `_aplicar_a_cuota`, rama `CONFIRMADO` de `registrar_pago` | `tests/test_servicio.py: test_pago_parcial_deja_cuota_parcial, test_pago_completo_cierra_cuota_y_pasa_a_la_siguiente, test_credito_se_cancela_al_pagar_todo` |
| RF-COB-016 | Idempotencia por `referenciaTransaccion`/`idOperacion` (= RN-INT-CR-006) | Hecho | chequeo de `referenciaTransaccion` al inicio de `registrar_pago` | `tests/test_servicio.py: test_idempotencia_no_duplica_el_pago` |
| RF-COB-017 | Pago mayor al saldo de la cuota se rechaza / aísla (= RN-COB-011); no se decide el tratamiento del excedente | Hecho (rechazo) | chequeo de `monto > total_adeudado` en `registrar_pago` | `tests/test_servicio.py: test_excedente_se_rechaza_hasta_definicion_del_comite`; `tests/test_parte2a.py: test_excedente_se_calcula_sobre_capital_mas_mora` |
| RF-COB-018 | Conciliación diaria: total cobrado vs aplicado, pagos pendientes y su antigüedad (I-04/I-05) | Hecho | `conciliacion` | `tests/test_parte2b.py: test_conciliacion_cobrado_aplicado_y_detalle, test_conciliacion_refleja_requiere_revision_como_diferencia` |
