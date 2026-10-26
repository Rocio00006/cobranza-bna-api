# Entrega Fase II — Módulo Cobranza (SRV-CR-05)

Proyecto académico UCSM, curso GSTI. Banco ficticio "Banco Nacional de Arequipa" (BNA). Este
documento responde los cuatro puntos del entregable de la Fase II (ITIL 4) para el módulo Cobranza
(COB), servicio TI **SRV-CR-05 "Servicio de Cobro de Cuotas de Crédito"**.

> Los nombres de cada `RF-COB-NNN` son los oficiales del diccionario de requerimientos de Fase I.

---

## (a) APIs implementadas

Todas requieren el header `X-API-Key` (rol indicado), salvo `/salud`. Swagger: `GET /docs` (botón
**Authorize**). Postman: `postman/Cobranza-BNA.postman_collection.json`, organizada en las mismas
carpetas que la tabla de abajo.

| Endpoint | Método | Rol | RF / RN que demuestra | Verlo en Swagger / Postman |
|---|---|---|---|---|
| `/salud` | GET | — (libre) | — | Carpeta "Estado" en Swagger |
| `/cr-int-06/obligaciones` | POST | `INTEGRACION_BUS` | RF-COB-015 (Activar obligación tras desembolso), CR-INT-06 | Swagger "CR-INT-06"; Postman carpeta **CR-INT-06**, request 1 |
| `/creditos/{codCredito}` | GET | `COBRANZA_LEER` | RF-COB-002 (Consultar cronograma) | Postman **Consultas**, request 11 |
| `/creditos/{codCredito}/cuotas` | GET | `COBRANZA_LEER` | RF-COB-002 (Consultar cronograma) | Postman **Consultas**, request 12 |
| `/creditos/{codCredito}/monto-a-pagar` | GET | `COBRANZA_LEER` | RF-COB-003 (Calcular monto a pagar) | Postman **Consultas**, request 13 |
| `/creditos/{codCredito}/recalcular-estado` | POST | `COBRANZA_EJECUTAR` | RF-COB-007 (Actualizar estado del crédito) | Swagger "Consultas" (acción) |
| `/creditos/{codCredito}/pagos` | GET | `COBRANZA_LEER` | RF-COB-012 (Consultar historial) | Postman **Consultas**, request 14 |
| `/clientes/{idCliente}/creditos` | GET | `COBRANZA_LEER` | RF-COB-002 (cronograma, por idCliente) | Postman **Consultas**, request 15 |
| `/clientes/{idCliente}/pagos` | GET | `COBRANZA_LEER` | RF-COB-012 (historial, por idCliente) | Postman **Consultas**, request 16 |
| `/cr-int-08/pagos` | POST | `INTEGRACION_BUS` (+ `X-Token-Seguridad`) | CR-INT-08; RF-COB-001 (Registrar pago de cuota), RF-COB-004 (Validar identidad/medio de pago), RF-COB-005 (Aplicar pago a cuenta de crédito), RF-COB-010 (Registrar pago parcial), RF-COB-011 (Reportar pago fallido o reversado), RF-COB-016 (Idempotencia), RF-COB-017 (Pagos superiores a la cuota) | Swagger "CR-INT-08"; Postman carpeta **CR-INT-08**, requests 5-10 |
| `/pagos/{ref}/comprobante` | GET | `COBRANZA_LEER` | RF-COB-008 (Emitir comprobante), RF-COB-013 (Recargo por mora en el comprobante) | Postman **Consultas**, request 17 |
| `/pagos/pendientes` | GET | `COBRANZA_LEER` | RF-COB-011 (Reportar pago fallido o reversado), INC-01 | Postman **Pendientes y conciliacion**, request 22 |
| `/pagos/{ref}/resolver` | POST | `COBRANZA_EJECUTAR` | RF-COB-011 (Reportar pago fallido o reversado), RN-COB-009 | Postman **Pendientes y conciliacion**, request 23 |
| `/conciliacion` | GET | `COBRANZA_LEER` | RF-COB-018 (Conciliación diaria) | Postman **Pendientes y conciliacion**, request 24 |
| `/metricas` | GET | `COBRANZA_LEER` | Indicadores I-05 (sin RF específico) | Postman **Metricas**, request 30 |
| `/creditos/{cod}/cuotas/{n}/mora` | POST | `COBRANZA_EJECUTAR` | RF-COB-009 (Calcular interés moratorio — pendiente del Comité; solo se registra lo recibido), RN-COB-005/010 | Postman **Mora**, requests 18-19 |
| `/creditos/{cod}/cuotas/{n}/mora` | GET | `COBRANZA_LEER` | RF-COB-009 | Postman **Mora**, request 20 |
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

