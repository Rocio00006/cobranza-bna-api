# Estado de integración por módulo

Ningún otro módulo del sistema tiene API publicada todavía. Mientras tanto, cada interfaz se prueba
contra un simulador HTTP propio (`simuladores/`), por red real y a través del Bus de Servicios
(RNF-04), no con llamadas directas a `app/servicio.py`. La evidencia detallada de la corrida más
reciente está en `evidencias/integracion_<fecha>.json` / `.md`.

| Módulo | Interfaz(es) | Estado | Resultado obtenido | Fecha |
|---|---|---|---|---|
| Desembolso | CR-INT-06 | Probado contra simulador propio (`simuladores/desembolso_cliente.py`, script cliente) | Activa la obligación vía Bus; `HTTP 201`, cuotas creadas y crédito `AL_DIA` | 2026-10-25 |
| Cuentas | CR-INT-07 | Probado contra simulador HTTP propio (`simuladores/cuentas_app.py`, puerto 8001) | Cargo confirmado, rechazo por fondos insuficientes, demora/sin respuesta (INC-01) e idempotencia por `idOperacion`, todos vía Bus | 2026-10-25 |
| Home Banking | CR-INT-08 | Probado contra simulador propio (`simuladores/home_banking_cliente.py`, script cliente) | Pago parcial, duplicado idempotente y validación de `X-Token-Seguridad` vía Bus | 2026-10-25 |
| Seguridad | RF-COB-004 (token), CR-INT-10 (auditoría) | Módulo real sin API publicada; validado con `app/seguridad.py` (simulado dentro de Cobranza) | `TOKEN-INVALIDO` rechazado, bloqueo temporal tras 3 rechazos y su expiración, todo registrado en `EVENTO_AUDITORIA` | 2026-10-25 |
| CORE | RN-COB-005 (mora) | Módulo real sin API publicada | No se prueba por red (no hay CR-INT definida para que CORE empuje la mora); se registra manualmente vía `POST /creditos/{cod}/cuotas/{n}/mora`, simulando el valor que CORE enviaría | 2026-10-25 |

## Notas
- El Bus de Servicios (`simuladores/bus_app.py`, puerto 8090) es también un simulador: en producción
  sería el Bus real del banco. Mientras tanto, enruta `/cobranza/*` → Cobranza (8002) y `/cuentas/*` →
  Cuentas simulado (8001), reenvía los headers de autenticación y registra cada llamada
  (`GET /bus/registro`).
- Cuando Desembolso, Cuentas, Home Banking o Seguridad publiquen su API real, el contrato a validar es
  el de `docs/contratos-cr-int.md`; los simuladores quedan como referencia y para seguir probando en
  Testing sin depender de los módulos reales.
- "Probado contra simulador" significa: la integración por RED (HTTP, con el Bus de por medio) fue
  ejecutada y su resultado quedó en `evidencias/`; no implica que el contrato esté validado con el
  equipo dueño del módulo real.
