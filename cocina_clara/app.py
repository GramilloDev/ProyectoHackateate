"""Eco Menu: app web local para gestionar insumos y reducir desperdicio."""

import math
import os
import re
from datetime import date
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

import database
import gemini_service

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "eco-menu-demo-local")

USUARIOS = {
    "dueño": {"clave": "dueno123", "rol": "dueno", "nombre": "Dueño"},
    "encargado": {"clave": "encargado123", "rol": "encargado", "nombre": "Encargado"},
    "empleado": {"clave": "empleado123", "rol": "empleado", "nombre": "Empleado"},
}

PANELES = {
    "dueno": "panel_dueno",
    "encargado": "inventario",
    "empleado": "avisos",
}

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# (clave, título visible, patrón para reconocer el título en la respuesta)
SECCIONES_GEMINI = [
    ("poca_salida", "Platillos con poca salida", r"platillos?\s+con\s+poca\s+salida"),
    (
        "usar_primero",
        "Ingredientes que conviene usar primero",
        r"ingredientes?\s+que\s+conviene\s+usar\s+primero",
    ),
    (
        "temporada",
        "Sugerencias de platillos de temporada",
        r"sugerencias?\s+de\s+platillos?\s+de\s+temporada",
    ),
    (
        "promociones",
        "Promociones para dar salida a tiempo",
        r"promociones?\s+para\s+dar\s+salida\s+a\s+tiempo",
    ),
    (
        "preparacion",
        "Qué preparar hoy o esta semana",
        r"qu[eé]\s+preparar\s+hoy\s+o\s+esta\s+semana",
    ),
]

database.init_db()


@app.template_filter("fecha")
def formato_fecha(valor):
    if not valor:
        return "—"
    return date.fromisoformat(str(valor)).strftime("%d/%m/%Y")


@app.template_filter("dinero")
def formato_dinero(valor):
    return f"${valor:,.2f}"


@app.template_filter("cantidad")
def formato_cantidad(valor):
    if valor is None:
        return "0"
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}".rstrip("0").rstrip(".")


@app.template_filter("destino")
def formato_destino(valor):
    return database.DESTINO_LABELS.get(valor, str(valor).capitalize())


def rol_requerido(*roles):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if "usuario" not in session:
                flash("Inicia sesión para continuar.", "warning")
                return redirect(url_for("login"))
            if session.get("rol") not in roles:
                flash("Tu rol no tiene acceso a esa sección.", "error")
                return redirect(url_for("inicio"))
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def _filas_inventario():
    filas = []
    for fila in database.listar_insumos():
        datos = dict(fila)
        datos["dias"] = database.dias_para_caducar(fila["caducidad"])
        datos["estado"], datos["clase"] = database.estado_insumo(
            fila["caducidad"], fila["cantidad"]
        )
        filas.append(datos)
    return filas


def _filas_avisos():
    return [fila for fila in _filas_inventario() if fila["dias"] <= 3 and fila["cantidad"] > 0]


def _agrupar_por_categoria(filas):
    return [
        {
            "nombre": categoria,
            "insumos": [fila for fila in filas if fila["categoria"] == categoria],
        }
        for categoria in database.CATEGORIAS
        if any(fila["categoria"] == categoria for fila in filas)
    ]


def _parsear_cantidad(texto):
    limpio = (texto or "").strip().replace(",", ".")
    if not limpio:
        raise ValueError("Escribe una cantidad.")
    try:
        valor = float(limpio)
    except ValueError:
        raise ValueError("La cantidad debe ser un número mayor que cero (por ejemplo 2.5).")
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError("La cantidad debe ser un número mayor que cero (por ejemplo 2.5).")
    return valor


def _parsear_monto(texto):
    limpio = (texto or "").strip().replace(",", ".")
    try:
        valor = float(limpio)
    except ValueError:
        raise ValueError("Escribe un monto válido, igual o mayor que cero.")
    if not math.isfinite(valor) or valor < 0:
        raise ValueError("El monto debe ser igual o mayor que cero.")
    return valor


def _temporada(mes):
    if mes in (12, 1, 2):
        return "invierno"
    if mes in (3, 4, 5):
        return "primavera"
    if mes in (6, 7, 8):
        return "verano"
    return "otoño"