| RF | Nombre oficial (Fase I) | Estado | Código | Prueba(s) |
|---|---|---|---|---|
| RF-COB-001 | Registrar pago de cuota | Hecho | `app/servicio.py:registrar_pago` (flujo completo CR-INT-08) | `tests/test_servicio.py: test_pago_parcial_deja_cuota_parcial, test_pago_completo_cierra_cuota_y_pasa_a_la_siguiente` |
| RF-COB-002 | Consultar cronograma | Hecho (por `codCredito` e `idCliente`; por DNI, falta) | `obtener_credito`, `creditos_por_cliente` | `tests/test_servicio.py: test_activacion_crea_credito_y_cuotas`; `tests/test_parte2a.py: test_consulta_de_creditos_y_pagos_por_idCliente` |
| RF-COB-003 | Calcular monto a pagar | Hecho | `monto_a_pagar` | `tests/test_parte2a.py: test_monto_a_pagar_desglosa_capital_y_mora, test_monto_a_pagar_sin_cuotas_pendientes_es_rechazado` |
| RF-COB-004 | Validar identidad o medio de pago | Hecho (identidad simulada; medio de pago vía Cuentas/CR-INT-07) | `app/seguridad.py:SeguridadSimulada`, `servicio.registrar_pago` (token); `cuentas.cargar` (cuenta/fondos, RN-COB-009) | `tests/test_parte2c.py` (8 pruebas: token inválido/vacío/válido, bloqueo, reinicio de contador, auditoría) |
| RF-COB-005 | Aplicar pago a cuenta de crédito | Hecho | `_aplicar_a_cuota`, interacción CR-INT-07 en `registrar_pago`/`resolver_pago` | `tests/test_servicio.py: test_pago_parcial_deja_cuota_parcial, test_credito_se_cancela_al_pagar_todo`; `tests/test_parte2b.py` (resolver_pago) |
| RF-COB-006 | Recordatorio | Fuera de alcance | — | — |
| RF-COB-007 | Actualizar estado del crédito | Hecho (catálogo provisional: AL_DIA/EN_MORA/CANCELADO) | `recalcular_estado_credito`, `recalcular_estado`, endpoint `POST /creditos/{cod}/recalcular-estado` | `tests/test_parte2a.py: test_credito_en_mora_al_activar_con_cuota_ya_vencida, test_recalcular_estado_con_fecha_de_referencia_para_demostracion, test_estado_se_recalcula_tras_pago_y_evento_queda_en_auditoria` |
| RF-COB-008 | Emitir comprobante | Hecho | `comprobante` | `tests/test_parte2a.py: test_comprobante_desglosa_cuanto_fue_mora_y_cuanto_capital` |
| RF-COB-009 | Calcular interés moratorio | Parcial — pendiente del Comité (fórmula y responsable); Cobranza solo **registra** la mora recibida | `registrar_mora`, `historial_mora` | `tests/test_servicio.py: test_mora_se_refleja_y_el_recalculo_conserva_historial`; `tests/test_parte2a.py` (pruebas de mora / RN-COB-010) |
| RF-COB-010 | Registrar pago parcial | Hecho | `registrar_pago` (cuota queda `PARCIAL` cuando `monto < saldo adeudado`) | `tests/test_servicio.py: test_pago_parcial_deja_cuota_parcial` |
| RF-COB-011 | Reportar pago fallido o reversado | Hecho | rama `RECHAZADO` de `registrar_pago`/`resolver_pago`; `pagos_pendientes`, `resolver_pago` (INC-01) | `tests/test_servicio.py: test_cuentas_rechaza_y_la_cuota_no_cambia`; `tests/test_parte2b.py` (7 pruebas) |
| RF-COB-012 | Consultar historial | Hecho (por `codCredito` e `idCliente`; por DNI, falta) | `historial_pagos`, `pagos_por_cliente` | `tests/test_servicio.py: test_comprobante_y_auditoria`; `tests/test_parte2a.py: test_consulta_de_creditos_y_pagos_por_idCliente` |
| RF-COB-013 | Recargo por mora en el comprobante | Hecho | `comprobante` (`montoAplicadoMora`) | `tests/test_parte2a.py: test_comprobante_desglosa_cuanto_fue_mora_y_cuanto_capital` |
| RF-COB-014 | Notificar pago | Fuera de alcance | — | — |
| RF-COB-015 | Activar obligación tras desembolso | Hecho | `activar_obligacion` | `tests/test_servicio.py: test_activacion_crea_credito_y_cuotas, test_activacion_duplicada_es_rechazada` |
| RF-COB-016 | Idempotencia | Hecho | chequeo de `referenciaTransaccion` al inicio de `registrar_pago` (= RN-INT-CR-006) | `tests/test_servicio.py: test_idempotencia_no_duplica_el_pago` |
| RF-COB-017 | Pagos superiores a la cuota | Hecho (rechazo); tratamiento del excedente pendiente del Comité | chequeo de `monto > total_adeudado` en `registrar_pago` (= RN-COB-011) | `tests/test_servicio.py: test_excedente_se_rechaza_hasta_definicion_del_comite`; `tests/test_parte2a.py: test_excedente_se_calcula_sobre_capital_mas_mora` |
| RF-COB-018 | Conciliación diaria | Hecho | `conciliacion` | `tests/test_parte2b.py: test_conciliacion_cobrado_aplicado_y_detalle, test_conciliacion_refleja_requiere_revision_como_diferencia` |
