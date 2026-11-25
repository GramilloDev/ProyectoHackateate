"""Arranca la app usando la base de datos persistente de la demo."""

import importlib
import secrets
from pathlib import Path

import database

database.DB_PATH = Path(__file__).resolve().with_name("cocina_clara_demo.db")
eco_menu = importlib.import_module("app")
eco_menu.app.secret_key = secrets.token_urlsafe(32)
eco_menu.app.run(host="127.0.0.1", port=5002, debug=False)
