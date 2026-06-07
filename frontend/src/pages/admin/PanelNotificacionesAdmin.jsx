import { useEffect, useMemo, useState } from "react";

import Alert from "../../components/shared/Alert";
import Button from "../../components/shared/Button";
import InputField from "../../components/shared/InputField";
import { apiGetNotificacionesAdmin, apiGetStatsNotificaciones, apiReenviarNotificacion } from "../../api/notificacionesApi.js";

const estados = ["", "pendiente", "enviado", "fallido"];
const tipos = ["", "solicitud_revision", "confirmacion", "recordatorio_24h", "recordatorio_2h", "listo_recoger", "pago_registrado", "encuesta", "bajo_stock"];

const badgeStyle = (estado) => {
  if (estado === "fallido") return { background: "rgba(239,68,68,0.18)", color: "#fecaca" };
  if (estado === "enviado") return { background: "rgba(34,197,94,0.16)", color: "#86efac" };
  return { background: "rgba(245,158,11,0.16)", color: "#fcd34d" };
};

export default function PanelNotificacionesAdmin() {
  const [stats, setStats] = useState(null);
  const [notificaciones, setNotificaciones] = useState([]);
  const [estado, setEstado] = useState("fallido");
  const [tipo, setTipo] = useState("");
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [statsData, listData] = await Promise.all([
        apiGetStatsNotificaciones(),
        apiGetNotificacionesAdmin({ estado: estado || undefined, tipo: tipo || undefined, limit }),
      ]);
      setStats(statsData);
      setNotificaciones(listData.notificaciones || []);
    } catch {
      setError("No se pudieron cargar las notificaciones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [estado, tipo, limit]);

  const cards = useMemo(
    () => [
      { label: "Pendientes", value: stats?.pendientes ?? 0, tone: "#f59e0b" },
      { label: "Enviadas", value: stats?.enviadas ?? 0, tone: "#22c55e" },
      { label: "Fallidas", value: stats?.fallidas ?? 0, tone: "#ef4444" },
      { label: "Listo para recoger", value: stats?.listo_recoger_enviadas ?? 0, tone: "#38bdf8" },
    ],
    [stats]
  );

  const handleReenviar = async (notifId) => {
    try {
      await apiReenviarNotificacion(notifId);
      await load();
    } catch {
      setError("No se pudo reenviar la notificación.");
    }
  };

  return (
    <section className="agenda-card agenda-wide">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
        <div>
          <p className="calendar-kicker">Notificaciones automáticas</p>
          <h3 style={{ marginBottom: 6 }}>Centro de alertas y envíos</h3>
          <p style={{ margin: 0, color: "rgba(255,255,255,0.7)" }}>Supervisa recordatorios, listo para recoger y bajo stock.</p>
        </div>
        <Button onClick={load}>{loading ? "Actualizando..." : "Refrescar"}</Button>
      </div>

      {error ? <Alert message={error} /> : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginTop: 18 }}>
        {cards.map((item) => (
          <article key={item.label} style={{ borderRadius: 18, padding: 16, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ color: "rgba(255,255,255,0.68)", marginBottom: 6 }}>{item.label}</div>
            <div style={{ fontSize: 34, fontWeight: 800, color: item.tone }}>{item.value}</div>
          </article>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 14, marginTop: 22 }}>
        <div className="input-field">
          <label>Estado</label>
          <div className="input-wrapper">
            <select className="select-field" value={estado} onChange={(event) => setEstado(event.target.value)}>
              {estados.map((item) => (
                <option key={item || "todos-estados"} value={item}>
                  {item ? item : "Todos"}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="input-field">
          <label>Tipo</label>
          <div className="input-wrapper">
            <select className="select-field" value={tipo} onChange={(event) => setTipo(event.target.value)}>
              {tipos.map((item) => (
                <option key={item || "todos-tipos"} value={item}>
                  {item ? item : "Todos"}
                </option>
              ))}
            </select>
          </div>
        </div>
        <InputField label="Límite" type="number" value={String(limit)} onChange={(value) => setLimit(Number(value) || 50)} />
      </div>

      <div style={{ marginTop: 24 }}>
        <h3>Tabla de notificaciones</h3>
        <div className="admin-table" style={{ marginTop: 12 }}>
          <div className="admin-row admin-row-head">
            <span>ID</span>
            <span>Tipo</span>
            <span>Canal</span>
            <span>Destino</span>
            <span>Estado</span>
            <span>Programado</span>
            <span>Enviado</span>
            <span>Acciones</span>
          </div>
          {notificaciones.map((item) => (
            <div key={item.id} className="admin-row">
              <span>{item.id}</span>
              <span>{item.tipo_evento}</span>
              <span>{item.tipo_canal}</span>
              <span style={{ wordBreak: "break-word" }}>{item.destino || "-"}</span>
              <span>
                <span style={{ borderRadius: 999, padding: "4px 10px", fontSize: 12, fontWeight: 700, ...badgeStyle(item.estado) }}>
                  {item.estado}
                </span>
              </span>
              <span>{item.fecha_programacion ? new Date(item.fecha_programacion).toLocaleString() : "-"}</span>
              <span>{item.fecha_envio ? new Date(item.fecha_envio).toLocaleString() : "-"}</span>
              <span>
                {item.estado === "fallido" ? (
                  <button type="button" className="link-button" onClick={() => handleReenviar(item.id)}>
                    Reenviar
                  </button>
                ) : (
                  "-"
                )}
              </span>
            </div>
          ))}
          {!notificaciones.length ? <div className="admin-empty">Sin notificaciones para mostrar.</div> : null}
        </div>
      </div>

      <div style={{ marginTop: 26 }}>
        <h3>Bajo stock pendientes</h3>
        <p style={{ marginTop: 6, color: "rgba(255,255,255,0.68)" }}>Filtro activo: tipo = bajo_stock.</p>
      </div>
    </section>
  );
}
