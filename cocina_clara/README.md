# Eco Menu

Aplicación local para gestionar el inventario de un restaurante familiar,
anticipar caducidades, reducir desperdicios y comunicar reportes entre roles.
Está hecha con Python, Flask y SQLite; el análisis y las sugerencias usan Gemini.

## Inicio rápido

Desde esta carpeta, en PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura `GEMINI_API_KEY` en `.env` con una clave propia y ejecuta:

```powershell
python app.py
```

Abre <http://127.0.0.1:5000>. Si el puerto está ocupado, usa
`$env:PORT=5001` antes de iniciar. El archivo de base de datos existente se
conserva para no perder registros; las nuevas tablas y columnas se agregan
automáticamente al iniciar.

## Demo temporal con QR

En Windows, ejecuta `.\start_demo.ps1` desde esta carpeta. El script inicia la
app sin modo depuración y crea un enlace temporal de Cloudflare para compartir.
La URL cambia cada vez que se inicia y deja de funcionar al cerrar el script,
apagar la laptop o perder la conexión. Los datos de esta demo se guardan en
`cocina_clara_demo.db`, separado de la base de datos normal y excluido de Git.

Ejecuta las pruebas con:

```powershell
python -m unittest discover -s tests
```

## Usuarios de prueba

| Rol | Usuario | Contraseña |
| --- | --- | --- |
| Dueño | `dueño` | `dueno123` |
| Encargado | `encargado` | `encargado123` |
| Empleado | `empleado` | `empleado123` |

En el inicio de sesión se puede pulsar una cuenta de prueba para completar sus
credenciales. El nombre de usuario del dueño acepta la `ñ` en UTF-8.

## Funciones

- Inventario por categorías, fecha de caducidad, fecha de compra, inversión y
  próxima fecha de reabastecimiento.
- Avisos organizados por categoría y registro de consumo sin permitir usar
  insumos caducados.
- Registro de salidas para consumo, promoción, ganadería, reciclaje o pérdida,
  con cantidad, fecha, autor y dinero recuperado.
- Reporte de recuperación económica, kilos enviados a ganadería y lotes de
  reciclaje frente a la pérdida neta.
- El encargado puede redactar un resumen con Gemini, escribirlo o editarlo y
  enviarlo a la bandeja del dueño, que permite marcarlo como leído.
- Gemini ofrece ideas de uso prioritario, platillos, preparación semanal,
  promociones para dar salida a productos y recuperación responsable.
- El empleado puede consultar sugerencias para el turno.

Para ganadería, separa desde el origen los residuos orgánicos limpios (vegetales,
frutas o pan sin moho ni químicos) y coordina retiros frecuentes. Enjuaga y
aplasta las latas limpias antes de acumularlas por lote para reciclaje.

## Configuración de Gemini

`GEMINI_MODEL` es opcional; por defecto se usa `gemini-3.5-flash-lite`.
Si falta la clave o Gemini no está disponible, los demás apartados siguen
funcionando.

No agregues claves al código ni al archivo `.env.example`. `.env` está excluido
del control de versiones; si una clave se compartió por accidente, revócala y
genera otra.
