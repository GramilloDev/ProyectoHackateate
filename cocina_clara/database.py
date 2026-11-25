"""Datos y consultas de Eco Menu (SQLite, sin ORM)."""

import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cocina_clara.db"

UNIDADES = ["kg", "g", "L", "ml", "pieza", "manojo", "caja", "bolsa"]
CATEGORIAS = ["Lácteos", "Perecederos", "Proteínas", "No perecederos", "Otros"]
DESTINOS = ["consumo", "promocion", "ganaderia", "reciclaje", "perdida"]
DESTINO_LABELS = {
    "consumo": "Consumo",
    "promocion": "Promoción",
    "ganaderia": "Ganadería",
    "reciclaje": "Reciclaje",
    "perdida": "Pérdida",
}
DESTINO_ALIASES = {
    "promoción": "promocion",
    "ganadería": "ganaderia",
    "pérdida": "perdida",
}


def get_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def init_db():
    """Crea las tablas y carga los datos de ejemplo la primera vez."""
    conexion = get_db()
    conexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cantidad REAL NOT NULL,
            cantidad_inicial REAL NOT NULL,
            unidad TEXT NOT NULL,
            caducidad TEXT NOT NULL,
            costo_unitario REAL NOT NULL DEFAULT 0,
            fecha_registro TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insumo_id INTEGER NOT NULL,
            cantidad REAL NOT NULL,
            fecha TEXT NOT NULL,
            registrado_por TEXT NOT NULL,
            FOREIGN KEY (insumo_id) REFERENCES insumos (id)
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platillo TEXT NOT NULL,
            precio REAL NOT NULL,
            unidades INTEGER NOT NULL,
            fecha TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS salidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insumo_id INTEGER,
            producto TEXT NOT NULL,
            destino TEXT NOT NULL CHECK (
                destino IN ('consumo', 'promocion', 'ganaderia', 'reciclaje', 'perdida')
            ),
            cantidad REAL NOT NULL CHECK (cantidad > 0),
            unidad TEXT NOT NULL,
            monto_recuperado REAL NOT NULL DEFAULT 0 CHECK (monto_recuperado >= 0),
            costo_unitario REAL NOT NULL DEFAULT 0 CHECK (costo_unitario >= 0),
            fecha TEXT NOT NULL,
            registrado_por TEXT NOT NULL,
            gasto_id INTEGER UNIQUE,
            FOREIGN KEY (insumo_id) REFERENCES insumos (id),
            FOREIGN KEY (gasto_id) REFERENCES gastos (id)
        );

        CREATE TABLE IF NOT EXISTS reportes_dueno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            autor TEXT NOT NULL,
            texto TEXT NOT NULL,
            leido INTEGER NOT NULL DEFAULT 0 CHECK (leido IN (0, 1))
        );
        """
    )
    columnas = {
        fila["name"]
        for fila in conexion.execute("PRAGMA table_info(insumos)").fetchall()
    }
    migrar_categoria = "categoria" not in columnas
    migrar_fecha_compra = "fecha_compra" not in columnas
    migrar_dinero_invertido = "dinero_invertido" not in columnas
    if migrar_categoria:
        conexion.execute(
            "ALTER TABLE insumos ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Otros'"
        )
    if migrar_fecha_compra:
        conexion.execute("ALTER TABLE insumos ADD COLUMN fecha_compra TEXT")
    if "reabasto_fecha" not in columnas:
        conexion.execute("ALTER TABLE insumos ADD COLUMN reabasto_fecha TEXT")
    if migrar_dinero_invertido:
        conexion.execute(
            "ALTER TABLE insumos ADD COLUMN dinero_invertido REAL NOT NULL DEFAULT 0"
        )
    hay_datos = conexion.execute("SELECT COUNT(*) FROM insumos").fetchone()[0]
    if hay_datos == 0:
        _cargar_datos_ejemplo(conexion)
    if migrar_categoria:
        conexion.execute(
            """
            UPDATE insumos
            SET categoria = CASE
            WHEN LOWER(nombre) LIKE '%queso%' OR LOWER(nombre) LIKE '%crema%'
                OR LOWER(nombre) LIKE '%leche%' OR LOWER(nombre) LIKE '%yogur%'
                THEN 'Lácteos'
            WHEN LOWER(nombre) LIKE '%pollo%' OR LOWER(nombre) LIKE '%carne%'
                OR LOWER(nombre) LIKE '%pescado%' OR LOWER(nombre) LIKE '%huevo%'
                THEN 'Proteínas'
            WHEN LOWER(nombre) LIKE '%arroz%' OR LOWER(nombre) LIKE '%frijol%'
                OR LOWER(nombre) LIKE '%lenteja%' OR LOWER(nombre) LIKE '%harina%'
                OR LOWER(nombre) LIKE '%aceite%'
                THEN 'No perecederos'
            WHEN categoria = 'Otros' AND (
                LOWER(nombre) LIKE '%lechuga%' OR LOWER(nombre) LIKE '%tomate%'
                OR LOWER(nombre) LIKE '%aguacate%' OR LOWER(nombre) LIKE '%tortilla%'
                OR LOWER(nombre) LIKE '%cebolla%' OR LOWER(nombre) LIKE '%pan%'
                OR LOWER(nombre) LIKE '%fruta%' OR LOWER(nombre) LIKE '%verdura%'
            ) THEN 'Perecederos'
            ELSE categoria
            END
            """
        )
    if migrar_fecha_compra:
        conexion.execute(
            "UPDATE insumos SET fecha_compra = fecha_registro WHERE fecha_compra IS NULL"
        )
    if migrar_dinero_invertido:
        conexion.execute(
            "UPDATE insumos SET dinero_invertido = cantidad_inicial * costo_unitario"
        )
    conexion.commit()
    conexion.close()


def _cargar_datos_ejemplo(conexion):
    hoy = date.today()

    # (nombre, existencia actual, cantidad inicial, unidad, días para caducar, costo unitario)
    insumos = [
        ("Lechuga romana", 4, 4, "kg", 2, 28),
        ("Tomate", 6, 7.5, "kg", 3, 25),
        ("Queso fresco", 3, 3, "kg", 1, 120),
        ("Pollo", 8, 10, "kg", 5, 95),
        ("Crema", 2, 2, "L", 0, 45),
        ("Aguacate", 5, 5, "kg", -1, 80),
        ("Arroz", 20, 20, "kg", 180, 22),
        ("Frijol", 15, 15, "kg", 240, 28),
        ("Tortilla de maíz", 10, 13, "kg", 2, 18),
        ("Cebolla", 7, 7, "kg", 20, 20),
    ]

    for nombre, cantidad, inicial, unidad, dias, costo in insumos:
        caducidad = (hoy + timedelta(days=dias)).isoformat()
        conexion.execute(
            """
            INSERT INTO insumos
                (nombre, cantidad, cantidad_inicial, unidad, caducidad, costo_unitario, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (nombre, cantidad, inicial, unidad, caducidad, costo, (hoy - timedelta(days=7)).isoformat()),
        )

    # Gastos de ejemplo para que el reporte no aparezca vacío.
    gastos = [
        ("Pollo", 2, 1),
        ("Tomate", 1.5, 2),
        ("Tortilla de maíz", 3, 2),
    ]
    for nombre, cantidad, dias_atras in gastos:
        fila = conexion.execute("SELECT id FROM insumos WHERE nombre = ?", (nombre,)).fetchone()
        conexion.execute(
            "INSERT INTO gastos (insumo_id, cantidad, fecha, registrado_por) VALUES (?, ?, ?, ?)",
            (fila["id"], cantidad, (hoy - timedelta(days=dias_atras)).isoformat(), "Empleado de prueba"),
        )

    # (platillo, unidades vendidas los últimos días, precio)
    ventas = [
        ("Tacos de pollo", 12, 65),
        ("Enchiladas verdes", 6, 85),
        ("Sopa de tortilla", 9, 70),
        ("Ensalada de la casa", 3, 75),
        ("Mole poblano", 2, 110),
        ("Arroz con pollo", 4, 90),
        ("Quesadillas", 14, 45),
        ("Flan casero", 5, 40),
    ]
    for posicion, (platillo, unidades, precio) in enumerate(ventas):
        conexion.execute(
            "INSERT INTO ventas (platillo, precio, unidades, fecha) VALUES (?, ?, ?, ?)",
            (platillo, precio, unidades, (hoy - timedelta(days=posicion % 7 + 1)).isoformat()),
        )