def _texto_dias(dias):
    if dias < 0:
        return f"caducó hace {abs(dias)} día(s)"
    if dias == 0:
        return "caduca hoy"
    return f"caduca en {dias} día(s)"


def construir_prompt():
    """Arma el texto con inventario, caducidades, ventas y época del año."""
    hoy = date.today()
    filas = _filas_inventario()
    ventas = database.listar_ventas()

    lineas_inventario = [
        f"- {fila['nombre']} ({fila['categoria']}): {fila['cantidad']:g} {fila['unidad']} | "
        f"caducidad {fila['caducidad']} ({_texto_dias(fila['dias'])})"
        for fila in filas
    ]
    lineas_ventas = [
        f"- {venta['platillo']}: {venta['unidades']} unidades vendidas "
        f"(precio ${venta['precio']:.2f})"
        for venta in ventas
    ]

    return f"""Eres el asesor de "Eco Menu", un restaurante familiar. Analiza solo los datos de abajo.

FECHA DE HOY: {hoy.strftime("%d/%m/%Y")} ({MESES[hoy.month - 1]}, {_temporada(hoy.month)}).

INVENTARIO ACTUAL (producto | existencia | caducidad):
{chr(10).join(lineas_inventario) if lineas_inventario else "- Sin insumos registrados."}

VENTAS POR PLATILLO (últimos días):
{chr(10).join(lineas_ventas) if lineas_ventas else "- Sin ventas registradas."}

Da exactamente CINCO recomendaciones:
1. Platillos con poca salida.
2. Ingredientes que conviene usar primero por caducidad.
3. Sugerencias de platillos de temporada para esta época del año.
4. Promociones para dar salida a tiempo: descuento, combo o platillo del día con productos que aún no hayan caducado.
5. Qué preparar hoy o esta semana, usando primero los ingredientes que aún estén en buen estado.

Reglas:
- Responde en español, breve y claro (máximo 240 palabras en total, de 1 a 3 viñetas por sección).
- No inventes platillos, ingredientes, precios, cantidades ni fechas que no aparezcan arriba.
- Si un insumo ya caducó, no lo recomiendes para cocinar: indícalo como descarte.
- Usa como títulos exactos: "PLATILLOS CON POCA SALIDA", "INGREDIENTES QUE CONVIENE USAR PRIMERO", "SUGERENCIAS DE PLATILLOS DE TEMPORADA", "PROMOCIONES PARA DAR SALIDA A TIEMPO" y "QUÉ PREPARAR HOY O ESTA SEMANA".
"""


def _titulo_de_linea(linea):
    limpia = re.sub(r"^[\s>*#_`\d.)\-]+", "", linea)
    limpia = re.sub(r"[\s*#_`:\-]+$", "", limpia).strip()
    for clave, titulo, patron in SECCIONES_GEMINI:
        if re.fullmatch(patron, limpia, re.IGNORECASE):
            return clave, titulo
    return None


def separar_recomendaciones(texto):
    """Divide la respuesta en las tres secciones pedidas (o muestra el texto completo)."""
    secciones = []
    actual = None

    for linea in texto.splitlines():
        detectado = _titulo_de_linea(linea)
        if detectado:
            actual = {"clave": detectado[0], "titulo": detectado[1], "texto": []}
            secciones.append(actual)
        elif actual is not None:
            actual["texto"].append(linea)

    if len(secciones) < len(SECCIONES_GEMINI):
        return [{"clave": "general", "titulo": "Recomendaciones de Gemini", "texto": texto.strip()}]

    for seccion in secciones:
        seccion["texto"] = "\n".join(seccion["texto"]).strip() or "Sin contenido."

    return secciones


@app.route("/")
def inicio():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return redirect(url_for(PANELES[session["rol"]]))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().casefold()
        clave = request.form.get("clave", "")
        datos = USUARIOS.get(usuario)
        if datos and datos["clave"] == clave:
            session.clear()
            session["usuario"] = usuario
            session["rol"] = datos["rol"]
            session["nombre"] = datos["nombre"]
            flash(f"Bienvenido, {datos['nombre']}.", "success")
            return redirect(url_for(PANELES[datos["rol"]]))
        flash("Usuario o contraseña incorrectos. Revisa los datos de prueba.", "error")

    return render_template("login.html", usuarios=USUARIOS)


