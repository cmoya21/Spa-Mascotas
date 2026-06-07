import { useEffect, useMemo, useState } from "react";

import { apiGetDuracionEstimada } from "../../api/agendaApi.js";

const baseCards = {
  box: {
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 18,
    padding: 16,
    background: "linear-gradient(180deg, rgba(18,24,32,0.96), rgba(10,14,20,0.98))",
    color: "#f4f7fb",
    cursor: "pointer",
    transition: "transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease",
  },
};

function formatCurrency(value) {
  return new Intl.NumberFormat("es-BO", {
    style: "currency",
    currency: "BOB",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatDurationPreview(preview) {
  if (!preview) return null;
  const total = preview.duracion_total ?? preview.duracion_total_min ?? preview.total_minutos;
  const breakdown = preview;
  return {
    total,
    breakdown,
  };
}

export default function CatalogoServicios({
  servicios = [],
  mascotaId,
  selectedServicioId,
  onSelect,
}) {
  const [previews, setPreviews] = useState({});
  const [loadingIds, setLoadingIds] = useState([]);

  const selectedService = useMemo(
    () => servicios.find((servicio) => String(servicio.id) === String(selectedServicioId)),
    [servicios, selectedServicioId]
  );

  useEffect(() => {
    let active = true;

    if (!mascotaId) {
      setPreviews({});
      setLoadingIds([]);
      return undefined;
    }

    const fetchPreviews = async () => {
      const ids = servicios.map((servicio) => servicio.id);
      setLoadingIds(ids);
      try {
        const entries = await Promise.all(
          servicios.map(async (servicio) => {
            try {
              const data = await apiGetDuracionEstimada(servicio.id, mascotaId);
              return [servicio.id, formatDurationPreview(data?.duracion_estimada || data)];
            } catch {
              return [servicio.id, null];
            }
          })
        );
        if (!active) return;
        setPreviews(Object.fromEntries(entries.filter(([, value]) => value)));
      } finally {
        if (active) {
          setLoadingIds([]);
        }
      }
    };

    fetchPreviews();
    return () => {
      active = false;
    };
  }, [mascotaId, servicios]);

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "end", marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0, color: "#f4f7fb" }}>Catálogo de servicios</h3>
          <p style={{ margin: "6px 0 0", color: "rgba(244,247,251,0.72)" }}>
            Selecciona un servicio para continuar con la cita.
          </p>
        </div>
        {selectedService ? (
          <div style={{ color: "#cdd7e1", fontSize: 14 }}>
            Seleccionado: <strong style={{ color: "#ffffff" }}>{selectedService.nombre}</strong>
          </div>
        ) : null}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 14,
        }}
      >
        {servicios.map((servicio) => {
          const preview = previews[servicio.id];
          const isSelected = String(selectedServicioId) === String(servicio.id);
          const isLoading = loadingIds.includes(servicio.id);
          const checklistCount = servicio.checklist_items?.length || servicio.checklist_items_template?.length || 0;

          return (
            <button
              key={servicio.id}
              type="button"
              onClick={() => onSelect?.(servicio.id)}
              style={{
                ...baseCards.box,
                textAlign: "left",
                transform: isSelected ? "translateY(-2px)" : "none",
                border: isSelected ? "1px solid #5dd3a4" : baseCards.box.border,
                boxShadow: isSelected ? "0 14px 32px rgba(93, 211, 164, 0.16)" : "none",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
                <div>
                  <div style={{ fontSize: 12, letterSpacing: 0.8, textTransform: "uppercase", color: "#8de8c0" }}>
                    {servicio.activo ? "Activo" : "Inactivo"}
                  </div>
                  <h4 style={{ margin: "8px 0 6px", fontSize: 20 }}>{servicio.nombre}</h4>
                </div>
                <div
                  style={{
                    padding: "8px 10px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.08)",
                    fontWeight: 700,
                    fontSize: 13,
                  }}
                >
                  {servicio.duracion_base_minutos} min
                </div>
              </div>

              <p style={{ margin: "8px 0 12px", color: "rgba(244,247,251,0.8)", minHeight: 42 }}>
                {servicio.descripcion || "Sin descripcion registrada."}
              </p>

              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                <span style={{ padding: "6px 10px", borderRadius: 999, background: "rgba(255,255,255,0.08)" }}>
                  {formatCurrency(servicio.precio_base)}
                </span>
                <span style={{ padding: "6px 10px", borderRadius: 999, background: "rgba(255,255,255,0.08)" }}>
                  {checklistCount} checklist
                </span>
                <span style={{ padding: "6px 10px", borderRadius: 999, background: "rgba(255,255,255,0.08)" }}>
                  {servicio.consumo_insumos?.length || 0} insumos
                </span>
              </div>

              {mascotaId ? (
                <div style={{ padding: 12, borderRadius: 14, background: "rgba(255,255,255,0.05)" }}>
                  {isLoading && !preview ? (
                    <div style={{ color: "rgba(244,247,251,0.72)" }}>Calculando ajuste...</div>
                  ) : preview ? (
                    <>
                      <div style={{ fontWeight: 700, marginBottom: 4 }}>
                        Duracion estimada: {preview.total} min
                      </div>
                      <div style={{ color: "rgba(244,247,251,0.72)", fontSize: 13 }}>
                        Base {preview.breakdown.duracion_base ?? servicio.duracion_base_minutos} min
                        {preview.breakdown.factor_tamano ? ` · Tamano x${preview.breakdown.factor_tamano}` : ""}
                        {preview.breakdown.extra_temperamento ? ` · Temperamento +${preview.breakdown.extra_temperamento} min` : ""}
                        {preview.breakdown.categoria_tamano ? ` · ${preview.breakdown.categoria_tamano}` : ""}
                      </div>
                    </>
                  ) : (
                    <div style={{ color: "rgba(244,247,251,0.72)" }}>
                      Sin mascota seleccionada no hay ajuste de duracion.
                    </div>
                  )}
                </div>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
