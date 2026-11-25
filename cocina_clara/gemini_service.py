"""Única llamada a la API de Gemini."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent
MODELO_POR_DEFECTO = "gemini-3.5-flash-lite"

# Carga solo el .env del proyecto, sin importar desde dónde se ejecute la app.
load_dotenv(BASE_DIR / ".env")


class GeminiError(Exception):
    """Error amable para mostrar en la sección de análisis."""


def analizar_con_gemini(prompt):
    """Envía el prompt a Gemini y devuelve el texto de la respuesta."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiError(
            "Falta la clave de Gemini en .env. Añade tu GEMINI_API_KEY válida para usar el análisis."
        )

    modelo = os.getenv("GEMINI_MODEL", "").strip() or MODELO_POR_DEFECTO

    try:
        cliente = genai.Client(api_key=api_key)
        respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
        texto = (respuesta.text or "").strip()
    except Exception as error:
        if getattr(error, "code", None) == 503:
            raise GeminiError(
                "Gemini está experimentando alta demanda. Intenta de nuevo en unos momentos."
            ) from error
        raise GeminiError(
            "No pude conectar con Gemini. Revisa tu conexión a internet y que la clave "
            f"y el modelo ({modelo}) estén bien configurados en .env."
        ) from error

    if not texto:
        raise GeminiError(
            "Gemini respondió vacío. Intenta de nuevo en unos momentos."
        )

    return texto