@app.route("/logout")
def logout():
    session.clear()
    flash("Cerraste sesión.", "info")
    return redirect(url_for("login"))


@app.route("/dueno")
@rol_requerido("dueno")
def panel_dueno():
    insumos = _filas_inventario()
    return render_template(
        "dueno.html",
        resumen=database.resumen_financiero(),
        avisos=_filas_avisos(),
        categorias=_agrupar_por_categoria(insumos),
        recuperacion=database.resumen_recuperacion(),
        salidas=database.listar_salidas(),
        reportes=database.listar_reportes_dueno(),
    )


@app.route("/inventario")
@rol_requerido("encargado")
def inventario():
    insumos = _filas_inventario()
    return render_template(
        "inventario.html",
        insumos=insumos,
        categorias=_agrupar_por_categoria(insumos),
    )


@app.route("/insumos/nuevo", methods=["GET", "POST"])
@rol_requerido("encargado")
def nuevo_insumo():
    formulario = {
        "nombre": "",
        "cantidad": "",
        "unidad": "kg",
        "caducidad": "",
        "categoria": "Otros",
        "dinero_invertido": "0",
        "fecha_compra": date.today().isoformat(),
        "reabasto_fecha": "",
    }

    if request.method == "POST":
        formulario = {
            "nombre": request.form.get("nombre", "").strip(),
            "cantidad": request.form.get("cantidad", "").strip(),
            "unidad": request.form.get("unidad", "kg"),
            "caducidad": request.form.get("caducidad", "").strip(),
            "categoria": request.form.get("categoria", ""),
            "dinero_invertido": request.form.get("dinero_invertido", "").strip(),
            "fecha_compra": request.form.get("fecha_compra", "").strip(),
            "reabasto_fecha": request.form.get("reabasto_fecha", "").strip(),
        }
        errores = []

        if not formulario["nombre"]:
            errores.append("Escribe el nombre del producto.")
        elif len(formulario["nombre"]) > 80:
            errores.append("El nombre del producto es demasiado largo.")

        cantidad = None
        try:
            cantidad = _parsear_cantidad(formulario["cantidad"])
        except ValueError as error:
            errores.append(str(error))

        if formulario["unidad"] not in database.UNIDADES:
            errores.append("Selecciona una unidad válida.")
        if formulario["categoria"] not in database.CATEGORIAS:
            errores.append("Selecciona una categoría válida.")

        fecha = None
        if not formulario["caducidad"]:
            errores.append("Escribe la fecha de caducidad.")
        else:
            try:
                fecha = date.fromisoformat(formulario["caducidad"])
            except ValueError:
                errores.append("La fecha de caducidad no es válida.")
            else:
                if fecha < date.today():
                    errores.append(
                        "Esa fecha ya pasó. No registres un insumo caducado: "
                        "sepáralo y avísale al encargado."
                    )

        fecha_compra = None
        try:
            fecha_compra = date.fromisoformat(formulario["fecha_compra"])
            if fecha_compra > date.today():
                errores.append("La fecha de compra no puede estar en el futuro.")
        except ValueError:
            errores.append("La fecha de compra no es válida.")

        fecha_reabasto = None
        if formulario["reabasto_fecha"]:
            try:
                fecha_reabasto = date.fromisoformat(formulario["reabasto_fecha"])
                if fecha_compra and fecha_reabasto < fecha_compra:
                    errores.append(
                        "La fecha de reabastecimiento no puede ser anterior a la compra."
                    )
            except ValueError:
                errores.append("La fecha de reabastecimiento no es válida.")

        dinero_invertido = None
        try:
            dinero_invertido = _parsear_monto(formulario["dinero_invertido"])
        except ValueError as error:
            errores.append(str(error))

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template(
                "insumo_nuevo.html",
                form=formulario,
                unidades=database.UNIDADES,
                categorias=database.CATEGORIAS,
                hoy=date.today().isoformat(),
            )

        database.agregar_insumo(
            formulario["nombre"],
            cantidad,
            formulario["unidad"],
            fecha.isoformat(),
            formulario["categoria"],
            dinero_invertido,
            fecha_compra.isoformat(),
            fecha_reabasto.isoformat() if fecha_reabasto else None,
        )
        flash(
            f"Insumo «{formulario['nombre']}» registrado: "
            f"{cantidad:g} {formulario['unidad']}, "
            f"caduca el {fecha.strftime('%d/%m/%Y')}.",
            "success",
        )
        if (fecha - date.today()).days <= 3:
            flash("Ojo: caduca en 3 días o menos. Entra a Avisos para no perderlo.", "warning")
        return redirect(url_for("inventario"))

    return render_template(
        "insumo_nuevo.html",
        form=formulario,
        unidades=database.UNIDADES,
        categorias=database.CATEGORIAS,
        hoy=date.today().isoformat(),
    )