def listar_insumos():
    """Insumos con el total gastado (descontado del inventario) por insumo."""
    conexion = get_db()
    try:
        return conexion.execute(
            """
            SELECT i.*, COALESCE(SUM(g.cantidad), 0) AS gastado
            FROM insumos i
            LEFT JOIN gastos g ON g.insumo_id = i.id
            GROUP BY i.id
            ORDER BY i.caducidad ASC, i.nombre ASC
            """
        ).fetchall()
    finally:
        conexion.close()


def obtener_insumo(insumo_id):
    conexion = get_db()
    try:
        return conexion.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()
    finally:
        conexion.close()


def listar_ventas():
    conexion = get_db()
    try:
        return conexion.execute(
            "SELECT * FROM ventas ORDER BY unidades ASC, platillo ASC"
        ).fetchall()
    finally:
        conexion.close()


def dias_para_caducar(caducidad, hoy=None):
    if isinstance(caducidad, str):
        caducidad = date.fromisoformat(caducidad)
    return (caducidad - (hoy or date.today())).days


def estado_insumo(caducidad, cantidad):
    """Devuelve (texto visible, clase CSS)."""
    dias = dias_para_caducar(caducidad)
    if cantidad <= 0:
        return "Agotado", "agotado"
    if dias < 0:
        return "Caducado", "caducado"
    if dias <= 3:
        return "Próximo a caducar", "aviso"
    return "Disponible", "ok"


