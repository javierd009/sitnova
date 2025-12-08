#!/usr/bin/env python3
"""
Script para actualizar la configuración de AsterSIPVox.

Este script lee el archivo de configuración V13 y lo puede:
1. Mostrar en formato JSON para copiar/pegar
2. Exportar a un archivo JSON
3. (Futuro) Actualizar via API directamente

Uso:
    python scripts/update_astersipvox_config.py --show
    python scripts/update_astersipvox_config.py --export output.json
    python scripts/update_astersipvox_config.py --validate

Nota: AsterSIPVox actualmente NO tiene API para actualizar extensiones.
      Por ahora, el script genera la config para copiar/pegar manualmente.
"""

import argparse
import json
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Archivo de configuración V13
CONFIG_FILE = ROOT_DIR / "docs" / "astersipvox-config-v13.json"

# Colores para output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def load_config():
    """Carga la configuración desde el archivo JSON."""
    if not CONFIG_FILE.exists():
        print(f"{Colors.RED}Error: No se encontró {CONFIG_FILE}{Colors.END}")
        sys.exit(1)

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_config(config):
    """Valida que la configuración tenga los campos requeridos."""
    issues = []

    if not isinstance(config, list) or len(config) == 0:
        issues.append("Config debe ser una lista con al menos una extensión")
        return issues

    ext = config[0]

    # Campos requeridos
    required_fields = [
        'username', 'password', 'recipientURI', 'systemPrompt',
        'extraTools', 'selectedTools'
    ]

    for field in required_fields:
        if field not in ext:
            issues.append(f"Campo requerido faltante: {field}")

    # Validar extraTools
    if 'extraTools' in ext:
        for i, tool in enumerate(ext['extraTools']):
            if 'modelToolName' not in tool:
                issues.append(f"Tool {i}: falta modelToolName")
            if 'http' not in tool:
                issues.append(f"Tool {i}: falta configuración http")
            elif 'baseUrlPattern' not in tool.get('http', {}):
                issues.append(f"Tool {i}: falta baseUrlPattern en http")

    # Validar selectedTools
    if 'selectedTools' in ext:
        for tool in ext['selectedTools']:
            if 'toolName' not in tool:
                issues.append(f"selectedTool sin toolName")

    # Validar systemPrompt no esté vacío
    if not ext.get('systemPrompt', '').strip():
        issues.append("systemPrompt está vacío")

    return issues


def show_config(config):
    """Muestra la configuración con resaltado."""
    ext = config[0]

    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Configuración AsterSIPVox - V13{Colors.END}")
    print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")

    # Info básica
    print(f"{Colors.BLUE}Extensión:{Colors.END} {ext.get('username')}")
    print(f"{Colors.BLUE}Descripción:{Colors.END} {ext.get('description')}")
    print(f"{Colors.BLUE}Modelo:{Colors.END} {ext.get('model')}")
    print(f"{Colors.BLUE}Idioma:{Colors.END} {ext.get('languageHint')}")
    print(f"{Colors.BLUE}Timezone:{Colors.END} {ext.get('timezone')}")
    print(f"{Colors.BLUE}Temperatura:{Colors.END} {ext.get('temperature')}")

    # Tools
    print(f"\n{Colors.YELLOW}HTTP Tools ({len(ext.get('extraTools', []))}){Colors.END}")
    for tool in ext.get('extraTools', []):
        print(f"  - {tool.get('modelToolName')}: {tool.get('description', 'N/A')[:50]}")

    print(f"\n{Colors.YELLOW}Built-in Tools ({len(ext.get('selectedTools', []))}){Colors.END}")
    for tool in ext.get('selectedTools', []):
        print(f"  - {tool.get('toolName')}: {tool.get('descriptionOverride', 'N/A')[:50]}")

    # System prompt preview
    prompt = ext.get('systemPrompt', '')
    print(f"\n{Colors.YELLOW}System Prompt (primeras 500 chars){Colors.END}")
    print(f"{Colors.GREEN}{prompt[:500]}...{Colors.END}")

    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")


def export_config(config, output_file):
    """Exporta la configuración a un archivo JSON."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"{Colors.GREEN}Configuración exportada a: {output_file}{Colors.END}")


def export_prompt_only(config, output_file):
    """Exporta solo el system prompt a un archivo de texto."""
    prompt = config[0].get('systemPrompt', '')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"{Colors.GREEN}System prompt exportado a: {output_file}{Colors.END}")


def generate_curl_commands(config):
    """Genera comandos curl para referencia (API no disponible aún)."""
    ext = config[0]

    print(f"\n{Colors.YELLOW}Nota: AsterSIPVox NO tiene API pública para actualizar config.{Colors.END}")
    print(f"{Colors.YELLOW}Los siguientes comandos son solo para referencia futura.{Colors.END}\n")

    print(f"{Colors.BLUE}# Health check{Colors.END}")
    print("curl https://devaster.integratec-ia.com/health\n")

    print(f"{Colors.BLUE}# Ver extensiones (requiere auth){Colors.END}")
    print("curl -H 'Authorization: Bearer <token>' https://devaster.integratec-ia.com/api/extensions\n")


def main():
    parser = argparse.ArgumentParser(
        description='Gestionar configuración de AsterSIPVox para SITNOVA'
    )
    parser.add_argument('--show', action='store_true',
                        help='Mostrar configuración actual')
    parser.add_argument('--validate', action='store_true',
                        help='Validar configuración')
    parser.add_argument('--export', type=str, metavar='FILE',
                        help='Exportar a archivo JSON')
    parser.add_argument('--export-prompt', type=str, metavar='FILE',
                        help='Exportar solo system prompt a archivo de texto')
    parser.add_argument('--curl', action='store_true',
                        help='Mostrar comandos curl de referencia')
    parser.add_argument('--json', action='store_true',
                        help='Mostrar config completa en JSON (para copiar)')

    args = parser.parse_args()

    # Cargar config
    config = load_config()

    # Ejecutar comandos
    if args.validate:
        issues = validate_config(config)
        if issues:
            print(f"{Colors.RED}Errores de validación:{Colors.END}")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print(f"{Colors.GREEN}Configuración válida{Colors.END}")

    if args.show:
        show_config(config)

    if args.export:
        export_config(config, args.export)

    if args.export_prompt:
        export_prompt_only(config, args.export_prompt)

    if args.curl:
        generate_curl_commands(config)

    if args.json:
        print(json.dumps(config, ensure_ascii=False, indent=2))

    # Si no se especificó ningún argumento, mostrar ayuda
    if not any(vars(args).values()):
        parser.print_help()
        print(f"\n{Colors.YELLOW}Ejemplo de uso:{Colors.END}")
        print(f"  python scripts/update_astersipvox_config.py --show")
        print(f"  python scripts/update_astersipvox_config.py --validate")
        print(f"  python scripts/update_astersipvox_config.py --json > config_to_paste.json")


if __name__ == '__main__':
    main()