@app.route("/avisos")
@rol_requerido("encargado", "empleado")
def avisos():
    avisos = _filas_avisos()
    return render_template(
        "avisos.html",
        avisos=avisos,
        categorias=_agrupar_por_categoria(avisos),
    )


@app.route("/gastos/nuevo", methods=["GET", "POST"])
@rol_requerido("empleado")
def nuevo_gasto():
    formulario = {"insumo_id": "", "cantidad": ""}
    insumos = _filas_inventario()

    if request.method == "POST":
        formulario = {
            "insumo_id": request.form.get("insumo_id", ""),
            "cantidad": request.form.get("cantidad", "").strip(),
        }

        try:
            insumo_id = int(formulario["insumo_id"])
        except ValueError:
            flash("Selecciona un insumo de la lista.", "error")
            return render_template("gasto_nuevo.html", insumos=insumos, form=formulario)

        try:
            cantidad = _parsear_cantidad(formulario["cantidad"])
        except ValueError as error:
            flash(str(error), "error")
            return render_template("gasto_nuevo.html", insumos=insumos, form=formulario)

        try:
            database.registrar_gasto(insumo_id, cantidad, session["nombre"])
        except ValueError as error:
            flash(str(error), "error")
            return render_template("gasto_nuevo.html", insumos=insumos, form=formulario)

        actualizado = database.obtener_insumo(insumo_id)
        flash(
            f"Gasto registrado: {cantidad:g} {actualizado['unidad']} de "
            f"«{actualizado['nombre']}». Quedan {actualizado['cantidad']:g} "
            f"{actualizado['unidad']}.",
            "success",
        )
        return redirect(url_for("avisos"))

    return render_template("gasto_nuevo.html", insumos=insumos, form=formulario)


@app.route("/reporte")
@rol_requerido("dueno", "encargado")
def reporte():
    insumos = _filas_inventario()
    return render_template(
        "reporte.html",
        insumos=insumos,
        resumen=database.resumen_recuperacion(),
        salidas=database.listar_salidas(),
        categorias=_agrupar_por_categoria(insumos),
        texto_preparado="",
        modo_preparado="",
    )


@app.route("/reporte", methods=["POST"])
@rol_requerido("encargado")
def enviar_reporte():
    accion = request.form.get("accion", "preparar")
    texto = request.form.get("texto", "").strip()
    modo = request.form.get("modo", "")

    if accion == "enviar":
        if not texto:
            flash("Escribe o genera un resumen antes de enviarlo.", "error")
        elif len(texto) > 2000:
            flash("El resumen no puede superar 2000 caracteres.", "error")
        else:
            database.registrar_reporte_dueno(session["nombre"], texto)
            flash("El resumen fue enviado al panel del dueño.", "success")
            return redirect(url_for("reporte"))
    elif modo == "gemini":
        try:
            prompt = (
                "Redacta en español un resumen breve y claro para el dueño del restaurante, "
                "usando solo estos datos de existencias, salidas y recuperación. No inventes "
                "datos y menciona por separado las pérdidas netas y los ingresos recuperados.\n\n"
                + _texto_reporte_actual()
            )
            texto = gemini_service.analizar_con_gemini(prompt)
        except gemini_service.GeminiError as error:
            flash(str(error), "error")
    elif modo != "manual":
        flash("Elige redactar con Gemini o escribir el resumen manualmente.", "error")

    insumos = _filas_inventario()
    return render_template(
        "reporte.html",
        insumos=insumos,
        resumen=database.resumen_recuperacion(),
        salidas=database.listar_salidas(),
        categorias=_agrupar_por_categoria(insumos),
        texto_preparado=texto,
        modo_preparado=modo,
    )


