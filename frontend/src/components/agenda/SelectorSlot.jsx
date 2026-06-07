import { useEffect, useMemo, useState } from "react";

import { apiGetSlotsDisponibles, apiValidarCita } from "../../api/agendaApi.js";

const DAY_GROUPS = [
  { key: "manana", label: "Mañana", start: 9, end: 12 },
  { key: "tarde", label: "Tarde", start: 12, end: 16 },
  { key: "noche", label: "Noche", start: 16, end: 19 },
];

function buildIsoDate(fecha, hora) {
  return `${fecha}T${hora}:00`;
}

function slotClass(slot) {
  if (slot.disponible) return "available";
  if (slot.motivo === "Bloqueado") return "blocked";
  if (slot.motivo === "Ocupado") return "busy";
  if ((slot.motivo || "").includes("Sin espacio")) return "tight";
  return "disabled";
}

export default function SelectorSlot({
  groomer_id,
  fecha,
  duracion_min,
  onSlotSelect,
  servicio_id,
  mascota_id,
}) {
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!groomer_id || !fecha || !duracion_min) {
      setSlots([]);
      setError("");
      return undefined;
    }

    const loadSlots = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await apiGetSlotsDisponibles({ groomer_id, fecha, duracion_min });
        if (!active) return;
        setSlots(data.slots || []);
      } catch (err) {
        if (active) {
          setError("No se pudieron cargar los slots disponibles.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadSlots();
    return () => {
      active = false;
    };
  }, [groomer_id, fecha, duracion_min]);

  const groupedSlots = useMemo(() => {
    const groups = Object.fromEntries(DAY_GROUPS.map((group) => [group.key, []]));
    slots.forEach((slot) => {
      const hour = Number(String(slot.hora_inicio).split(":")[0]);
      const group = DAY_GROUPS.find((item) => hour >= item.start && hour < item.end) || DAY_GROUPS[2];
      groups[group.key].push(slot);
    });
    return groups;
  }, [slots]);

  const handleSelect = async (slot) => {
    if (!slot.disponible) return;
    const payload = { hora_inicio: slot.hora_inicio, hora_fin: slot.hora_fin, duracion_ajustada: duracion_min };
    if (!servicio_id || !mascota_id) {
      onSlotSelect?.(payload);
      return;
    }

    try {
      const validacion = await apiValidarCita({
        groomer_id: Number(groomer_id),
        servicio_id: Number(servicio_id),
        mascota_id: Number(mascota_id),
        fecha_hora_inicio: buildIsoDate(fecha, slot.hora_inicio),
      });
      if (!validacion.valido) {
        setError((validacion.errores || ["No se pudo validar el slot."]).join(". "));
        return;
      }
      onSlotSelect?.({
        hora_inicio: validacion.fecha_hora_inicio,
        hora_fin: validacion.fecha_hora_fin,
        duracion_ajustada: validacion.duracion_ajustada_min,
      });
    } catch (err) {
      const data = err?.response?.data;
      const detalles = data?.errores || data?.details?.errores;
      setError((detalles || [data?.message || "No se pudo validar el slot."]).join(". "));
    }
  };

  if (!groomer_id || !fecha || !duracion_min) {
    return <div className="admin-empty">Selecciona groomer, fecha y duración.</div>;
  }

  return (
    <div className="slot-selector" style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div>
          <h4 style={{ margin: 0 }}>Selector de slots</h4>
          <p style={{ margin: "4px 0 0", color: "rgba(255,255,255,0.7)" }}>
            {duracion_min} min para {fecha}
          </p>
        </div>
        {loading ? <span className="pill">Cargando...</span> : null}
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div> : null}

      <div style={{ display: "grid", gap: 14, marginTop: 14 }}>
        {DAY_GROUPS.map((group) => (
          <div key={group.key} style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.03)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <strong>{group.label}</strong>
              <span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{group.start}:00 - {group.end}:00</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 10 }}>
              {(groupedSlots[group.key] || []).map((slot) => {
                const kind = slotClass(slot);
                const available = slot.disponible;
                const styleMap = {
                  available: { background: "#dff8e7", color: "#10351d", border: "1px solid #95d8ad" },
                  blocked: { background: "#d9d9df", color: "#444", border: "1px dashed #999" },
                  busy: { background: "#d9d9df", color: "#444", border: "1px solid #999" },
                  tight: { background: "#fff4cc", color: "#6a4d00", border: "1px solid #e7c75f" },
                  disabled: { background: "#e7e7e7", color: "#666", border: "1px solid #bbb" },
                };
                return (
                  <button
                    key={`${slot.hora_inicio}-${slot.hora_fin}`}
                    type="button"
                    title={slot.motivo || (available ? "Disponible" : "No disponible")}
                    disabled={!available}
                    onClick={() => handleSelect(slot)}
                    style={{
                      ...styleMap[kind],
                      borderRadius: 14,
                      padding: 12,
                      textAlign: "left",
                      cursor: available ? "pointer" : "not-allowed",
                      opacity: available ? 1 : 0.9,
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{slot.hora_inicio}</div>
                    <div style={{ fontSize: 13 }}>{slot.hora_fin}</div>
                    <div style={{ fontSize: 12, marginTop: 6 }}>
                      {available ? "Disponible" : slot.motivo || "No disponible"}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
