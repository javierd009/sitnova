"""
Vercel serverless function entry point.
Importa la aplicación FastAPI desde src/api/main.py
"""
from src.api.main import app

# Vercel espera una variable llamada "app" o "handler"
# En este caso, simplemente re-exportamos la app de FastAPI
