# Eco Menu

## 1. Nombre y descripción

**Eco Menu** es una aplicación web para organizar insumos de un restaurante familiar, revisar caducidades, registrar consumo y salidas, y resumir pérdidas y recuperaciones. Las recomendaciones con Gemini son opcionales.

## 2. Usuarios objetivo y cómo se identificaron

La aplicación contempla tres roles: **Dueño**, **Encargado** y **Empleado**. Estos roles y sus tareas se identificaron en el alcance funcional disponible del proyecto y se reflejan en los permisos y paneles de la aplicación.

No se encontraron entrevistas, transcripciones ni resultados de pruebas de usuario en los archivos disponibles. No se afirma que se hayan realizado. Agrega aquí la evidencia y completa: **[COMPLETAR: cómo se reclutó a los usuarios, cuántas personas participaron, método y hallazgos]**.

## 3. Solución

### Flujo principal

1. La persona inicia sesión y accede al panel correspondiente a su rol.
2. El dueño consulta el resumen, los avisos, el reporte de insumos y los reportes enviados por el encargado.
3. El encargado registra y revisa inventario, caducidades y reportes; puede enviar un resumen al dueño.
4. El empleado consulta avisos y sugerencias, y registra el consumo de insumos.
5. El equipo registra salidas por consumo, promoción, ganadería, reciclaje o pérdida. El reporte diferencia ingresos recuperados y pérdida neta.
6. Gemini puede analizar el inventario y redactar recomendaciones cuando se configura una clave válida.

### Propuesta de valor

Reunir inventario, caducidades, salidas y reportes por rol en una aplicación sencilla, para facilitar decisiones oportunas sobre los insumos y dar visibilidad a las mermas y recuperaciones.

### Decisiones clave

- Interfaz web en español con permisos diferenciados por rol.
- SQLite para mantener los datos localmente sin configurar un servidor de base de datos.
- Gemini es opcional: el inventario y los demás apartados pueden utilizarse sin configurar la API.
- La carpeta `evidencia/` contiene únicamente los archivos de proceso que se encontraron; sus faltantes están señalados como **[COMPLETAR]**.

## 4. Tecnologías usadas y por qué

- **Python**: lenguaje de la lógica del servidor.
- **Flask**: rutas web, sesiones y renderizado de páginas.
- **SQLite**: persistencia local simple, sin servicio de base de datos separado.
- **Jinja y HTML/CSS**: plantillas y presentación de la interfaz.
- **Google Gen AI SDK / Gemini Developer API**: análisis y sugerencias opcionales de inventario.
- **unittest**: pruebas automatizadas incluidas en `src/tests/`.

## 5. Requisitos, instalación y ejecución

Requisitos: Windows, Python 3.10 o posterior, PowerShell y conexión a internet para instalar dependencias. La integración con Gemini requiere internet y una clave de API propia.

Abre PowerShell y ejecuta estos comandos:

```powershell
Set-Location "$HOME\Downloads\EcoMenu (DEMO)"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\src\requirements.txt
Copy-Item .\.env.example .\src\.env
notepad .\src\.env
```

En `src\.env`, reemplaza los marcadores de las tres claves `DEMO_PASSWORD_...` con claves de demostración elegidas por ti. Para usar Gemini, también reemplaza `TU_API_KEY_AQUI` según la sección siguiente. `SECRET_KEY` puede quedarse vacío para una ejecución local; la aplicación generará una clave de sesión aleatoria al arrancar.

Inicia la aplicación local:

```powershell
python .\src\app.py
```

Abre <http://127.0.0.1:5000>. Si el puerto 5000 está ocupado, detén la ejecución o abre otra consola y usa:

```powershell
$env:PORT = "5001"
python .\src\app.py
```

Para una demostración pública temporal desde Windows, instala `cloudflared` si aún no está instalado:

```powershell
winget install --id Cloudflare.cloudflared -e
```

Después ejecuta:

```powershell
Set-Location "$HOME\Downloads\EcoMenu (DEMO)"
.\.venv\Scripts\Activate.ps1
Set-Location "$HOME\Downloads\EcoMenu (DEMO)\src"
.\start_demo.ps1
```