def _costo_referencia(nombre):
    """Para insumos nuevos usa el costo promedio del mismo producto, si existe."""
    conexion = get_db()
    try:
        fila = conexion.execute(
            "SELECT AVG(costo_unitario) FROM insumos WHERE LOWER(nombre) = LOWER(?) AND costo_unitario > 0",
            (nombre,),
        ).fetchone()
        return round(fila[0], 2) if fila and fila[0] else 0.0
    finally:
        conexion.close()


def agregar_insumo(
    nombre,
    cantidad,
    unidad,
    caducidad,
    categoria="Otros",
    dinero_invertido=0,
    fecha_compra=None,
    reabasto_fecha=None,
):
    costo_referencia = _costo_referencia(nombre)
    costo_unitario = (
        dinero_invertido / cantidad
        if dinero_invertido > 0
        else costo_referencia
    )
    conexion = get_db()
    try:
        conexion.execute(
            """
            INSERT INTO insumos
                (nombre, cantidad, cantidad_inicial, unidad, caducidad, costo_unitario,
                 fecha_registro, categoria, fecha_compra, reabasto_fecha, dinero_invertido)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre,
                cantidad,
                cantidad,
                unidad,
                caducidad,
                costo_unitario,
                date.today().isoformat(),
                categoria,
                fecha_compra or date.today().isoformat(),
                reabasto_fecha,
                dinero_invertido,
            ),
        )
        conexion.commit()
    finally:
        conexion.close()


def registrar_salida(insumo_id, tipo, cantidad, monto_recuperado, registrado_por):
    """Registra y descuenta una salida validada del inventario."""
    tipo = DESTINO_ALIASES.get(tipo, tipo)
    if tipo not in DESTINOS:
        raise ValueError("Selecciona un destino válido para el insumo.")
    if not math.isfinite(cantidad) or cantidad <= 0:
        raise ValueError("La cantidad debe ser un número mayor que cero.")
    if not math.isfinite(monto_recuperado) or monto_recuperado < 0:
        raise ValueError("El monto recuperado no puede ser negativo.")
    if tipo not in ("promocion", "ganaderia", "reciclaje") and monto_recuperado:
        raise ValueError("Solo promociones, ganadería y reciclaje pueden registrar recuperación.")

    conexion = get_db()
    try:
        fila = conexion.execute(
            "SELECT * FROM insumos WHERE id = ?", (insumo_id,)
        ).fetchone()
        if fila is None:
            raise ValueError("El insumo seleccionado no existe.")
        if cantidad > fila["cantidad"]:
            raise ValueError(
                f"Solo hay {fila['cantidad']:g} {fila['unidad']} de «{fila['nombre']}»."
            )
        if tipo in ("consumo", "promocion") and date.fromisoformat(fila["caducidad"]) < date.today():
            raise ValueError(
                f"«{fila['nombre']}» ya caducó. No se puede registrar como consumo o promoción."
            )

        conexion.execute(
            "UPDATE insumos SET cantidad = cantidad - ? WHERE id = ?",
            (cantidad, insumo_id),
        )
        conexion.execute(
            """
            INSERT INTO salidas
                (insumo_id, producto, destino, cantidad, unidad, monto_recuperado,
                 costo_unitario, fecha, registrado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                insumo_id,
                fila["nombre"],
                tipo,
                cantidad,
                fila["unidad"],
                monto_recuperado,
                fila["costo_unitario"],
                date.today().isoformat(),
                registrado_por,
            ),
        )
        conexion.commit()
    finally:
        conexion.close()


