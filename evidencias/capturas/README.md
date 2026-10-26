# Capturas de Swagger (`/docs`)

Generadas automáticamente con Playwright (`simuladores/capturas_swagger.py`) contra una instancia
standalone de Cobranza (Cuentas simulada en memoria), usando claves de **demostración** (no las
reales de `.env`): `DEMO-CAPTURA-SWAGGER` (rol INTEGRACION_BUS) y `DEMO-COBRANZA-LEER` (rol
COBRANZA_LEER).

| Archivo | Qué muestra |
|---|---|
| `01_swagger_inicio.png` | Swagger UI recién cargado: título, descripción de la API y el botón **Authorize**. |
| `02_swagger_authorize.png` | Diálogo de **Authorize** abierto, pidiendo el header `X-API-Key`. |
| `03_swagger_autorizado.png` | Todos los endpoints con el candado **cerrado** tras autorizar; se ve la lista completa de carpetas/endpoints de la API. |
| `04_cr_int_06_respuesta.png` | `POST /cr-int-06/obligaciones` ejecutado con "Try it out": petición, curl, y respuesta `201` con el crédito y sus cuotas. |
| `05_cr_int_08_respuesta.png` | `POST /cr-int-08/pagos` ejecutado con `X-Token-Seguridad`: respuesta `200` `CONFIRMADO` con el desglose mora/capital. |
| `06_auditoria_respuesta.png` | `GET /auditoria` (re-autorizado con el rol `COBRANZA_LEER`): respuesta `200` mostrando `usuarioOperador` (el rol que hizo cada llamada) y el campo `resultado` (CR-INT-10). |

Para regenerarlas: `python simuladores/capturas_swagger.py` (requiere
`pip install playwright && playwright install chromium`, y una instancia de Cobranza corriendo —
ver `CAPTURAS_BASE_URL` en el script).
