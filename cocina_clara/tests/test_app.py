import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import app as app_module
import database
import gemini_service


class EcoMenuTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DB_PATH = os.path.join(self.temp_dir.name, "test.sqlite")
        database.init_db()
        app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def login(self, username, password):
        client = app_module.app.test_client()
        response = client.post(
            "/login", data={"usuario": username, "clave": password}
        )
        self.assertEqual(response.status_code, 302)
        return client

    def test_owner_login_accepts_utf8_username(self):
        page = app_module.app.test_client().get("/login")
        self.assertIn('data-usuario="due\u00f1o"', page.get_data(as_text=True))

        owner = self.login("due\u00f1o", "dueno123")
        self.assertEqual(owner.get("/dueno").status_code, 200)

    def test_recovery_summary_tracks_outputs_and_net_loss(self):
        resumen_inicial = database.resumen_recuperacion()
        database.agregar_insumo(
            "Producto de prueba",
            10,
            "kg",
            (date.today() + timedelta(days=10)).isoformat(),
            "Perecederos",
            100,
            date.today().isoformat(),
            None,
        )
        product = next(
            row
            for row in database.listar_insumos()
            if row["nombre"] == "Producto de prueba"
        )

        database.registrar_salida(product["id"], "ganaderia", 2, 5, "Encargado")
        database.registrar_salida(product["id"], "reciclaje", 1, 2, "Encargado")
        database.registrar_salida(product["id"], "promocion", 1, 4, "Encargado")
        database.registrar_salida(product["id"], "perdida", 1, 0, "Encargado")

        resumen = database.resumen_recuperacion()
        recuperado = resumen_inicial["recuperado"] + 11
        perdida_bruta = resumen_inicial["perdida_bruta"] + 10
        self.assertEqual(resumen["recuperado"], recuperado)
        self.assertEqual(resumen["perdida_bruta"], perdida_bruta)
        self.assertEqual(resumen["perdida_neta"], max(0, perdida_bruta - recuperado))
        self.assertEqual(
            resumen["kilos_ganaderia"],
            resumen_inicial["kilos_ganaderia"] + 2,
        )
        self.assertEqual(
            resumen["lotes_reciclados"],
            resumen_inicial["lotes_reciclados"] + 1,
        )
        self.assertEqual(database.obtener_insumo(product["id"])["cantidad"], 5)

    def test_manager_can_send_an_editable_gemini_report_to_owner(self):
        manager = self.login("encargado", "encargado123")
        with patch.object(
            gemini_service,
            "analizar_con_gemini",
            return_value="Borrador generado.",
        ):
            draft = manager.post(
                "/reporte", data={"accion": "preparar", "modo": "gemini"}
            )
        self.assertEqual(draft.status_code, 200)
        self.assertIn("Borrador generado.", draft.get_data(as_text=True))

        sent = manager.post(
            "/reporte",
            data={
                "accion": "enviar",
                "modo": "gemini",
                "texto": "Borrador editado por el encargado.",
            },
        )
        self.assertEqual(sent.status_code, 302)

        owner = self.login("due\u00f1o", "dueno123")
        page = owner.get("/dueno")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Borrador editado por el encargado.", page.get_data(as_text=True))

        reporte = database.listar_reportes_dueno()[0]
        self.assertEqual(reporte["leido"], 0)
        self.assertEqual(
            owner.post(f"/reportes/{reporte['id']}/leer").status_code, 302
        )
        self.assertEqual(database.listar_reportes_dueno()[0]["leido"], 1)

    def test_employee_keeps_expired_stock_protection(self):
        employee = self.login("empleado", "empleado123")
        page = employee.get("/avisos")
        self.assertEqual(page.status_code, 200)
        self.assertIn("recicladoras", page.get_data(as_text=True))
        self.assertNotIn("recicladoras", employee.get("/sugerencias").get_data(as_text=True))
        self.assertNotIn("Salidas y recuperación", page.get_data(as_text=True))
        self.assertEqual(employee.get("/salidas").status_code, 302)

        expired = next(
            row
            for row in database.listar_insumos()
            if database.dias_para_caducar(row["caducidad"]) < 0
        )
        original_quantity = expired["cantidad"]

        response = employee.post(
            "/gastos/nuevo",
            data={"insumo_id": str(expired["id"]), "cantidad": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("ya caduc\u00f3", response.get_data(as_text=True))
        self.assertEqual(
            database.obtener_insumo(expired["id"])["cantidad"], original_quantity
        )

    def test_recovery_guidance_only_appears_in_role_specific_sections(self):
        manager = self.login("encargado", "encargado123")
        self.assertIn("recicladoras", manager.get("/avisos").get_data(as_text=True))
        self.assertNotIn(
            "recicladoras", manager.get("/inventario").get_data(as_text=True)
        )

        owner = self.login("due\u00f1o", "dueno123")
        self.assertNotIn("recicladoras", owner.get("/dueno").get_data(as_text=True))
        self.assertNotIn("recicladoras", owner.get("/analisis").get_data(as_text=True))
        self.assertIn("recicladoras", owner.get("/reporte").get_data(as_text=True))
        self.assertIn("reciclaje", owner.get("/salidas").get_data(as_text=True))
        self.assertNotIn("recicladoras", owner.get("/avisos").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
