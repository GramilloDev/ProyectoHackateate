const express = require('express');
const cors = require('cors');
require('dotenv').config();
const { sql, getPool } = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// 1. Salud del servidor y conexión a SQL Server
app.get('/api/health', async (req, res) => {
  try {
    const pool = await getPool();
    await pool.request().query('SELECT 1 AS ok');
    res.json({ ok: true, message: 'API y SQL Server conectados' });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 2. Vista: Stock de insumos
app.get('/api/stock-insumos', async (req, res) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query('SELECT * FROM dbo.vw_StockInsumos');
    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 3. Vista: Ventas por platillo
app.get('/api/ventas-platillo', async (req, res) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query('SELECT * FROM dbo.vw_VentasPorPlatillo');
    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 4. Procedimiento: Validar login
// Body: { "nombreUsuario": "...", "contrasena": "...", "nombreRol": "..." }
app.post('/api/login', async (req, res) => {
  const { nombreUsuario, contrasena, nombreRol } = req.body;
  if (!nombreUsuario || !contrasena) {
    return res.status(400).json({ ok: false, error: 'Faltan nombreUsuario o contrasena' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('NombreUsuario', sql.VarChar(100), nombreUsuario)
      .input('Contrasena', sql.NVarChar(255), contrasena)
      .input('NombreRol', sql.VarChar(100), nombreRol || null)
      .execute('dbo.sp_ValidarLogin');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 5. Procedimiento: Registrar venta
// Body: { "idUsuario": 1, "idPlatillo": 1, "cantidad": 1 }
app.post('/api/ventas', async (req, res) => {
  const { idUsuario, idPlatillo, cantidad } = req.body;
  if (!idUsuario || !idPlatillo || !cantidad) {
    return res.status(400).json({ ok: false, error: 'Faltan idUsuario, idPlatillo o cantidad' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('IdUsuario', sql.Int, Number(idUsuario))
      .input('IdPlatillo', sql.Int, Number(idPlatillo))
      .input('Cantidad', sql.Int, Number(cantidad))
      .execute('dbo.sp_RegistrarVenta');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 6. Procedimiento: Ver inventario (opcional ?diasAviso=7)
app.get('/api/inventario', async (req, res) => {
  const diasAviso = req.query.diasAviso !== undefined ? Number(req.query.diasAviso) : 7;

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('DiasAviso', sql.Int, diasAviso)
      .execute('dbo.sp_VerInventario');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 7. Procedimiento: Insumos por agotarse
app.get('/api/insumos-por-agotarse', async (req, res) => {
  try {
    const pool = await getPool();
    const result = await pool.request().execute('dbo.sp_InsumosPorAgotarse');
    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 8. Procedimiento: Insumos próximos a vencer (ej. /api/insumos-proximos-a-vencer?dias=7)
app.get('/api/insumos-proximos-a-vencer', async (req, res) => {
  const dias = req.query.dias !== undefined ? Number(req.query.dias) : 7;

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('Dias', sql.Int, dias)
      .execute('dbo.sp_InsumosProximosAVencer');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 9. Procedimiento: Registrar entrada de inventario
// Body: { "idUsuario": 1, "nombreProducto": "...", "idUnidad": 1, "cantidad": 10, "fechaCaducidad": "2026-12-31", "costoUnitario": 25.5 }
app.post('/api/entradas', async (req, res) => {
  const { idUsuario, nombreProducto, idUnidad, cantidad, fechaCaducidad, costoUnitario } = req.body;
  if (!idUsuario || !nombreProducto || !idUnidad || cantidad === undefined) {
    return res.status(400).json({ ok: false, error: 'Faltan campos obligatorios para la entrada' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('IdUsuario', sql.Int, Number(idUsuario))
      .input('NombreProducto', sql.VarChar(150), nombreProducto)
      .input('IdUnidad', sql.Int, Number(idUnidad))
      .input('Cantidad', sql.Decimal(12, 2), Number(cantidad))
      .input('FechaCaducidad', sql.Date, fechaCaducidad ? new Date(fechaCaducidad) : null)
      .input('CostoUnitario', sql.Decimal(12, 2), costoUnitario !== undefined ? Number(costoUnitario) : 0)
      .execute('dbo.sp_RegistrarEntrada');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 10. Procedimiento: Registrar consumo de insumo
// Body: { "idUsuario": 1, "idInsumo": 1, "cantidad": 2.5, "idUnidad": 1 }
app.post('/api/consumos', async (req, res) => {
  const { idUsuario, idInsumo, cantidad, idUnidad } = req.body;
  if (!idUsuario || !idInsumo || cantidad === undefined || !idUnidad) {
    return res.status(400).json({ ok: false, error: 'Faltan campos obligatorios para el consumo' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('IdUsuario', sql.Int, Number(idUsuario))
      .input('IdInsumo', sql.Int, Number(idInsumo))
      .input('Cantidad', sql.Decimal(12, 2), Number(cantidad))
      .input('IdUnidad', sql.Int, Number(idUnidad))
      .execute('dbo.sp_RegistrarConsumo');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 11. Procedimiento: Registrar merma
// Body: { "idUsuario": 1, "idEntrada": 1, "cantidad": 1, "motivo": "Caducado" }
app.post('/api/mermas', async (req, res) => {
  const { idUsuario, idEntrada, cantidad, motivo } = req.body;
  if (!idUsuario || !idEntrada || cantidad === undefined || !motivo) {
    return res.status(400).json({ ok: false, error: 'Faltan campos obligatorios para la merma' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('IdUsuario', sql.Int, Number(idUsuario))
      .input('IdEntrada', sql.Int, Number(idEntrada))
      .input('Cantidad', sql.Decimal(12, 2), Number(cantidad))
      .input('Motivo', sql.VarChar(255), motivo)
      .execute('dbo.sp_RegistrarMerma');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 12. Procedimiento: Resumen del dueño (ej. /api/resumen-dueno?fechaInicio=2026-11-01&fechaFin=2026-11-30)
app.get('/api/resumen-dueno', async (req, res) => {
  const { fechaInicio, fechaFin } = req.query;
  if (!fechaInicio || !fechaFin) {
    return res.status(400).json({ ok: false, error: 'Faltan fechaInicio y fechaFin (YYYY-MM-DD)' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('FechaInicio', sql.Date, new Date(fechaInicio))
      .input('FechaFin', sql.Date, new Date(fechaFin))
      .execute('dbo.sp_ResumenDueno');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// 13. Procedimiento: Cambiar área / rol del dueño
// Body: { "idUsuario": 1, "contrasena": "Dueno123 ", "rolDestino": "Encargado" }
app.post('/api/cambiar-area-dueno', async (req, res) => {
  const { idUsuario, contrasena, rolDestino } = req.body;
  if (!idUsuario || !contrasena || !rolDestino) {
    return res.status(400).json({ ok: false, error: 'Faltan idUsuario, contrasena o rolDestino' });
  }

  try {
    const pool = await getPool();
    const result = await pool
      .request()
      .input('IdUsuario', sql.Int, Number(idUsuario))
      .input('Contrasena', sql.NVarChar(255), contrasena)
      .input('RolDestino', sql.VarChar(100), rolDestino)
      .execute('dbo.sp_CambiarAreaDueno');

    res.json({ ok: true, data: result.recordset });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
});