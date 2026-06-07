import { useState } from "react";
import { useNavigate } from "react-router-dom";
import CampanaNotificaciones from "../shared/CampanaNotificaciones";
import useAuth from "../../hooks/useAuth";

export default function TopBar() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 24px", borderBottom: "1px solid rgba(255,255,255,0.04)", background: "#0f1724" }}>
      <div style={{ fontSize: 18 }}>{document.title || "Pet Spa"}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <CampanaNotificaciones />
        <div style={{ position: "relative" }}>
          <button className="ghost-button" onClick={() => setOpen((s) => !s)}>
            {usuario?.nombre?.[0] || usuario?.email?.[0] || "U"}
          </button>
          {open && (
            <div style={{ position: "absolute", right: 0, top: "110%", background: "#111827", border: "1px solid rgba(255,255,255,0.04)", padding: 8, borderRadius: 6 }}>
              <button className="link-button" onClick={() => navigate("/cliente/perfil")}>Mi perfil</button>
              {(usuario?.rol === "Admin" || usuario?.rol === "Recepcion") && (
                <button className="link-button" onClick={() => navigate("/setup-2fa")}>Configurar 2FA</button>
              )}
              <button className="link-button" onClick={handleLogout}>Cerrar sesión</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