def registrar_reporte_dueno(autor, texto):
    conexion = get_db()
    try:
        cursor = conexion.execute(
            "INSERT INTO reportes_dueno (fecha, autor, texto) VALUES (?, ?, ?)",
            (date.today().isoformat(), autor, texto),
        )
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


def listar_reportes_dueno():
    conexion = get_db()
    try:
        return conexion.execute(
            "SELECT * FROM reportes_dueno ORDER BY fecha DESC, id DESC"
        ).fetchall()
    finally:
        conexion.close()


def marcar_reporte_leido(reporte_id):
    conexion = get_db()
    try:
        cursor = conexion.execute(
            "UPDATE reportes_dueno SET leido = 1 WHERE id = ?", (reporte_id,)
        )
        conexion.commit()
        return cursor.rowcount > 0
    finally:
        conexion.close()


def listar_salidas():
    conexion = get_db()
    try:
        return conexion.execute(
            """
            SELECT s.*, COALESCE(i.nombre, s.producto) AS insumo,
                   s.destino AS tipo
            FROM salidas s LEFT JOIN insumos i ON i.id = s.insumo_id
            ORDER BY s.fecha DESC, s.id DESC
            """
        ).fetchall()
    finally:
        conexion.close()


def resumen_recuperacion():
    hoy = date.today().isoformat()
    conexion = get_db()
    try:
        filas = conexion.execute(
            """
            SELECT s.destino AS tipo, s.cantidad, s.unidad, s.monto_recuperado,
                   s.costo_unitario
            FROM salidas s
            """
        ).fetchall()
        perdida_inventario = conexion.execute(
            """
            SELECT COALESCE(SUM(cantidad * costo_unitario), 0)
            FROM insumos
            WHERE caducidad < ? AND cantidad > 0
            """,
            (hoy,),
        ).fetchone()[0]
    finally:
        conexion.close()

    recuperado = sum(
        fila["monto_recuperado"]
        for fila in filas
        if fila["tipo"] in ("promocion", "ganaderia", "reciclaje")
    )
    perdida_bruta = perdida_inventario + sum(
        fila["cantidad"] * fila["costo_unitario"]
        for fila in filas
        if fila["tipo"] == "perdida"
    )
    kilos_ganaderia = sum(
        fila["cantidad"] if fila["unidad"] == "kg"
        else fila["cantidad"] / 1000 if fila["unidad"] == "g"
        else 0
        for fila in filas
        if fila["tipo"] == "ganaderia"
    )
    return {
        "recuperado": round(recuperado, 2),
        "perdida_bruta": round(perdida_bruta, 2),
        "perdida_neta": round(max(0, perdida_bruta - recuperado), 2),
        "kilos_ganaderia": round(kilos_ganaderia, 2),
        "lotes_reciclados": sum(
            1 for fila in filas if fila["tipo"] == "reciclaje"
        ),
    }


