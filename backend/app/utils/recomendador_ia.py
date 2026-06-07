import json
import os

import requests


def recomendar_productos_con_claude(mascota, productos, max_resultados=6):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    if not productos:
        return []

    prompt = {
        "mascota": {
            "nombre": getattr(mascota, "nombre", None),
            "especie": getattr(mascota, "especie", None),
            "raza": getattr(mascota, "raza", None),
            "tamano": getattr(mascota, "tamano", None),
            "peso_kg": float(getattr(mascota, "peso_kg", 0) or 0),
            "temperamento": getattr(mascota, "temperamento", None),
            "alergias_conocidas": getattr(mascota, "alergias_conocidas", None),
        },
        "productos": [
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "categoria": getattr(getattr(producto, "categoria", None), "nombre", None),
                "stock": int(producto.stock or 0),
            }
            for producto in productos
        ],
        "max_resultados": max_resultados,
    }

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Devuelve solo JSON válido con esta forma: "
                        '{"recomendaciones":[{"producto_id":1,"razon":"..."}]} '\
                        "Usa únicamente productos existentes y prioriza seguridad, alergias, especie y tamaño.\n\n"
                        f"Contexto: {json.dumps(prompt, ensure_ascii=False)}"
                    ),
                }
            ],
        }
    ]

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                "max_tokens": 500,
                "messages": messages,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        contenido = "".join(part.get("text", "") for part in payload.get("content", []) if isinstance(part, dict))
        if not contenido:
            return None
        data = json.loads(contenido)
        recomendaciones = data.get("recomendaciones", [])
        if not isinstance(recomendaciones, list):
            return None
        return recomendaciones[:max_resultados]
    except Exception:
        return None
