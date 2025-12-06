#!/usr/bin/env python3
"""
Script de prueba para verificar el matching fonético.

Este script prueba que "Daisy" pueda hacer match con "Deisy" en la base de datos.
"""

import sys
import unicodedata
from typing import List


# Copiar las funciones necesarias del código
def normalize_text(text: str) -> str:
    """Remove accents and normalize text for search."""
    if not text:
        return text
    # Normalize unicode and remove accents
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


PHONETIC_VARIATIONS = [
    ("ai", "ei"),  # Daisy ↔ Deisy
    ("ei", "ai"),  # Deisy ↔ Daisy
    ("y", "i"),    # Daisy ↔ Daisi
    ("i", "y"),    # Daisi ↔ Daisy
    ("ll", "y"),   # Lluis ↔ Yuis
    ("y", "ll"),   # Yolanda ↔ Llolanda (menos común pero posible)
    ("b", "v"),    # Bictoria ↔ Victoria
    ("v", "b"),    # Victoria ↔ Bictoria
    ("s", "z"),    # Rosa ↔ Roza
    ("z", "s"),    # Roza ↔ Rosa
    ("c", "s"),    # Cecilia ↔ Sesilia
    ("s", "c"),    # Sesilia ↔ Cecilia
]


def generate_phonetic_variations(text: str, max_variations: int = 5) -> List[str]:
    """
    Genera variaciones fonéticas de un texto para matching más robusto.
    """
    if not text:
        return [text]

    # Normalizar primero (quitar acentos)
    text_normalized = normalize_text(text.lower().strip())

    # Siempre incluir el original
    variations = {text_normalized}

    # Aplicar cada patrón de variación
    for pattern_from, pattern_to in PHONETIC_VARIATIONS:
        if pattern_from in text_normalized:
            # Generar variación reemplazando el patrón
            variation = text_normalized.replace(pattern_from, pattern_to)
            variations.add(variation)

            # Limitar el número de variaciones para evitar explosión combinatoria
            if len(variations) >= max_variations:
                break

    return list(variations)


def test_phonetic_matching():
    """Prueba el matching fonético con casos reales."""

    print("=" * 60)
    print("TEST: Matching Fonético - Daisy ↔ Deisy")
    print("=" * 60)

    # Caso 1: Lo que dice el visitante (transcripción de voz)
    voice_input = "Daisy Colorado"
    print(f"\n📢 ENTRADA DE VOZ (Speech-to-Text): '{voice_input}'")

    # Extraer nombre y apellido
    parts = voice_input.split()
    nombre_voice = parts[0] if len(parts) > 0 else ""
    apellido_voice = parts[1] if len(parts) > 1 else ""

    print(f"   - Nombre: '{nombre_voice}'")
    print(f"   - Apellido: '{apellido_voice}'")

    # Generar variaciones
    nombre_variations = generate_phonetic_variations(nombre_voice)
    apellido_variations = generate_phonetic_variations(apellido_voice)

    print(f"\n🔄 VARIACIONES FONÉTICAS GENERADAS:")
    print(f"   - Nombre '{nombre_voice}': {nombre_variations}")
    print(f"   - Apellido '{apellido_voice}': {apellido_variations}")

    # Caso 2: Lo que está en la base de datos
    db_name = "Deisy Colorado"
    print(f"\n💾 NOMBRE EN BASE DE DATOS: '{db_name}'")

    # Simular búsqueda
    db_parts = db_name.lower().split()
    db_nombre = db_parts[0] if len(db_parts) > 0 else ""
    db_apellido = db_parts[1] if len(db_parts) > 1 else ""

    print(f"   - Nombre DB: '{db_nombre}'")
    print(f"   - Apellido DB: '{db_apellido}'")

    # Generar variaciones del nombre en DB
    db_nombre_variations = generate_phonetic_variations(db_nombre)
    db_apellido_variations = generate_phonetic_variations(db_apellido)

    print(f"\n🔄 VARIACIONES FONÉTICAS DE DB:")
    print(f"   - Nombre DB '{db_nombre}': {db_nombre_variations}")
    print(f"   - Apellido DB '{db_apellido}': {db_apellido_variations}")

    # Verificar si hay match
    print(f"\n🔍 VERIFICANDO MATCH:")

    # Nombre match
    nombre_match = False
    nombre_matched_var = None
    for v_variation in nombre_variations:
        if v_variation in db_nombre_variations:
            nombre_match = True
            nombre_matched_var = v_variation
            break

    if nombre_match:
        print(f"   ✅ NOMBRE MATCH: '{nombre_voice}' ↔ '{db_nombre}' (variación común: '{nombre_matched_var}')")
    else:
        print(f"   ❌ NOMBRE NO MATCH: '{nombre_voice}' ✗ '{db_nombre}'")

    # Apellido match
    apellido_match = False
    apellido_matched_var = None
    for v_variation in apellido_variations:
        if v_variation in db_apellido_variations or v_variation == db_apellido:
            apellido_match = True
            apellido_matched_var = v_variation
            break

    if apellido_match:
        print(f"   ✅ APELLIDO MATCH: '{apellido_voice}' ↔ '{db_apellido}' (variación: '{apellido_matched_var}')")
    else:
        print(f"   ❌ APELLIDO NO MATCH: '{apellido_voice}' ✗ '{db_apellido}'")

    # Resultado final
    print(f"\n{'=' * 60}")
    if nombre_match and apellido_match:
        print("✅✅✅ RESULTADO: MATCH EXITOSO ✅✅✅")
        print(f"El visitante que dijo '{voice_input}' SERÁ ENCONTRADO")
        print(f"en la base de datos como '{db_name}'")
        return True
    else:
        print("❌❌❌ RESULTADO: NO MATCH ❌❌❌")
        print(f"El visitante que dijo '{voice_input}' NO será encontrado")
        return False
    print("=" * 60)


def test_other_cases():
    """Prueba otros casos de variaciones fonéticas."""
    print("\n\n" + "=" * 60)
    print("TESTS ADICIONALES")
    print("=" * 60)

    test_cases = [
        ("Victoria", "Bictoria"),  # b/v variation
        ("Rosa", "Roza"),          # s/z variation
        ("Cecilia", "Sesilia"),    # c/s variation
        ("Daisy", "Deisy"),        # ai/ei variation (caso principal)
        ("Deisy", "Daisy"),        # ei/ai variation (reverso)
    ]

    for input_name, db_name in test_cases:
        input_vars = generate_phonetic_variations(input_name.lower())
        db_vars = generate_phonetic_variations(db_name.lower())

        # Buscar variación común
        common = set(input_vars) & set(db_vars)

        if common:
            print(f"\n✅ '{input_name}' ↔ '{db_name}': MATCH (variación común: {common})")
        else:
            print(f"\n❌ '{input_name}' ✗ '{db_name}': NO MATCH")
            print(f"   Input vars: {input_vars}")
            print(f"   DB vars: {db_vars}")


if __name__ == "__main__":
    success = test_phonetic_matching()
    test_other_cases()

    print("\n\n" + "=" * 60)
    if success:
        print("🎉 TEST PASADO: El fix está funcionando correctamente")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ TEST FALLIDO: Revisar implementación")
        print("=" * 60)
        sys.exit(1)
