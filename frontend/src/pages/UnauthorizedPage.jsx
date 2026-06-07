import { useNavigate } from "react-router-dom";

import Button from "../components/shared/Button";
import useAuth from "../hooks/useAuth";

const HOME_BY_ROLE = {
  Admin: "/admin/dashboard",
  Recepcion: "/agenda",
  Groomer: "/groomers/agenda",
  Cliente: "/cliente"
};

export default function UnauthorizedPage() {
  const navigate = useNavigate();
  const { usuario } = useAuth();

  const home = HOME_BY_ROLE[usuario?.rol] || "/redirect";

  return (
    <div style={{ minHeight: "70vh", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ maxWidth: 640, width: "100%", padding: 32, borderRadius: 24, background: "rgba(20,20,24,0.92)", color: "#fff", boxShadow: "0 30px 80px rgba(0,0,0,0.35)" }}>
        <div style={{ fontSize: 44, marginBottom: 12 }}>⛔</div>
        <h2 style={{ margin: 0, fontSize: 32 }}>No autorizado</h2>
        <p style={{ marginTop: 12, color: "rgba(255,255,255,0.8)", lineHeight: 1.6 }}>
          No tienes permiso para acceder a esta página.
        </p>
        <div style={{ marginTop: 24 }}>
          <Button onClick={() => navigate(home)}>Volver al inicio</Button>
        </div>
      </div>
    </div>
  );
}