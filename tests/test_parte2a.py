import os, sys, unittest
from datetime import date
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import servicio as S
from app.db import conectar, crear_esquema
from app.cuentas import CuentasSimulado


def obligacion(cod="CR-0001", cliente="CLI-0001", vencimientos=("2026-11-05", "2026-12-05", "2027-01-05")):
    return {"codCredito": cod, "idCliente": cliente, "idSolicitud": "SOL-0001", "montoAprobado": "1200.00",
            "moneda": "PEN", "fechaDesembolso": "2026-10-05T10:00:00",
            "calendarioPagos": [
                {"numeroCuota": i, "fechaVencimiento": v, "montoCuota": "400.00"}
                for i, v in enumerate(vencimientos, 1)]}


def pago(ref, monto, cuenta="AH-001", cod="CR-0001", cliente="CLI-0001"):
    return {"codCliente": cliente, "codCredito": cod, "montoPago": monto, "cuentaOrigen": cuenta,
            "referenciaTransaccion": ref, "idCanal": "HB"}


class PruebasParte2A(unittest.TestCase):
    def setUp(self):
        self.db = conectar("sqlite:///:memory:")
        crear_esquema(self.db)
        self.cuentas = CuentasSimulado()

    # ---------------------------------------------------------- RF-COB-003
    def test_monto_a_pagar_desglosa_capital_y_mora(self):
        S.activar_obligacion(self.db, obligacion())
        r = S.monto_a_pagar(self.db, "CR-0001")
        self.assertEqual(r["numeroCuota"], 1)
        self.assertEqual(r["saldoCapital"], Decimal("400.00"))
        self.assertEqual(r["moraVigente"], Decimal("0.00"))
        self.assertEqual(r["totalAPagar"], Decimal("400.00"))

        S.registrar_mora(self.db, "CR-0001", 1, 5, "12.50")
        r = S.monto_a_pagar(self.db, "CR-0001")
        self.assertEqual(r["saldoCapital"], Decimal("400.00"))
        self.assertEqual(r["moraVigente"], Decimal("12.50"))
        self.assertEqual(r["totalAPagar"], Decimal("412.50"))

    def test_monto_a_pagar_sin_cuotas_pendientes_es_rechazado(self):
        S.activar_obligacion(self.db, obligacion())
        for i, m in enumerate(("400.00", "400.00", "400.00"), 1):
            S.registrar_pago(self.db, pago(f"OP-{i}", m), self.cuentas)
        with self.assertRaises(S.ErrorNegocio) as e:
            S.monto_a_pagar(self.db, "CR-0001")
        self.assertEqual(e.exception.regla, "RF-COB-003")

    # ---------------------------------------------------------- RF-COB-007
    def test_credito_en_mora_al_activar_con_cuota_ya_vencida(self):
        S.activar_obligacion(self.db, obligacion(vencimientos=("2020-01-01", "2026-12-05", "2027-01-05")))
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["estadoCredito"], "EN_MORA")

    def test_recalcular_estado_con_fecha_de_referencia_para_demostracion(self):
        S.activar_obligacion(self.db, obligacion())  # cuota 1 vence 2026-11-05, hoy no esta vencida: AL_DIA
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["estadoCredito"], "AL_DIA")
        c = S.recalcular_estado(self.db, "CR-0001", date(2026, 11, 10))
        self.assertEqual(c["estadoCredito"], "EN_MORA")
        c = S.recalcular_estado(self.db, "CR-0001", None)  # vuelve a evaluar con "hoy"
        self.assertEqual(c["estadoCredito"], "AL_DIA")

    def test_estado_se_recalcula_tras_pago_y_evento_queda_en_auditoria(self):
        S.activar_obligacion(self.db, obligacion(vencimientos=("2020-01-01", "2026-12-05", "2027-01-05")))
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["estadoCredito"], "EN_MORA")
        S.registrar_pago(self.db, pago("OP-1", "400.00"), self.cuentas)  # paga la cuota vencida por completo
        self.assertEqual(S.obtener_credito(self.db, "CR-0001")["estadoCredito"], "AL_DIA")
        tipos = {e["tipoEvento"] for e in S.auditoria(self.db, "CR-0001")}
        self.assertIn("CREDITO_EN_MORA", tipos)
        self.assertIn("CREDITO_AL_DIA", tipos)

    # ---------------------------------------------------------- RF-COB-008 / RF-COB-013
    def test_comprobante_desglosa_cuanto_fue_mora_y_cuanto_capital(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_mora(self.db, "CR-0001", 1, 5, "50.00")
        S.registrar_pago(self.db, pago("OP-1", "100.00"), self.cuentas)  # orden: mora primero
        c = S.comprobante(self.db, "OP-1")
        self.assertEqual(c["montoAplicadoMora"], Decimal("50.00"))
        self.assertEqual(c["montoAplicadoCapital"], Decimal("50.00"))
        self.assertEqual(c["moraRestanteCuota"], Decimal("0.00"))
        self.assertEqual(c["saldoRestanteCuota"], Decimal("350.00"))

    def test_excedente_se_calcula_sobre_capital_mas_mora(self):
        S.activar_obligacion(self.db, obligacion())
        S.registrar_mora(self.db, "CR-0001", 1, 5, "50.00")  # total adeudado de la cuota 1: 450.00
        with self.assertRaises(S.ErrorNegocio) as e:
            S.registrar_pago(self.db, pago("OP-1", "500.00"), self.cuentas)
        self.assertEqual(e.exception.regla, "RN-COB-011")

    # ---------------------------------------------------------- RF-COB-002 / RF-COB-012
    def test_consulta_de_creditos_y_pagos_por_idCliente(self):
        S.activar_obligacion(self.db, obligacion(cod="CR-A", cliente="CLI-X"))
        S.activar_obligacion(self.db, obligacion(cod="CR-B", cliente="CLI-X"))
        S.activar_obligacion(self.db, obligacion(cod="CR-C", cliente="CLI-OTRO"))
        S.registrar_pago(self.db, pago("OP-A1", "100.00", cod="CR-A", cliente="CLI-X"), self.cuentas)
        S.registrar_pago(self.db, pago("OP-B1", "100.00", cod="CR-B", cliente="CLI-X"), self.cuentas)

        creditos = S.creditos_por_cliente(self.db, "CLI-X")
        self.assertEqual({c["codCredito"] for c in creditos}, {"CR-A", "CR-B"})
        self.assertEqual(len(creditos[0]["cuotas"]), 3)

        pagos = S.pagos_por_cliente(self.db, "CLI-X")
        self.assertEqual(len(pagos), 2)
        self.assertEqual({p["referenciaTransaccion"] for p in pagos}, {"OP-A1", "OP-B1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
