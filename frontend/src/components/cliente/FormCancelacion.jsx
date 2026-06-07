import { useMemo, useState } from "react";

import { useAuthContext } from "../../context/AuthContext.jsx";
import Button from "../shared/Button";

const MOTIVOS = [
  { value: "Problema de salud", label: "🏥 Problema de salud de la mascota" },
  { value: "Emergencia", label: "🚨 Emergencia personal" },
  { value: "Falta de tiempo", label: "⏰ Falta de tiempo" },
  { value: "Cambio de planes", label: "📅 Cambio de planes" },
  { value: "Otro", label: "💬 Otro motivo" },
];

const formatFecha = (value) => {
  if (!value) return "-";
  return new Intl.DateTimeFormat("es-BO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
};

const normalizeError = (data) => {
  if (!data) return { mensaje: "No se pudo cancelar la cita." };
  if (data.error === "cancelacion_anticipacion") return data;
  return {
    mensaje: data.mensaje || data.message || "No se pudo cancelar la cita.",
  };
};

export default function FormCancelacion({ cita, onCancelada, onCerrar }) {
  const { accessToken } = useAuthContext();
  const [motivo, setMotivo] = useState("");
  const [motivoExtra, setMotivoExtra] = useState("");
  const [aceptaPolitica, setAceptaPolitica] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [error, setError] = useState(null);

  const horasRestantes = useMemo(() => {
    if (!cita?.fecha_hora_inicio) return null;
    return (new Date(cita.fecha_hora_inicio) - new Date()) / (1000 * 60 * 60);
  }, [cita]);

  if (!cita) return null;

  const citaNombre = cita.mascota_nombre || cita.mascota || "Mascota";
  const servicioNombre = cita.servicio_nombre || cita.servicio || "Servicio";

  const bannerCorto = horasRestantes !== null && horasRestantes < 24;
  const bannerAviso = horasRestantes !== null && horasRestantes >= 24 && horasRestantes < 48;

  const handleCancelar = async () => {
    setCancelando(true);
    setError(null);
    try {
      const payload = {
        motivo_cancelacion: motivo === "Otro" ? motivoExtra.trim() : motivo.trim(),
        acepta_politica: aceptaPolitica,
      };
      const res = await fetch(`/api/clientes/me/citas/${cita.id}/cancelar`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(normalizeError(data));
        return;
      }
      onCancelada?.(data);
    } catch (e) {
      setError({ mensaje: "Error de conexión. Intenta de nuevo." });
    } finally {
      setCancelando(false);
    }
  };

  const formularioDeshabilitado = bannerCorto;
  const motivoFinalValido = motivo === "Otro" ? motivoExtra.trim() : motivo.trim();

  return (
    <div className="modal-backdrop" style={{ position: "fixed", inset: 0, background: "rgba(5, 8, 12, 0.65)", display: "grid", placeItems: "center", padding: 16, zIndex: 40 }}>
      <div className="modal-card" style={{ width: "min(620px, 100%)", borderRadius: 24, padding: 20, background: "#10161f", border: "1px solid rgba(255,255,255,0.08)", display: "grid", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
          <div>
            <h3 style={{ margin: 0 }}>Cancelar cita</h3>
            <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.7)" }}>
              Mascota: {citaNombre} · Servicio: {servicioNombre} · {formatFecha(cita.fecha_hora_inicio)}
            </p>
          </div>
          <button type="button" className="ghost-button" onClick={onCerrar}>Cerrar</button>
        </div>

        {bannerCorto ? (
          <div className="alert alert-error">
            ⚠ Esta cita es en {Math.max(0, Math.round(horasRestantes || 0))} horas. Por política, las cancelaciones requieren 24h de anticipación. Para cancelar, contacta directamente a recepción.
          </div>
        ) : bannerAviso ? (
          <div className="alert" style={{ background: "rgba(245, 158, 11, 0.15)", border: "1px solid rgba(245, 158, 11, 0.35)" }}>
            ⏰ Puedes cancelar esta cita (faltan {Math.max(0, Math.round(horasRestantes || 0))}h).
          </div>
        ) : null}

        <label className="input-field">
          <span>Motivo de cancelación *</span>
          <div className="input-wrapper">
            <select value={motivo} onChange={(event) => setMotivo(event.target.value)} disabled={formularioDeshabilitado}>
              <option value="">— Seleccionar motivo —</option>
              {MOTIVOS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </div>
        </label>

        {motivo === "Otro" ? (
          <label className="input-field">
            <span>Especifica el motivo</span>
            <div className="input-wrapper">
              <textarea
                value={motivoExtra}
                onChange={(event) => setMotivoExtra(event.target.value)}
                rows={3}
                disabled={formularioDeshabilitado}
                style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
              />
            </div>
          </label>
        ) : null}

        <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.84)" }}>
          📋 Política de cancelación del spa:
          <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
            <div>• Las citas deben cancelarse con al menos 24 horas de anticipación.</div>
            <div>• Cancelaciones tardías pueden estar sujetas a cargo parcial.</div>
            <div>• Para emergencias, contáctanos directamente.</div>
          </div>
          <label style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 12, opacity: formularioDeshabilitado ? 0.65 : 1 }}>
            <input type="checkbox" checked={aceptaPolitica} onChange={(event) => setAceptaPolitica(event.target.checked)} disabled={formularioDeshabilitado} />
            <span>He leído y acepto la política de cancelación</span>
          </label>
        </div>

        {error ? (
          <div className="alert alert-error">
            {error.error === "cancelacion_anticipacion"
              ? `${error.mensaje} ${error.contacto || ""}`.trim()
              : error.mensaje}
          </div>
        ) : null}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button type="button" className="ghost-button" onClick={onCerrar}>Volver</button>
          {!formularioDeshabilitado ? (
            <Button type="button" onClick={handleCancelar} disabled={cancelando || !motivoFinalValido || !aceptaPolitica}>
              {cancelando ? "Cancelando..." : "Confirmar cancelación"}
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
