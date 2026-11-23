const API_BASE = "http://localhost:3000/api";
let usuarioActual = null;

const vistaLogin = document.getElementById("vista-login");
const vistaDueno = document.getElementById("vista-dueno");
const formLogin = document.getElementById("form-login-dueno");
const mensajeLogin = document.getElementById("mensaje-login");
const infoSesion = document.getElementById("info-sesion");
const btnCerrarSesion = document.getElementById("btn-cerrar-sesion");
const btnCargarResumen = document.getElementById("btn-cargar-resumen");
const fechaInicioInput = document.getElementById("fecha-inicio");
const fechaFinInput = document.getElementById("fecha-fin");
const formCambiarArea = document.getElementById("form-cambiar-area");
const mensajeArea = document.getElementById("mensaje-area");

function establecerFechasPorDefecto() {
  const hoy = new Date();
  const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const finMes = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);

  const fmt = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };

  if (!fechaInicioInput.value) fechaInicioInput.value = fmt(inicioMes);
  if (!fechaFinInput.value) fechaFinInput.value = fmt(finMes);
}

function aArreglo(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") return [data];
  return [];
}

function formatoMoneda(valor) {
  const num = Number(valor ?? 0);
  return Number.isFinite(num)
    ? num.toLocaleString("es-MX", { style: "currency", currency: "MXN" })
    : "$0.00";
}

function primerValor(fila, llaves, fallback = "-") {
  for (const k of llaves) {
    if (fila && fila[k] !== undefined && fila[k] !== null) return fila[k];
  }
  return fallback;
}

async function pedirApi(ruta, opciones = {}) {
  const resp = await fetch(`${API_BASE}${ruta}`, {
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

formLogin.addEventListener("submit", async (e) => {
  e.preventDefault();
  mensajeLogin.textContent = "Validando...";

  const nombreUsuario = document.getElementById("login-usuario").value.trim();
  const contrasena = document.getElementById("login-contrasena").value;
  const nombreRol = document.getElementById("login-rol")?.value || "Dueño";

  try {
    const json = await pedirApi("/login", {
      method: "POST",
      body: JSON.stringify({
        nombreUsuario,
        contrasena,
        nombreRol,
      }),
    });

    const filas = aArreglo(json.data);
    if (!filas.length) {
      mensajeLogin.textContent = `Credenciales o rol de ${nombreRol} inválidos.`;
      return;
    }

    usuarioActual = {
      ...filas[0],
      NombreRol: filas[0].NombreRol || nombreRol,
    };
    mensajeLogin.textContent = "";
    vistaLogin.classList.add("oculto");

    if (usuarioActual.NombreRol === "Encargado" && typeof window.abrirPanelEncargado === "function") {
      await window.abrirPanelEncargado(usuarioActual);
      return;
    }

    if (usuarioActual.NombreRol === "Empleado" && typeof window.abrirPanelEmpleado === "function") {
      await window.abrirPanelEmpleado(usuarioActual);
      return;
    }

    vistaDueno.classList.remove("oculto");
    infoSesion.textContent = `Usuario: ${usuarioActual.NombreUsuario} | Rol: ${usuarioActual.NombreRol} (ID: ${usuarioActual.IdUsuario})`;

    establecerFechasPorDefecto();
    await cargarPanelDueno();
  } catch (err) {
    mensajeLogin.textContent = `Error: ${err.message}`;
  }
});

btnCerrarSesion.addEventListener("click", () => {
  usuarioActual = null;
  document.getElementById("login-contrasena").value = "";
  vistaDueno.classList.add("oculto");
  vistaLogin.classList.remove("oculto");
});

btnCargarResumen.addEventListener("click", cargarPanelDueno);

async function cargarPanelDueno() {
  establecerFechasPorDefecto();
  const params = new URLSearchParams({
    fechaInicio: fechaInicioInput.value,
    fechaFin: fechaFinInput.value,
  });

  try {
    const [resumenResp, ventasResp, stockResp, agotarResp, vencerResp] = await Promise.all([
      pedirApi(`/resumen-dueno?${params.toString()}`),
      pedirApi("/ventas-platillo"),
      pedirApi("/stock-insumos"),
      pedirApi("/insumos-por-agotarse"),
      pedirApi("/insumos-proximos-a-vencer"),
    ]);

    const resumenFila = aArreglo(resumenResp.data)[0] || {};
    document.getElementById("kpi-inversion").textContent = formatoMoneda(resumenFila.InversionInsumos);
    document.getElementById("kpi-ventas").textContent = formatoMoneda(resumenFila.VentasTotales);
    document.getElementById("kpi-ganancias").textContent = formatoMoneda(resumenFila.Ganancias);
    document.getElementById("kpi-mermas").textContent = formatoMoneda(resumenFila.PerdidaPorMermas);

    pintarVentasPlatillo(aArreglo(ventasResp.data));
    pintarStockInsumos(aArreglo(stockResp.data));
    pintarPorAgotarse(aArreglo(agotarResp.data));
    pintarProximosVencer(aArreglo(vencerResp.data));
  } catch (err) {
    console.error("Error cargando panel del dueño:", err);
  }
}

function pintarVentasPlatillo(filas) {
  const tbody = document.getElementById("tabla-ventas-platillo");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3">Sin datos</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const nombre = primerValor(f, ["Nombre", "NombrePlatillo", "Platillo"]);
      const unidades = primerValor(f, ["UnidadesVendidas", "CantidadVendida", "Cantidad"], 0);
      const margen = primerValor(f, ["MargenUnitario", "TotalVentas", "Total"], 0);
      return `<tr><td>${nombre}</td><td>${unidades}</td><td>${formatoMoneda(margen)}</td></tr>`;
    })
    .join("");
}

function pintarStockInsumos(filas) {
  const tbody = document.getElementById("tabla-stock-insumos");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="2">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = primerValor(f, ["producto", "Producto", "NombreInsumo"]);
      const stock = primerValor(f, ["StockDisponible", "CantidadRestante", "Cantidad"], 0);
      const unidad = primerValor(f, ["Unidad"], "");
      return `<tr><td>${prod}</td><td>${stock} ${unidad}</td></tr>`;
    })
    .join("");
}

