#!/usr/bin/env python3
"""
Script para obtener el schema actual de Supabase.
Ejecutar antes de cualquier migración para que Claude pueda ver el contexto.

Usage:
    python scripts/fetch_schema.py

Output:
    - data/current_schema.json (estructura completa)
    - data/current_schema.txt (formato legible)
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Configuración
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OUTPUT_DIR = Path(__file__).parent.parent / "data"


def get_supabase_client():
    """Crear cliente de Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos en .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_schema_via_rpc(client):
    """
    Obtener schema usando la función RPC get_full_schema().
    Esta función debe existir en Supabase.
    """
    try:
        result = client.rpc("get_full_schema").execute()
        return result.data
    except Exception as e:
        print(f"⚠️  Función RPC no disponible: {e}")
        return None


def fetch_schema_via_tables(client):
    """
    Obtener schema consultando tablas directamente.
    Fallback si la función RPC no existe.
    """
    schema = {
        "fetched_at": datetime.now().isoformat(),
        "tables": {},
        "views": [],
        "functions": []
    }

    # Lista de tablas conocidas del proyecto
    known_tables = [
        "access_logs",
        "condominiums",
        "residents",
        "vehicles",
        "pre_authorized_visitors",
        "visitor_registry",
        "notifications",
        "pending_authorizations",
        "access_events"  # Nueva tabla de tracking
    ]

    print("📊 Obteniendo estructura de tablas...")

    for table_name in known_tables:
        try:
            # Intentar obtener una fila para ver la estructura
            result = client.table(table_name).select("*").limit(0).execute()

            # Obtener metadata de columnas haciendo un select vacío
            # Supabase no expone directamente el schema, pero podemos inferirlo
            schema["tables"][table_name] = {
                "exists": True,
                "sample_columns": []  # Se llenará con la primera fila si existe
            }

            # Intentar obtener una fila de ejemplo
            sample = client.table(table_name).select("*").limit(1).execute()
            if sample.data and len(sample.data) > 0:
                schema["tables"][table_name]["sample_columns"] = list(sample.data[0].keys())
                schema["tables"][table_name]["row_count_sample"] = "1+"
            else:
                schema["tables"][table_name]["row_count_sample"] = "0"

            print(f"  ✅ {table_name}")

        except Exception as e:
            schema["tables"][table_name] = {
                "exists": False,
                "error": str(e)
            }
            print(f"  ❌ {table_name}: {e}")

    return schema


def format_schema_text(schema: dict) -> str:
    """Formatear schema como texto legible."""
    lines = [
        "=" * 60,
        "SCHEMA DE BASE DE DATOS - SITNOVA",
        f"Obtenido: {schema.get('fetched_at', 'N/A')}",
        "=" * 60,
        ""
    ]

    # Tablas
    lines.append("📊 TABLAS")
    lines.append("-" * 40)

    for table_name, info in schema.get("tables", {}).items():
        if info.get("exists", False):
            columns = info.get("sample_columns", [])
            if columns:
                lines.append(f"\n✅ {table_name}")
                lines.append(f"   Columnas: {', '.join(columns)}")
            else:
                lines.append(f"\n✅ {table_name} (tabla vacía)")
        else:
            lines.append(f"\n❌ {table_name} - NO EXISTE")
            if "error" in info:
                lines.append(f"   Error: {info['error']}")

    # Vistas
    if schema.get("views"):
        lines.append("\n")
        lines.append("👁️ VISTAS")
        lines.append("-" * 40)
        for view in schema["views"]:
            lines.append(f"  - {view}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


def main():
    print("🔌 Conectando a Supabase...")
    client = get_supabase_client()

    # Intentar RPC primero, luego fallback a consultas directas
    print("📥 Obteniendo schema...")
    schema = fetch_schema_via_rpc(client)

    if not schema:
        print("⚠️  Usando método alternativo (consultas directas)...")
        schema = fetch_schema_via_tables(client)

    # Asegurar que existe el directorio
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar JSON
    json_path = OUTPUT_DIR / "current_schema.json"
    with open(json_path, "w") as f:
        json.dump(schema, f, indent=2, default=str)
    print(f"✅ Schema JSON guardado: {json_path}")

    # Guardar texto legible
    txt_path = OUTPUT_DIR / "current_schema.txt"
    with open(txt_path, "w") as f:
        f.write(format_schema_text(schema))
    print(f"✅ Schema TXT guardado: {txt_path}")

    # Mostrar resumen
    print("\n" + format_schema_text(schema))


if __name__ == "__main__":
    main()