def registrar_gasto(insumo_id, cantidad, registrado_por):
    """Descuenta inventario y registra el gasto. Lanza ValueError si no es válido."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser un número mayor que cero.")

    conexion = get_db()
    try:
        fila = conexion.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()
        if fila is None:
            raise ValueError("El insumo seleccionado no existe.")

        if date.fromisoformat(fila["caducidad"]) < date.today():
            raise ValueError(
                f"«{fila['nombre']}» ya caducó el "
                f"{date.fromisoformat(fila['caducidad']).strftime('%d/%m/%Y')}. "
                "No se descontó nada: no lo uses y avísale al encargado."
            )

        if cantidad > fila["cantidad"]:
            raise ValueError(
                f"No puedes gastar {cantidad:g} {fila['unidad']} de «{fila['nombre']}». "
                f"Solo hay {fila['cantidad']:g} {fila['unidad']} en inventario."
            )

        conexion.execute(
            "UPDATE insumos SET cantidad = cantidad - ? WHERE id = ?",
            (cantidad, insumo_id),
        )
        gasto = conexion.execute(
            "INSERT INTO gastos (insumo_id, cantidad, fecha, registrado_por) VALUES (?, ?, ?, ?)",
            (insumo_id, cantidad, date.today().isoformat(), registrado_por),
        )
        conexion.execute(
            """
            INSERT INTO salidas
                (insumo_id, producto, destino, cantidad, unidad, monto_recuperado,
                 costo_unitario, fecha, registrado_por, gasto_id)
            VALUES (?, ?, 'consumo', ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                insumo_id,
                fila["nombre"],
                cantidad,
                fila["unidad"],
                fila["costo_unitario"],
                date.today().isoformat(),
                registrado_por,
                gasto.lastrowid,
            ),
        )
        conexion.commit()
    finally:
        conexion.close()


def resumen_financiero():
    """Calcula el resumen financiero con ventas, consumo y recuperación."""
    conexion = get_db()
    try:
        inversion = conexion.execute(
            "SELECT COALESCE(SUM(dinero_invertido), 0) FROM insumos"
        ).fetchone()[0]
        ingresos = conexion.execute(
            "SELECT COALESCE(SUM(precio * unidades), 0) FROM ventas"
        ).fetchone()[0]
        consumo = conexion.execute(
            """
            SELECT COALESCE(SUM(g.cantidad * i.costo_unitario), 0)
            FROM gastos g JOIN insumos i ON i.id = g.insumo_id
            """
        ).fetchone()[0]
    finally:
        conexion.close()

    recuperacion = resumen_recuperacion()
    return {
        "inversion": round(inversion, 2),
        "ingresos": round(ingresos, 2),
        "consumo": round(consumo, 2),
        "perdidas": recuperacion["perdida_neta"],
        "recuperado": recuperacion["recuperado"],
        "ganancia": round(
            ingresos + recuperacion["recuperado"] - consumo - recuperacion["perdida_bruta"],
            2,
        ),
    }