def _texto_reporte_actual():
    resumen = database.resumen_recuperacion()
    inventario = "\n".join(
        f"- {fila['nombre']}: {fila['cantidad']:g} {fila['unidad']}, "
        f"categoría {fila['categoria']}, vence {fila['caducidad']}"
        for fila in _filas_inventario()
    )
    return (
        f"Inventario:\n{inventario or '- Sin insumos'}\n"
        f"Pérdida bruta: ${resumen['perdida_bruta']:.2f}\n"
        f"Recuperado por promociones, ganadería y reciclaje: ${resumen['recuperado']:.2f}\n"
        f"Pérdida neta: ${resumen['perdida_neta']:.2f}\n"
        f"Kilos enviados a ganadería: {resumen['kilos_ganaderia']:.2f}\n"
        f"Lotes de reciclaje: {resumen['lotes_reciclados']}"
    )


@app.route("/reportes/<int:reporte_id>/leer", methods=["POST"])
@rol_requerido("dueno")
def marcar_reporte_leido(reporte_id):
    if not database.marcar_reporte_leido(reporte_id):
        flash("Ese resumen ya no está disponible.", "error")
    else:
        flash("Resumen marcado como leído.", "success")
    return redirect(url_for("panel_dueno"))


@app.route("/salidas", methods=["GET", "POST"])
@rol_requerido("dueno", "encargado")
def salidas():
    formulario = {
        "insumo_id": "",
        "tipo": "perdida",
        "cantidad": "",
        "monto_recuperado": "0",
    }
    if request.method == "POST":
        formulario.update(
            insumo_id=request.form.get("insumo_id", ""),
            tipo=request.form.get("tipo", ""),
            cantidad=request.form.get("cantidad", "").strip(),
            monto_recuperado=request.form.get("monto_recuperado", "0").strip(),
        )
        try:
            if not formulario["insumo_id"]:
                raise ValueError("Selecciona un insumo de la lista.")
            insumo_id = int(formulario["insumo_id"])
            cantidad = _parsear_cantidad(formulario["cantidad"])
            monto = _parsear_monto(formulario["monto_recuperado"])
            if formulario["tipo"] == "consumo":
                if monto:
                    raise ValueError("El consumo no registra dinero recuperado.")
                database.registrar_gasto(insumo_id, cantidad, session["nombre"])
            else:
                database.registrar_salida(
                    insumo_id,
                    formulario["tipo"],
                    cantidad,
                    monto,
                    session["nombre"],
                )
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Salida del inventario registrada.", "success")
            return redirect(url_for("salidas"))

    insumos = _filas_inventario()
    return render_template(
        "salidas.html",
        insumos=insumos,
        salidas=database.listar_salidas(),
        destinos=database.DESTINO_LABELS,
        form=formulario,
    )


@app.route("/dueno/analisis", methods=["GET", "POST"])
@rol_requerido("dueno")
def analisis():
    resultado = None
    error = None

    if request.method == "POST":
        try:
            texto = gemini_service.analizar_con_gemini(construir_prompt())
            resultado = separar_recomendaciones(texto)
        except gemini_service.GeminiError as fallo:
            error = str(fallo)
        except Exception:
            app.logger.exception("Error inesperado en el análisis con Gemini")
            error = (
                "Ocurrió un problema inesperado al preparar el análisis. "
                "Intenta de nuevo en unos momentos."
            )

    hoy = date.today()
    return render_template(
        "analisis.html",
        resultado=resultado,
        error=error,
        ventas=database.listar_ventas(),
        insumos=_filas_inventario(),
        temporada_actual=f"{MESES[hoy.month - 1]} · {_temporada(hoy.month)}",
    )


@app.route("/sugerencias", methods=["GET", "POST"])
@rol_requerido("empleado")
def sugerencias():
    resultado = None
    error = None
    if request.method == "POST":
        try:
            resultado = separar_recomendaciones(
                gemini_service.analizar_con_gemini(construir_prompt())
            )
        except gemini_service.GeminiError as fallo:
            error = str(fallo)
        except Exception:
            app.logger.exception("Error inesperado en las sugerencias con Gemini")
            error = "No se pudieron cargar las sugerencias. Intenta de nuevo en unos momentos."
    return render_template("sugerencias.html", resultado=resultado, error=error)


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "5000"))
    app.run(debug=True, port=puerto)