function pintarPorAgotarse(filas) {
  const tbody = document.getElementById("tabla-por-agotarse");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="2">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = primerValor(f, ["Producto", "producto", "NombreInsumo"]);
      const stock = primerValor(f, ["StockDisponible", "CantidadRestante"], 0);
      const unidad = primerValor(f, ["Unidad"], "");
      const msg = primerValor(f, ["Mensaje"], "");
      const detalle = msg ? `${stock} ${unidad} (${msg})` : `${stock} ${unidad}`;
      return `<tr><td>${prod}</td><td>${detalle}</td></tr>`;
    })
    .join("");
}

function pintarProximosVencer(filas) {
  const tbody = document.getElementById("tabla-proximos-vencer");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="2">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = primerValor(f, ["Producto", "producto", "NombreInsumo"]);
      let fecha = primerValor(f, ["FechaCaducidad"], "");
      if (typeof fecha === "string" && fecha.includes("T")) {
        fecha = fecha.split("T")[0];
      }
      const cant = primerValor(f, ["Cantidad"], "");
      const unidad = primerValor(f, ["Unidad"], "");
      const dias = primerValor(f, ["DiasRestantes"], "");
      const extra = [cant && `${cant} ${unidad}`, dias !== "" && `${dias} días`].filter(Boolean).join(" · ");
      return `<tr><td>${prod}</td><td>${fecha}${extra ? ` — ${extra}` : ""}</td></tr>`;
    })
    .join("");
}

formCambiarArea.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!usuarioActual) return;

  const rolDestino = document.getElementById("rol-destino").value;
  const contrasena = document.getElementById("area-contrasena").value;
  mensajeArea.textContent = "Verificando...";

  try {
    const json = await pedirApi("/cambiar-area-dueno", {
      method: "POST",
      body: JSON.stringify({
        idUsuario: usuarioActual.IdUsuario,
        contrasena,
        rolDestino,
      }),
    });

    const fila = aArreglo(json.data)[0] || {};
    if (Number(fila.Acceso) === 1) {
      const destinoFinal = fila.RolDestino || rolDestino;
      document.getElementById("area-contrasena").value = "";
      mensajeArea.textContent = `Acceso concedido al área: ${destinoFinal}`;

      if (destinoFinal === "Encargado" && typeof window.abrirPanelEncargado === "function") {
        await window.abrirPanelEncargado({ ...usuarioActual, NombreRol: "Encargado" });
      } else if (destinoFinal === "Empleado" && typeof window.abrirPanelEmpleado === "function") {
        await window.abrirPanelEmpleado({ ...usuarioActual, NombreRol: "Empleado" });
      }
    } else {
      mensajeArea.textContent = "No se pudo cambiar de área (revisa contraseña o rol).";
    }
  } catch (err) {
    mensajeArea.textContent = `Error: ${err.message}`;
  }
});