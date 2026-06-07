import { useEffect, useMemo, useRef, useState } from "react";

import { useAuthContext } from "../../context/AuthContext.jsx";
import { apiGetMisNotificaciones } from "../../api/clienteApi.js";
import { apiGetNotificacionesAdmin, apiReenviarNotificacion } from "../../api/notificacionesApi.js";

const iconos = {
  solicitud_revision: "📋",
  confirmacion: "✅",
  recordatorio_24h: "⏰",
  recordatorio_2h: "🔔",
  listo_recoger: "🎉",
  pago_registrado: "💰",
  encuesta: "⭐",
  bajo_stock: "⚠️",
};

const titulo = (item) => {
  const tipo = item?.tipo_evento || "notificacion";
  return tipo.replace(/_/g, " ");
};

const formatHora = (value) => {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("es-BO", { hour: "2-digit", minute: "2-digit" }).format(date);
};

export default function CampanaNotificaciones() {
  const { usuario } = useAuthContext();
  const [abierto, setAbierto] = useState(false);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef(null);

  const mode = useMemo(() => {
    if (usuario?.rol === "Admin" || usuario?.rol === "Recepcion") return "admin";
    if (usuario?.rol === "Cliente") return "cliente";
    return null;
  }, [usuario?.rol]);

  const loadItems = async () => {
    if (!mode) return;
    setLoading(true);
    setError("");
    try {
      if (mode === "admin") {
        const data = await apiGetNotificacionesAdmin({ estado: "fallido", limit: 20 });
        setItems(data.notificaciones || []);
      } else {
        const data = await apiGetMisNotificaciones();
        setItems(Array.isArray(data) ? data : data.notificaciones || []);
      }
    } catch {
      setError("No se pudieron cargar notificaciones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadItems();
    if (!mode) return undefined;
    const intervalId = setInterval(loadItems, 30 * 1000);
    return () => clearInterval(intervalId);
  }, [mode]);

  useEffect(() => {
    const handleOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setAbierto(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const badgeCount = useMemo(() => {
    if (!items.length) return 0;
    if (mode === "admin") return items.length;
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    return items.filter((item) => {
      const fecha = new Date(item.creado_en || item.fecha_programacion || 0).getTime();
      return fecha >= cutoff;
    }).length;
  }, [items, mode]);

  const handleReenviar = async (notifId) => {
    try {
      await apiReenviarNotificacion(notifId);
      await loadItems();
    } catch {
      setError("No se pudo reenviar la notificación.");
    }
  };

  if (!mode) return null;

  return (
    <div ref={wrapperRef} style={{ position: "relative", display: "inline-flex", justifyContent: "flex-end" }}>
      <button
        type="button"
        className="ghost-button"
        onClick={() => setAbierto((prev) => !prev)}
        style={{ minWidth: 54, position: "relative" }}
        aria-label="Notificaciones"
      >
        🔔
        {badgeCount > 0 ? (
          <span
            style={{
              position: "absolute",
              top: -6,
              right: -4,
              minWidth: 20,
              height: 20,
              borderRadius: 999,
              background: mode === "admin" ? "#ef4444" : "#f59e0b",
              color: "#fff",
              fontSize: 11,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 6px",
              fontWeight: 700,
            }}
          >
            {badgeCount}
          </span>
        ) : null}
      </button>

      {abierto ? (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 10px)",
            right: 0,
            width: 360,
            maxWidth: "calc(100vw - 24px)",
            borderRadius: 20,
            padding: 14,
            background: "rgba(15,23,42,0.98)",
            border: "1px solid rgba(255,255,255,0.12)",
            boxShadow: "0 20px 50px rgba(0,0,0,0.35)",
            zIndex: 30,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
            <strong>Notificaciones</strong>
            <button type="button" className="link-button" onClick={loadItems} disabled={loading}>
              {loading ? "Cargando..." : "Actualizar"}
            </button>
          </div>

          {error ? <div className="alert alert-error" style={{ marginBottom: 10 }}>{error}</div> : null}

          <div style={{ display: "grid", gap: 10, maxHeight: 420, overflowY: "auto" }}>
            {!items.length ? <div className="admin-empty">Sin notificaciones.</div> : null}
            {items.map((item) => (
              <article
                key={item.id}
                style={{
                  borderRadius: 16,
                  padding: 12,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                  <div style={{ display: "grid", gap: 4 }}>
                    <strong style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span>{iconos[item.tipo_evento] || "🔔"}</span>
                      <span>{titulo(item)}</span>
                    </strong>
                    <div style={{ color: "rgba(255,255,255,0.74)", fontSize: 13 }}>
                      {String(item.mensaje || "").slice(0, 96)}
                      {String(item.mensaje || "").length > 96 ? "..." : ""}
                    </div>
                    <div style={{ color: "rgba(255,255,255,0.56)", fontSize: 12 }}>
                      {formatHora(item.creado_en || item.fecha_programacion)}
                      {item.destino ? ` · ${item.destino}` : ""}
                    </div>
                  </div>
                  {mode === "admin" && item.estado === "fallido" ? (
                    <button type="button" className="link-button" onClick={() => handleReenviar(item.id)}>
                      Reenviar
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
