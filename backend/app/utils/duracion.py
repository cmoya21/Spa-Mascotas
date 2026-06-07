import math


DEFAULT_FACTOR_TAMANO = {
    "pequeno": 1.0,
    "mediano": 1.15,
    "grande": 1.30,
    "gigante": 1.30,
}


def _resolver_categoria_tamano(peso_kg):
    if peso_kg is None:
        peso_kg = 5.0

    if peso_kg <= 10:
        return "pequeno"
    if peso_kg <= 25:
        return "mediano"
    if peso_kg <= 45:
        return "grande"
    return "gigante"


def _normalizar_factor_tamano(factor_tamano_raza):
    if not isinstance(factor_tamano_raza, dict):
        return DEFAULT_FACTOR_TAMANO.copy()

    normalized = DEFAULT_FACTOR_TAMANO.copy()
    for key, value in factor_tamano_raza.items():
        if key in normalized:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                continue
    return normalized


def calcular_duracion(duracion_base, peso_kg, temperamento, factor_tamano_raza):
    """
    Calcula la duración real del servicio ajustada por mascota.
    duracion_base: int (minutos, múltiplo de 15)
    peso_kg: float
    temperamento: str (tranquilo|jugueton|agresivo|ansioso|otro)
    factor_tamano_raza: dict {"pequeno":1.0,"mediano":1.15,"grande":1.30,"gigante":1.30}
    Retorna: int (minutos, redondeado al múltiplo de 15 superior)
    """
    factores = _normalizar_factor_tamano(factor_tamano_raza)
    categoria_tamano = _resolver_categoria_tamano(peso_kg)
    factor = factores.get(categoria_tamano, 1.0)

    duracion = float(duracion_base) * float(factor)
    extras = {"agresivo": 15, "ansioso": 10, "otro": 5}
    duracion += extras.get((temperamento or "").strip().lower(), 0)

    return int(math.ceil(duracion / 15.0) * 15)


def calcular_duracion_simple(duracion_base, peso_kg, temperamento, factor_tamano_raza):
    return calcular_duracion(duracion_base, peso_kg, temperamento, factor_tamano_raza)


def desglose_duracion(duracion_base, peso_kg, temperamento, factor_tamano_raza, hora_inicio=None):
    factores = _normalizar_factor_tamano(factor_tamano_raza)
    categoria_tamano = _resolver_categoria_tamano(peso_kg)
    factor = factores.get(categoria_tamano, 1.0)
    temperamento_normalizado = (temperamento or "").strip().lower()
    extra_temperamento = {"agresivo": 15, "ansioso": 10, "otro": 5}.get(temperamento_normalizado, 0)
    duracion_total = calcular_duracion(duracion_base, peso_kg, temperamento, factores)

    resultado = {
        "duracion_base": int(duracion_base),
        "factor_tamano": float(factor),
        "categoria_tamano": categoria_tamano,
        "extra_temperamento": extra_temperamento,
        "temperamento": temperamento_normalizado or None,
        "duracion_total": duracion_total,
    }

    if hora_inicio:
        try:
            from datetime import datetime, timedelta

            inicio = datetime.fromisoformat(hora_inicio) if "T" in str(hora_inicio) else datetime.combine(
                datetime.today().date(), datetime.strptime(str(hora_inicio), "%H:%M").time()
            )
            resultado["hora_fin_ejemplo"] = (inicio + timedelta(minutes=duracion_total)).isoformat()
        except Exception:
            resultado["hora_fin_ejemplo"] = None

    return resultado
