import { useEffect, useState } from "react";
import { apiListCitas } from "../../api/agendaApi";
import { apiGetAlertasInventarioActivos } from "../../api/alertasApi";

export default function SidebarAdmin() {
  const [solicitudes, setSolicitudes] = useState(0);
  const [alertas, setAlertas] = useState(0);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiListCitas({ estado: "agendada" });
        setSolicitudes((data.citas || []).length);
      } catch (_) {
        setSolicitudes(0);
      }
      try {
        const d2 = await apiGetAlertasInventarioActivos();
        setAlertas(d2.total_criticos || d2.total || 0);
      } catch (_) {
        setAlertas(0);
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside className="page-sidebar">
      <div className="sidebar-title">Administración</div>
      <a className="ghost-button" href="/admin/dashboard">📊 Dashboard</a>
      <a className="ghost-button" href="/agenda">🗓 Agenda</a>
      <a className="ghost-button" href="/solicitudes">📋 Solicitudes {solicitudes > 0 ? `(${solicitudes})` : ""}</a>
      <a className="ghost-button" href="/cobros">💰 Cobros</a>
      <a className="ghost-button" href="/cierre-caja">🏦 Cierre de caja</a>
      <a className="ghost-button" href="/disponibilidad">⚙️ Disponibilidad</a>
      <a className="ghost-button" href="/servicios">✂️ Servicios</a>
      <a className="ghost-button" href="/admin/productos">📦 Productos</a>
      <a className="ghost-button" href="/admin/promociones">🎁 Promociones</a>
      <a className="ghost-button" href="/admin/usuarios">👥 Usuarios</a>
      <a className="ghost-button" href="/alertas">🔔 Alertas {alertas > 0 ? `(${alertas})` : ""}</a>
      <a className="ghost-button" href="/reportes">📈 Reportes</a>
      <a className="ghost-button" href="/admin/notificaciones">🔔 Notificaciones</a>
      <a className="ghost-button" href="/login">Volver al login</a>
    </aside>
  );
}
