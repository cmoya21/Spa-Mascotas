const DEFAULT_FACTOR_TAMANO = {
  pequeno: 1.0,
  mediano: 1.15,
  grande: 1.30,
  gigante: 1.30,
};

function _resolver_categoria_tamano(pesoKg) {
  const peso = pesoKg == null || Number.isNaN(Number(pesoKg)) ? 5 : Number(pesoKg);
  if (peso <= 10) return { clave: "pequeno", label: "Pequeña (≤10 kg)" };
  if (peso <= 25) return { clave: "mediano", label: "Mediana (≤25 kg)" };
  if (peso <= 45) return { clave: "grande", label: "Grande (≤45 kg)" };
  return { clave: "gigante", label: "Gigante o raza compleja (>45 kg)" };
}

function _normalizar_factores(factorTamanoRaza) {
  if (!factorTamanoRaza || typeof factorTamanoRaza !== "object") return { ...DEFAULT_FACTOR_TAMANO };
  const normalized = { ...DEFAULT_FACTOR_TAMANO };
  ["pequeno", "mediano", "grande", "gigante"].forEach((k) => {
    const v = factorTamanoRaza[k];
    const num = Number(v);
    if (!Number.isNaN(num) && isFinite(num)) normalized[k] = num;
  });
  return normalized;
}

function _ceil15(minutos) {
  const val = Number(minutos) || 0;
  return Math.ceil(val / 15) * 15;
}

export function calcularDesglose(duracionBase, pesoKg, temperamento, factorTamanoRaza) {
  const base = Number(duracionBase) || 0;
  const factores = _normalizar_factores(factorTamanoRaza);
  const categoria = _resolver_categoria_tamano(pesoKg);
  const factor = factores[categoria.clave] ?? 1.0;

  const duracionConFactor = base * factor;
  const minutosPorTamano = duracionConFactor - base;

  const extrasTemperamento = { tranquilo: 0, jugueton: 0, ansioso: 10, otro: 5, agresivo: 15 };
  const tempKey = (temperamento || "").toString().trim().toLowerCase();
  const extraTemp = extrasTemperamento[tempKey] ?? 0;

  const duracionConExtras = duracionConFactor + extraTemp;
  const duracionFinal = _ceil15(duracionConExtras);

  return {
    duracionBase: base,
    categoriaLabel: categoria.label,
    categoria: categoria.clave,
    factor: factor,
    minutosPorTamano: Math.round(minutosPorTamano * 10) / 10,
    temperamento: tempKey || null,
    extraTemperamento: extraTemp,
    duracionFinal,
  };
}

export function calcularDuracionSimple(duracionBase, pesoKg, temperamento, factorTamanoRaza) {
  return calcularDesglose(duracionBase, pesoKg, temperamento, factorTamanoRaza).duracionFinal;
}

// Backwards-compatible export used elsewhere in the UI
export function calcularDuracion(duracionBase, pesoKg, temperamento, factorTamanoRaza) {
  return calcularDuracionSimple(duracionBase, pesoKg, temperamento, factorTamanoRaza);
}
