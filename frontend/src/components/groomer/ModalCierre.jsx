import { useEffect, useState } from "react";
import Button from "../shared/Button";
import { apiCerrarFicha } from "../../api/groomerApi.js";

export default function ModalCierre({ ficha, onCerrado, onCancelar }) {
  const [form, setForm] = useState({ estado_final: "", observaciones_final: "", duracion_real: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ficha) return;
    if (!form.duracion_real && ficha.cita?.servicio?.duracion_base_minutos) {
      setForm((c) => ({ ...c, duracion_real: String(ficha.cita.servicio.duracion_base_minutos) }));
    }
  }, [ficha]);

  const confirmar = async () => {
    setError("");
    if (!form.estado_final || (form.estado_final || "").trim().length < 10) {
      setError("Describe brevemente el estado final (mínimo 10 caracteres)");
      return;
    }
    setLoading(true);
    try {
      await apiCerrarFicha(ficha.id, {
        estado_final: form.estado_final,
        observaciones_final: form.observaciones_final,
        duracion_real: form.duracion_real ? Number(form.duracion_real) : undefined,
        recomendaciones: form.recomendaciones,
      });
      if (onCerrado) onCerrado();
    } catch (err) {
      setError(err?.response?.data?.mensaje || err?.response?.data?.message || "No se pudo cerrar la ficha.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.65)", display: "grid", placeItems: "center", padding: 16, zIndex: 50 }}>
      <div style={{ width: "min(640px, 100%)", borderRadius: 24, padding: 20, background: "#101722", border: "1px solid rgba(255,255,255,0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
          <div>
            <h3 style={{ margin: 0 }}>¿Cerrar el servicio de {ficha?.cita?.mascota?.nombre || "la mascota"}?</h3>
            <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>
              Verifica checklist, fotos e insumos antes de confirmar.
            </p>
          </div>
          <button type="button" className="ghost-button" onClick={onCancelar}>Cerrar</button>
        </div>

        <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
          {error ? <div className="alert alert-error">{error}</div> : null}
          <label className="input-field">
            <span>Estado final</span>
            <div className="input-wrapper">
              <textarea
                rows={4}
                value={form.estado_final}
                onChange={(e) => setForm((c) => ({ ...c, estado_final: e.target.value }))}
                style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
              />
            </div>
          </label>

          <label className="input-field">
            <span>Recomendaciones (opcional)</span>
            <div className="input-wrapper">
              <textarea
                rows={3}
                value={form.recomendaciones || ""}
                onChange={(e) => setForm((c) => ({ ...c, recomendaciones: e.target.value }))}
                style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
              />
            </div>
          </label>

          <InputDuracion value={form.duracion_real} onChange={(v) => setForm((c) => ({ ...c, duracion_real: v }))} />

          <label className="input-field">
            <span>Observaciones finales</span>
            <div className="input-wrapper">
              <textarea
                rows={3}
                value={form.observaciones_final}
                onChange={(e) => setForm((c) => ({ ...c, observaciones_final: e.target.value }))}
                style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
              />
            </div>
          </label>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button type="button" className="ghost-button" onClick={onCancelar} disabled={loading}>Cancelar</button>
            <Button type="button" onClick={confirmar} disabled={loading}>
              {loading ? "Cerrando..." : "Confirmar cierre"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function InputDuracion({ value, onChange }) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <label className="input-field" style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{ minWidth: 140 }}>Duración real (min)</span>
        <input type="number" value={value || ""} onChange={(e) => onChange(e.target.value)} style={{ flex: 1 }} />
      </label>
    </div>
  );
}
