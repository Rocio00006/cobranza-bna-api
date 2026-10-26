# Prototipo navegable: Home Banking BNA – Pago de cuotas

Prototipo de la interfaz del Servicio de Cobro de Cuotas de Crédito (SRV-CR-05) en el canal Home Banking,
único canal confirmado para Cobranza (CR-INT-08).

- Un solo archivo HTML, sin dependencias: abrir `index.html` en el navegador o visitarlo en GitHub Pages.
- Datos ficticios. **No está conectado a la API todavía.** Las respuestas de Cuentas y de Seguridad se eligen en el
  panel "Simulación (solo demostración)" de la parte superior.
- Usa los mismos datos y reglas de la API: crédito CR-0001 en mora, cuota 2 con S/ 400.00 de capital y S/ 12.50 de mora,
  imputación primero a mora y luego a capital (supuesto pendiente del Comité).

Parámetros opcionales en la URL: `?pantalla=pagar|verificacion|historial|...`, `?cuentas=confirmado|fondos|sin_respuesta`,
`?seguridad=normal|bloqueado`, `?demo=0` (oculta el panel de simulación, para capturas).

| Pantalla | Endpoint o regla de la API |
|---|---|
| Ingreso | X-Token-Seguridad (RF-COB-004) |
| Mis créditos | GET /clientes/{idCliente}/creditos (RF-COB-002, RF-COB-007) |
| Pagar cuota | GET /creditos/{codCredito}/monto-a-pagar (RF-COB-003, RF-COB-010) |
| Confirma tu pago / Pago confirmado | POST /cr-int-08/pagos, GET /pagos/{ref}/comprobante (RF-COB-001, 005, 008, 013) |
| No se pudo realizar el pago | Rechazo de Cuentas (RN-COB-009) |
| Estamos confirmando tu pago | Pago PENDIENTE (RF-COB-011, INC-01) |
| Monto no permitido | Excedente, 422 (RN-COB-011) |
| Pagos bloqueados | Bloqueo tras 3 rechazos de token (RF-COB-004) |
| Historial de pagos | GET /creditos/{codCredito}/pagos (RF-COB-012) |
