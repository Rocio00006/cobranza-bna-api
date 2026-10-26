"""Parte 4: capturas automaticas de Swagger (/docs) con Playwright, para la evidencia del entregable.

Requiere: pip install playwright && playwright install chromium, y una instancia de Cobranza
corriendo (por defecto http://127.0.0.1:8000; ajustar BASE_URL si usas otro puerto, ver README).

Uso: python simuladores/capturas_swagger.py
Guarda los PNG en evidencias/capturas/.
"""
import os
import sys

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = os.environ.get("CAPTURAS_BASE_URL", "http://127.0.0.1:8000")
CARPETA = os.path.join(RAIZ, "evidencias", "capturas")

# Clave de DEMOSTRACION, nunca la real de .env: la captura queda en el repo, y el valor real del
# dev no debe aparecer en pantalla. Arranca el servidor para este script con
# API_KEY_INTEGRACION_BUS=DEMO-CAPTURA-SWAGGER (override de entorno, no toca .env).
API_KEY_DEMO = os.environ.get("CAPTURAS_API_KEY", "DEMO-CAPTURA-SWAGGER")
API_KEY_LEER_DEMO = os.environ.get("CAPTURAS_API_KEY_LEER", "DEMO-COBRANZA-LEER")


def main():
    os.makedirs(CARPETA, exist_ok=True)
    api_key_bus = API_KEY_DEMO

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1440, "height": 1000})

        # 1. Swagger UI, vista inicial (lista de tags/endpoints)
        pagina.goto(f"{BASE_URL}/docs", wait_until="networkidle")
        pagina.wait_for_selector("text=Cobranza BNA")
        pagina.screenshot(path=os.path.join(CARPETA, "01_swagger_inicio.png"), full_page=True)
        print("01_swagger_inicio.png")

        # 2. Dialogo Authorize abierto
        pagina.click("button.btn.authorize")
        pagina.wait_for_selector("text=Available authorizations")
        pagina.screenshot(path=os.path.join(CARPETA, "02_swagger_authorize.png"))
        print("02_swagger_authorize.png")

        # 3. Autorizado con la clave INTEGRACION_BUS (se pega el valor pero no se muestra en claro
        #    en la captura siguiente: Swagger la enmascara en el input una vez cerrado el dialogo)
        pagina.fill("input[type=text]", api_key_bus)
        pagina.locator("button:has-text('Authorize')").last.click()
        pagina.click("button:has-text('Close')")
        pagina.wait_for_timeout(300)
        pagina.screenshot(path=os.path.join(CARPETA, "03_swagger_autorizado.png"), full_page=True)
        print("03_swagger_autorizado.png (candados cerrados)")

        # 4. CR-INT-06: expandir el operation y ejecutar "Try it out" con el ejemplo
        pagina.click("button:has-text('/cr-int-06/obligaciones')")
        pagina.wait_for_timeout(300)
        pagina.click("button:has-text('Try it out')")
        pagina.wait_for_timeout(200)
        pagina.click("button:has-text('Execute')")
        pagina.wait_for_selector("text=Server response", timeout=10000)
        pagina.wait_for_timeout(500)
        pagina.screenshot(path=os.path.join(CARPETA, "04_cr_int_06_respuesta.png"), full_page=True)
        print("04_cr_int_06_respuesta.png")
        pagina.click("button:has-text('/cr-int-06/obligaciones')")  # colapsar de nuevo

        # 5. CR-INT-08: pago sobre el credito recien activado, con X-Token-Seguridad (RF-COB-004)
        pagina.click("button:has-text('/cr-int-08/pagos')")
        pagina.wait_for_timeout(300)
        pagina.click("button:has-text('Try it out')")
        pagina.wait_for_timeout(200)
        pagina.locator("tr:has-text('X-Token-Seguridad') input").fill("TOKEN-DEMO-CAPTURA")
        pagina.click("button:has-text('Execute')")
        pagina.wait_for_selector("text=Server response", timeout=10000)
        pagina.wait_for_timeout(500)
        pagina.screenshot(path=os.path.join(CARPETA, "05_cr_int_08_respuesta.png"), full_page=True)
        print("05_cr_int_08_respuesta.png")
        pagina.click("button:has-text('/cr-int-08/pagos')")  # colapsar

        # 6. CR-INT-10: auditoria, mostrando usuarioOperador (rol) y resultado. Requiere COBRANZA_LEER,
        # asi que primero se re-autoriza con esa clave de demostracion (distinta de la de INTEGRACION_BUS).
        pagina.click("button.btn.authorize")
        pagina.wait_for_selector("text=Available authorizations")
        if pagina.locator("button:has-text('Logout')").count():
            pagina.click("button:has-text('Logout')")
            pagina.wait_for_timeout(200)
        pagina.fill("input[type=text]", API_KEY_LEER_DEMO)
        pagina.locator("button:has-text('Authorize')").last.click()
        pagina.click("button:has-text('Close')")
        pagina.wait_for_timeout(300)

        pagina.click("button:has-text('/auditoria')")
        pagina.wait_for_timeout(300)
        pagina.click("button:has-text('Try it out')")
        pagina.wait_for_timeout(200)
        pagina.click("button:has-text('Execute')")
        pagina.wait_for_selector("text=Server response", timeout=10000)
        pagina.wait_for_timeout(500)
        pagina.screenshot(path=os.path.join(CARPETA, "06_auditoria_respuesta.png"), full_page=True)
        print("06_auditoria_respuesta.png")

        navegador.close()

    print(f"\nCapturas guardadas en {CARPETA}")


if __name__ == "__main__":
    main()
