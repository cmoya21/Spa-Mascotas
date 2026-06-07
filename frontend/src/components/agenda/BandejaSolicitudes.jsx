import { useEffect, useMemo, useState } from "react";

import { apiActualizarEstadoCita, apiConfirmarCita, apiListCitas, apiReprogramarCita } from "../../api/agendaApi";
import { apiListGroomersActivos } from "../../api/adminApi";

const formatDateTime = (value) => {
  if (!value) return "-";
  return new Date(value).toLocaleString();
};

export default function BandejaSolicitudes() {
  const [solicitudes, setSolicitudes] = useState([]);
  const [groomers, setGroomers] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [lastRefresh, setLastRefresh] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [processingId, setProcessingId] = useState(null);
  const [assignments, setAssignments] = useState({});

  const loadGroomers = async () => {
    const data = await apiListGroomersActivos();
    setGroomers(data.groomers || []);
  };

  const loadSolicitudes = async () => {
    const data = await apiListCitas({ estado: "agendada" });
    const items = data.citas || [];
    setSolicitudes(items);
    setAssignments((prev) => {
      const next = { ...prev };
      items.forEach((cita) => {
        if (next[cita.id] === undefined) {
          next[cita.id] = String(cita.groomer?.id || cita.groomer_id || "");
        }
      });
      return next;
    });
    setLastRefresh(new Date());
  };

  useEffect(() => {
    let mounted = true;
    const bootstrap = async () => {
      try {
        await Promise.all([loadGroomers(), loadSolicitudes()]);
      } catch (loadError) {
        if (mounted) setError("No se pudieron cargar solicitudes.");
      }
    };

    bootstrap();
    const timer = setInterval(() => {
      loadSolicitudes().catch(() => undefined);
    }, 60000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const pendientes = useMemo(() => solicitudes.length, [solicitudes]);

  const handleConfirmar = async (cita) => {
    setError("");
    setSuccess("");
    setProcessingId(cita.id);
    try {
      const groomerSeleccionado = assignments[cita.id];
      if (groomerSeleccionado && String(groomerSeleccionado) !== String(cita.groomer?.id || cita.groomer_id || "")) {
        await apiReprogramarCita(cita.id, {
          groomer_id: Number(groomerSeleccionado),
          fecha_hora_inicio: cita.fecha_hora_inicio,
        });
      }
      await apiConfirmarCita(cita.id);
      setSuccess("Solicitud confirmada.");
      await loadSolicitudes();
    } catch (confirmError) {
      setError("No se pudo confirmar la solicitud.");
    } finally {
      setProcessingId(null);
    }
  };

  const openReject = (cita) => {
    setRejectTarget(cita);
    setRejectReason("");
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    setError("");
    setSuccess("");
    setProcessingId(rejectTarget.id);
    try {
      await apiActualizarEstadoCita(rejectTarget.id, {
        estado: "rechazada",
        motivo_rechazo: rejectReason,
      });
      setSuccess("Solicitud rechazada.");
      setRejectTarget(null);
      setRejectReason("");
      await loadSolicitudes();
    } catch (rejectError) {
      setError("No se pudo rechazar la solicitud.");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <section className="agenda-card agenda-wide">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p className="calendar-kicker">Bandeja operativa</p>
          <h3 style={{ marginBottom: 8 }}>Solicitudes pendientes</h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div style={{ padding: "10px 14px", borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <strong>{pendientes}</strong> pendientes
            </div>
            <div style={{ padding: "10px 14px", borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              {groomers.length} groomers activos
            </div>
            <div style={{ padding: "10px 14px", borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              {lastRefresh ? `Actualizado ${lastRefresh.toLocaleTimeString()}` : "Sin refrescar"}
            </div>
          </div>
        </div>
        <div style={{ color: "rgba(255,255,255,0.68)", maxWidth: 360 }}>
          Acepta, reasigna o rechaza solicitudes sin salir de la bandeja. El refresco se ejecuta cada 60 segundos.
        </div>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}
      {success ? <div className="alert alert-success" style={{ marginTop: 16 }}>{success}</div> : null}

      {!solicitudes.length ? (
        <div className="admin-empty" style={{ marginTop: 18 }}>No hay solicitudes pendientes.</div>
      ) : (
        <div className="admin-table" style={{ marginTop: 18 }}>
          {solicitudes.map((cita) => (
            <div key={cita.id} className="admin-row" style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr auto", gap: 12, alignItems: "center" }}>
              <div>
                <strong>{cita.mascota?.nombre || "Mascota"}</strong>
                <div style={{ color: "rgba(255,255,255,0.72)", fontSize: 13 }}>{cita.cliente?.nombre || "Cliente"}</div>
                <div style={{ color: "rgba(255,255,255,0.58)", fontSize: 12, marginTop: 4 }}>{cita.servicio?.nombre || "Servicio"}</div>
              </div>
              <div>
                <div>{formatDateTime(cita.fecha_hora_inicio)}</div>
                <div style={{ color: "rgba(255,255,255,0.58)", fontSize: 12, marginTop: 4 }}>{cita.duracion_estimada || "-"} min</div>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "rgba(255,255,255,0.68)", marginBottom: 6 }}>Groomer asignado</label>
                <select
                  value={assignments[cita.id] || ""}
                  onChange={(event) => setAssignments((prev) => ({ ...prev, [cita.id]: event.target.value }))}
                >
                  <option value="">Autoasignar</option>
                  {groomers.map((groomer) => (
                    <option key={groomer.id} value={groomer.id}>
                      {groomer.nombre} {groomer.apellido || ""}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <button type="button" className="link-button" onClick={() => handleConfirmar(cita)} disabled={processingId === cita.id}>
                  Confirmar
                </button>
                <button type="button" className="link-button" onClick={() => openReject(cita)} disabled={processingId === cita.id}>
                  Rechazar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {rejectTarget ? (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ width: "min(620px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Rechazo de solicitud</p>
                <h4 style={{ margin: 0 }}>{rejectTarget.mascota?.nombre || "Mascota"}</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setRejectTarget(null)}>Cerrar</button>
            </div>
            <label>
              Motivo
              <textarea rows={4} value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} />
            </label>
            <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button type="button" className="primary-button" onClick={handleReject} disabled={processingId === rejectTarget.id}>
                Confirmar rechazo
              </button>
              <button type="button" className="secondary-button" onClick={() => setRejectTarget(null)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
