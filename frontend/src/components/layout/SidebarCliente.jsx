export default function SidebarCliente() {
  return (
    <aside className="page-sidebar">
      <div className="sidebar-title">Cliente</div>
      <a className="ghost-button" href="/cliente">🏠 Inicio</a>
      <a className="ghost-button" href="/cliente/mascotas">🐾 Mis mascotas</a>
      <a className="ghost-button" href="/cliente/nueva-cita">📅 Solicitar cita</a>
      <a className="ghost-button" href="/cliente/citas">📋 Mis citas</a>
      <a className="ghost-button" href="/cliente/historial">📜 Historial</a>
      <a className="ghost-button" href="/tienda">🛍️ Catálogo</a>
      <a className="ghost-button" href="/cliente/perfil">👤 Mi perfil</a>
      <a className="ghost-button" href="/login">Volver al login</a>
    </aside>
  );
}