Comparte la URL que imprime Cloudflare. La URL es temporal y cambia al reiniciar; el proceso debe permanecer abierto y la laptop conectada a internet. Cualquier persona que tenga el enlace puede acceder y modificar la base local de demostración. No uses este túnel como alojamiento de producción.

Para correr las pruebas:

```powershell
Set-Location "$HOME\Downloads\EcoMenu (DEMO)"
.\.venv\Scripts\Activate.ps1
Set-Location .\src
python -m unittest discover -s tests -v
```

## 6. Configuración de la API

### Servicio y clave

La aplicación usa **Gemini Developer API** mediante el SDK oficial `google-genai`. Puedes obtener una clave desde [Google AI Studio](https://aistudio.google.com/apikey). Usa una clave propia y revisa el nivel de facturación y las cuotas de tu proyecto en Google AI Studio.

1. Copia `.env.example` a `src\.env` con el comando de instalación anterior.
2. Abre `src\.env`.
3. En la **línea 5**, reemplaza `TU_API_KEY_AQUI` por la clave de tu proyecto:

   ```dotenv
   GEMINI_API_KEY=TU_API_KEY_AQUI
   ```

4. Guarda el archivo. `src\.env` está excluido de Git; no compartas ni subas ese archivo.
5. El modelo se selecciona con `GEMINI_MODEL` (línea 6 del ejemplo). El valor incluido es `gemini-3.5-flash-lite`.

### URL base

El proyecto no define una variable `API_URL`. El SDK de Google usa su endpoint predeterminado: `https://generativelanguage.googleapis.com`. En el código, el cliente se crea en `src/gemini_service.py`, en la llamada `genai.Client(api_key=api_key)`. No cambies la URL ni agregues una variable `API_URL` para esta configuración normal.

### Comprobar la conexión y errores frecuentes

1. Inicia la aplicación y entra con el usuario de prueba **Dueño**; la contraseña se completa desde la clave de demostración que configuraste en `src\.env`.
2. Abre **Análisis con Gemini** y solicita un análisis. Esta acción envía inventario a la API y consume cuota del proyecto.
3. Si aparece **“Falta la clave de Gemini”**, revisa que `src\.env` exista y que `GEMINI_API_KEY` no conserve el marcador.
4. Si aparece **“No pude conectar con Gemini”**, comprueba que la clave sea válida, que el nombre del modelo esté disponible y que haya conexión a internet. En esta versión no se configura manualmente una URL base.
5. Si la API responde `429` o `RESOURCE_EXHAUSTED`, se alcanzó un límite de solicitudes o cuota; revisa los límites de tu proyecto.
6. Si aparece un error `503`, Gemini puede estar temporalmente saturado; espera e inténtalo más tarde.

Una clave de Gemini puede tener cuotas gratuitas o cargos según el proyecto y su facturación. La carpeta no incluye una clave real. Para asegurar que no haya cargos, revisa la configuración vigente de facturación y límites de tu proyecto antes de usar la API.

### Fuentes técnicas

- Python: <https://docs.python.org/3/>
- Flask: <https://flask.palletsprojects.com/>
- SQLite: <https://www.sqlite.org/docs.html>
- Gemini Developer API: <https://ai.google.dev/gemini-api/docs>
- SDK de Google Gen AI para Python: <https://googleapis.github.io/python-genai/>

## Evidencia y datos pendientes

En `evidencia/` están las imágenes que se encontraron junto al proyecto y un QR de demostración temporal. No se hallaron entrevistas, bocetos, capturas del proceso ni documentos de investigación; revisa `evidencia/README.txt` y completa los campos **[COMPLETAR]** si dispones de esos materiales.

- Integrantes/autores: **[COMPLETAR]**
- Enlace al repositorio o entrega final: **[COMPLETAR]**
- Fuentes de investigación sobre usuarios y problema: **[COMPLETAR]**
- Fechas y contexto de la validación: **[COMPLETAR]**
