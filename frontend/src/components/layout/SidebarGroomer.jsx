export default function SidebarGroomer() {
  return (
    <aside className="page-sidebar">
      <div className="sidebar-title">Groomer</div>
      <a className="ghost-button" href="/groomers/agenda">🗓 Mi agenda</a>
      <a className="ghost-button" href="/groomers/fichas">📋 Fichas activas</a>
      <a className="ghost-button" href="/groomer/log-salida-insumos">📦 Log de insumos</a>
      <a className="ghost-button" href="/login">Volver al login</a>
    </aside>
  );
}
