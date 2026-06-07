import { useEffect, useState } from "react";

import { apiGetSlotsDisponibles } from "../../api/agendaApi.js";

function getColor(restante, max) {
  if (!max) return "#2f855a";
  const usageRatio = 1 - restante / max;
  if (usageRatio >= 1) return "#c53030";
  if (usageRatio >= 0.7) return "#dd6b20";
  return "#2f855a";
}

export default function IndicadorCapacidad({ groomer_id, fecha, duracion_min }) {
  const [capacidad, setCapacidad] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!groomer_id || !fecha || !duracion_min) {
      setCapacidad(null);
      return undefined;
    }

    const load = async () => {
      setError("");
      try {
        const data = await apiGetSlotsDisponibles({ groomer_id, fecha, duracion_min });
        if (!active) return;
        setCapacidad(data.capacidad_diaria || null);
      } catch {
        if (active) setError("No se pudo leer la capacidad del groomer.");
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [groomer_id, fecha, duracion_min]);

  if (!groomer_id || !fecha || !duracion_min) {
    return null;
  }

  const max = capacidad?.max || 0;
  const usada = capacidad?.usada || 0;
  const restante = capacidad?.restante ?? Math.max(max - usada, 0);
  const ratio = max ? usada / max : 0;
  const color = getColor(restante, max);
  const lleno = max > 0 && restante <= 0;

  return (
    <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.04)", marginTop: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <strong>Capacidad del groomer</strong>
        {lleno ? (
          <span style={{ background: "#c53030", color: "white", borderRadius: 999, padding: "4px 10px", fontSize: 12 }}>
            Lleno
          </span>
        ) : null}
      </div>
      {error ? <div style={{ color: "#f6ad55", marginTop: 8 }}>{error}</div> : null}
      <div style={{ marginTop: 10, background: "rgba(255,255,255,0.08)", borderRadius: 999, height: 10, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(ratio * 100, 100)}%`, height: "100%", background: color }} />
      </div>
      <div style={{ marginTop: 8, color: "rgba(255,255,255,0.8)" }}>
        {usada} / {max} servicios
      </div>
    </div>
  );
}
