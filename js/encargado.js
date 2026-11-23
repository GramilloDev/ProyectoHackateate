const ENC_API = typeof API_BASE !== "undefined" ? API_BASE : "http://localhost:3000/api";
let encargadoActual = null;

const vistaEncargado = document.getElementById("vista-encargado");
const infoSesionEncargado = document.getElementById("info-sesion-encargado");
const btnRefrescarEncargado = document.getElementById("btn-refrescar-encargado");
const btnCerrarSesionEncargado = document.getElementById("btn-cerrar-sesion-encargado");
const formEntrada = document.getElementById("form-registrar-entrada");
const mensajeEntrada = document.getElementById("mensaje-entrada");
const formConsumo = document.getElementById("form-registrar-consumo");
const mensajeConsumo = document.getElementById("mensaje-consumo");
const selectConsumoInsumo = document.getElementById("consumo-insumo");

function encArreglo(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") return [data];
  return [];
}

function encValor(fila, llaves, fallback = "-") {
  for (const k of llaves) {
    if (fila && fila[k] !== undefined && fila[k] !== null) return fila[k];
  }
  return fallback;
}

async function encPedirApi(ruta, opciones = {}) {
  const resp = await fetch(`${ENC_API}${ruta}`, {
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

window.abrirPanelEncargado = async function (usuario) {
  encargadoActual = usuario;
  document.getElementById("vista-login")?.classList.add("oculto");
  document.getElementById("vista-dueno")?.classList.add("oculto");
  vistaEncargado.classList.remove("oculto");
  infoSesionEncargado.textContent = `Usuario: ${usuario.NombreUsuario} | Rol: ${usuario.NombreRol} (ID: ${usuario.IdUsuario})`;
  await cargarPanelEncargado();
};

btnCerrarSesionEncargado?.addEventListener("click", () => {
  encargadoActual = null;
  vistaEncargado.classList.add("oculto");
  document.getElementById("vista-login")?.classList.remove("oculto");
});

btnRefrescarEncargado?.addEventListener("click", cargarPanelEncargado);

async function cargarPanelEncargado() {
  try {
    const [stockResp, invResp, agotarResp, vencerResp] = await Promise.all([
      encPedirApi("/stock-insumos"),
      encPedirApi("/inventario"),
      encPedirApi("/insumos-por-agotarse"),
      encPedirApi("/insumos-proximos-a-vencer"),
    ]);

    const stockFilas = encArreglo(stockResp.data);
    poblarSelectInsumos(stockFilas);
    pintarEncStock(stockFilas);
    pintarEncInventario(encArreglo(invResp.data));
    pintarEncAgotar(encArreglo(agotarResp.data));
    pintarEncVencer(encArreglo(vencerResp.data));
  } catch (err) {
    console.error("Error cargando panel del encargado:", err);
  }
}

function poblarSelectInsumos(filas) {
  const valorAnterior = selectConsumoInsumo.value;
  selectConsumoInsumo.innerHTML = filas
    .map((f) => {
      const id = encValor(f, ["IdInsumo", "idInsumo"], "");
      const nombre = encValor(f, ["producto", "Producto", "NombreInsumo"], "Insumo");
      const unidad = encValor(f, ["Unidad"], "");
      return `<option value="${id}">${id} — ${nombre} (${unidad})</option>`;
    })
    .join("");
  if (valorAnterior) selectConsumoInsumo.value = valorAnterior;
}

function pintarEncStock(filas) {
  const tbody = document.getElementById("enc-tabla-stock");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const id = encValor(f, ["IdInsumo", "idInsumo"]);
      const prod = encValor(f, ["producto", "Producto", "NombreInsumo"]);
      const disp = encValor(f, ["StockDisponible", "CantidadRestante"], 0);
      const unidad = encValor(f, ["Unidad"], "");
      return `<tr><td>${id}</td><td>${prod}</td><td>${disp} ${unidad}</td></tr>`;
    })
    .join("");
}

function pintarEncInventario(filas) {
  const tbody = document.getElementById("enc-tabla-inventario");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = encValor(f, ["Producto", "producto", "NombreProducto", "NombreInsumo"]);
      const cant = encValor(f, ["CantidadRestante", "Cantidad", "StockDisponible"], 0);
      const unidad = encValor(f, ["Unidad"], "");
      let cad = encValor(f, ["FechaCaducidad"], "");
      if (typeof cad === "string" && cad.includes("T")) cad = cad.split("T")[0];
      return `<tr><td>${prod}</td><td>${cant} ${unidad}</td><td>${cad}</td></tr>`;
    })
    .join("");
}

function pintarEncAgotar(filas) {
  const tbody = document.getElementById("enc-tabla-agotar");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="2">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = encValor(f, ["Producto", "producto", "NombreInsumo"]);
      const msg = encValor(f, ["Mensaje"], "");
      const disp = encValor(f, ["StockDisponible", "CantidadRestante"], 0);
      const unidad = encValor(f, ["Unidad"], "");
      return `<tr><td>${prod}</td><td>${msg || `${disp} ${unidad}`}</td></tr>`;
    })
    .join("");
}

function pintarEncVencer(filas) {
  const tbody = document.getElementById("enc-tabla-vencer");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="2">Sin registros</td></tr>`;
    return;
  }
  tbody.innerHTML = filas
    .map((f) => {
      const prod = encValor(f, ["Producto", "producto", "NombreInsumo"]);
      let fecha = encValor(f, ["FechaCaducidad"], "");
      if (typeof fecha === "string" && fecha.includes("T")) fecha = fecha.split("T")[0];
      const dias = encValor(f, ["DiasRestantes"], "");
      return `<tr><td>${prod}</td><td>${fecha}${dias !== "" ? ` (${dias} d)` : ""}</td></tr>`;
    })
    .join("");
}

formEntrada?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!encargadoActual) return;
  mensajeEntrada.textContent = "Guardando entrada...";

  const payload = {
    idUsuario: encargadoActual.IdUsuario,
    nombreProducto: document.getElementById("entrada-producto").value.trim(),
    idUnidad: Number(document.getElementById("entrada-unidad").value),
    cantidad: Number(document.getElementById("entrada-cantidad").value),
    fechaCaducidad: document.getElementById("entrada-caducidad").value || null,
    costoUnitario: Number(document.getElementById("entrada-costo").value || 0),
  };

  try {
    await encPedirApi("/entradas", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    mensajeEntrada.textContent = "Entrada registrada correctamente.";
    formEntrada.reset();
    document.getElementById("entrada-unidad").value = "1";
    document.getElementById("entrada-costo").value = "0";
    await cargarPanelEncargado();
  } catch (err) {
    mensajeEntrada.textContent = `Error: ${err.message}`;
  }
});

formConsumo?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!encargadoActual) return;
  mensajeConsumo.textContent = "Registrando consumo...";

  const payload = {
    idUsuario: encargadoActual.IdUsuario,
    idInsumo: Number(selectConsumoInsumo.value),
    cantidad: Number(document.getElementById("consumo-cantidad").value),
    idUnidad: Number(document.getElementById("consumo-unidad").value),
  };

  try {
    await encPedirApi("/consumos", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    mensajeConsumo.textContent = "Consumo registrado correctamente.";
    document.getElementById("consumo-cantidad").value = "";
    await cargarPanelEncargado();
  } catch (err) {
    mensajeConsumo.textContent = `Error: ${err.message}`;
  }
});