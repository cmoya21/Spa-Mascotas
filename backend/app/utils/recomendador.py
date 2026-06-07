def recomendar_productos(mascota, productos, max_resultados=6):
    """
    Motor de recomendación basado en características de la mascota.
    Asigna un score a cada producto y retorna los más relevantes.
    """
    especie = (getattr(mascota, "especie", "") or "").lower()
    temperamento = (getattr(mascota, "temperamento", "") or "").lower()
    alergias = (getattr(mascota, "alergias_conocidas", "") or "").lower()
    peso_kg = getattr(mascota, "peso_kg", None) or 5.0

    if peso_kg <= 10:
        tamano = "pequeno"
    elif peso_kg <= 25:
        tamano = "mediano"
    elif peso_kg <= 45:
        tamano = "grande"
    else:
        tamano = "gigante"

    palabras_especie = {
        "perro": ["perro", "canino", "dog", "mascotas"],
        "gato": ["gato", "felino", "cat", "gatuno"],
        "otro": ["mascota", "animal"],
    }
    kw_especie = palabras_especie.get(especie, ["mascota"])

    resultados = []

    for producto in productos:
        if not getattr(producto, "activo", False) or (getattr(producto, "stock", 0) or 0) <= 0:
            continue

        texto = f"{getattr(producto, 'nombre', '')} {getattr(producto, 'descripcion', '') or ''}".lower()
        score = 0
        razones = []

        categoria = getattr(producto, "categoria", None)
        cat_nombre = (getattr(categoria, "nombre", "") or "").lower()

        if any(kw in texto for kw in kw_especie):
            score += 30
            razones.append(f"Ideal para {especie}s")

        if alergias:
            if cat_nombre in ["higiene", "salud"]:
                score += 20
                razones.append("Recomendado para mascotas con sensibilidades")
            if "hipo" in texto or "hipoalergenico" in texto:
                score += 15
                razones.append("Fórmula hipoalergénica")
            palabras_alergia = [p.strip() for p in alergias.split() if len(p.strip()) > 3]
            if any(p in texto for p in palabras_alergia):
                score -= 50
                razones.append("⚠ Puede contener alérgeno")

        if temperamento in ("agresivo", "ansioso"):
            if any(
                kw in texto
                for kw in ["calmante", "relajante", "tranquilizante", "calming", "stress"]
            ):
                score += 15
                razones.append("Ayuda a reducir el estrés")
            if cat_nombre == "salud":
                score += 10

        if tamano in ("grande", "gigante") and cat_nombre == "alimentos":
            score += 20
            razones.append("Nutrición para razas grandes")
        if tamano in ("pequeno", "mediano") and cat_nombre in ("juguetes", "accesorios"):
            score += 15
            razones.append("Tamaño adecuado para tu mascota")

        if (getattr(producto, "stock", 0) or 0) > 10:
            score += 5

        if score > 0:
            resultados.append({
                "producto": producto,
                "score": score,
                "razones": razones[:2],
            })

    resultados.sort(key=lambda item: item["score"], reverse=True)
    return resultados[:max_resultados]
