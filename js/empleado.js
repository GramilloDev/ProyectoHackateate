const EMP_API = typeof API_BASE !== "undefined" ? API_BASE : "http://localhost:3000/api";
let empleadoActual = null;

const vistaEmpleado = document.getElementById("vista-empleado");
const infoSesionEmpleado = document.getElementById("info-sesion-empleado");
const btnRefrescarEmpleado = document.getElementById("btn-refrescar-empleado");
const btnCerrarSesionEmpleado = document.getElementById("btn-cerrar-sesion-empleado");
const formVenta = document.getElementById("form-registrar-venta");
const mensajeVenta = document.getElementById("mensaje-venta");
const formMerma = document.getElementById("form-registrar-merma");
const mensajeMerma = document.getElementById("mensaje-merma");
const selectVentaPlatillo = document.getElementById("venta-platillo");
const inputMermaIdEntrada = document.getElementById("merma-id-entrada");
const inputVentaFecha = document.getElementById("venta-fecha");

function empArreglo(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") return [data];
  return [];
}

function empValor(fila, llaves, fallback = "-") {
  for (const k of llaves) {
    if (fila && fila[k] !== undefined && fila[k] !== null) return fila[k];
  }
  return fallback;
}

function empMoneda(valor) {
  const num = Number(valor ?? 0);
  return Number.isFinite(num)
    ? num.toLocaleString("es-MX", { style: "currency", currency: "MXN" })
    : "$0.00";
}

function establecerFechaHoyEmpleado() {
  if (!inputVentaFecha) return;
  const hoy = new Date();
  const y = hoy.getFullYear();
  const m = String(hoy.getMonth() + 1).padStart(2, "0");
  const d = String(hoy.getDate()).padStart(2, "0");
  if (!inputVentaFecha.value) inputVentaFecha.value = `${y}-${m}-${d}`;
}

async function empPedirApi(ruta, opciones = {}) {
  const resp = await fetch(`${EMP_API}${ruta}`, {
    ...opciones,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...(opciones.headers || {}),
    },
  });
  const json = await resp.json();
  if (!resp.ok || json.ok === false) {
    throw new Error(json.error || `Error HTTP ${resp.status}`);
  }
  return json;
}

window.abrirPanelEmpleado = async function (usuario) {
  empleadoActual = usuario;
  document.getElementById("vista-login")?.classList.add("oculto");
  document.getElementById("vista-dueno")?.classList.add("oculto");
  document.getElementById("vista-encargado")?.classList.add("oculto");
  vistaEmpleado.classList.remove("oculto");
  infoSesionEmpleado.textContent = `Usuario: ${usuario.NombreUsuario} | Rol: ${usuario.NombreRol} (ID: ${usuario.IdUsuario})`;
  establecerFechaHoyEmpleado();
  await cargarPanelEmpleado();
};

btnCerrarSesionEmpleado?.addEventListener("click", () => {
  empleadoActual = null;
  if (mensajeVenta) mensajeVenta.textContent = "";
  if (mensajeMerma) mensajeMerma.textContent = "";
  vistaEmpleado.classList.add("oculto");
  document.getElementById("vista-login")?.classList.remove("oculto");
});

btnRefrescarEmpleado?.addEventListener("click", cargarPanelEmpleado);

async function cargarPanelEmpleado() {
  try {
    const [ventasResp, stockResp] = await Promise.all([
      empPedirApi("/ventas-platillo"),
      empPedirApi("/stock-insumos"),
    ]);

    const ventasFilas = empArreglo(ventasResp.data);
    const stockFilas = empArreglo(stockResp.data);

    poblarSelectPlatillos(ventasFilas);
    pintarEmpVentas(ventasFilas);
    pintarEmpStock(stockFilas);
  } catch (err) {
    console.error("Error cargando panel del empleado:", err);
  }
}

function poblarSelectPlatillos(filas) {
  const anterior = selectVentaPlatillo.value;
  selectVentaPlatillo.innerHTML = filas
    .map((f, idx) => {
      const id = empValor(f, ["IdPlatillo", "idPlatillo", "Id"], idx + 1);
      const nombre = empValor(f, ["Nombre", "NombrePlatillo", "Platillo"], "Platillo");
      return `<option value="${id}" data-nombre="${String(nombre).replace(/"/g, "&quot;")}">${id} — ${nombre}</option>`;
    })
    .join("");
  if (anterior) selectVentaPlatillo.value = anterior;
}

function pintarEmpVentas(filas) {
  const tbody = document.getElementById("emp-tabla-ventas");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3">Sin datos</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const nombre = empValor(f, ["Nombre", "NombrePlatillo", "Platillo"]);
      const unidades = empValor(f, ["UnidadesVendidas", "CantidadVendida", "Cantidad"], 0);
      const margen = empValor(f, ["MargenUnitario", "TotalVentas", "Total"], 0);
      return `<tr><td>${nombre}</td><td>${unidades}</td><td>${empMoneda(margen)}</td></tr>`;
    })
    .join("");
}

function pintarEmpStock(filas) {
  const tbody = document.getElementById("emp-tabla-stock");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const id = empValor(f, ["IdInsumo", "idInsumo"]);
      const prod = empValor(f, ["producto", "Producto", "NombreInsumo"]);
      const disp = empValor(f, ["StockDisponible", "CantidadRestante"], 0);
      const unidad = empValor(f, ["Unidad"], "");
      return `<tr><td>${id}</td><td>${prod}</td><td>${disp} ${unidad}</td></tr>`;
    })
    .join("");
}

formVenta?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!empleadoActual) return;
  mensajeVenta.textContent = "Registrando venta...";

  const opcionSel = selectVentaPlatillo.options[selectVentaPlatillo.selectedIndex];
  const nombrePlatillo = opcionSel?.dataset?.nombre || "";

  const payload = {
    idUsuario: empleadoActual.IdUsuario,
    idPlatillo: Number(selectVentaPlatillo.value),
    nombrePlatillo,
    cantidad: Number(document.getElementById("venta-cantidad").value),
    fecha: document.getElementById("venta-fecha").value || null,
  };

  try {
    await empPedirApi("/ventas", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    mensajeVenta.textContent = "Venta registrada correctamente.";
    document.getElementById("venta-cantidad").value = "1";
    await cargarPanelEmpleado();
  } catch (err) {
    mensajeVenta.textContent = `Error: ${err.message}`;
  }
});

formMerma?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!empleadoActual) return;
  mensajeMerma.textContent = "Registrando merma...";

  const payload = {
    idUsuario: empleadoActual.IdUsuario,
    idEntrada: Number(inputMermaIdEntrada.value),
    cantidad: Number(document.getElementById("merma-cantidad").value),
    motivo: document.getElementById("merma-motivo").value,
  };

  try {
    await empPedirApi("/mermas", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    mensajeMerma.textContent = "Merma registrada correctamente.";
    document.getElementById("merma-cantidad").value = "";
    const selectMotivo = document.getElementById("merma-motivo");
    if (selectMotivo) selectMotivo.value = "Vencido";
    await cargarPanelEmpleado();
  } catch (err) {
    mensajeMerma.textContent = `Error: ${err.message}`;
  }
});