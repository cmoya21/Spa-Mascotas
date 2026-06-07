import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import useAuth from "../hooks/useAuth";

export default function DashboardRedirect() {
  const { usuario } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!usuario?.rol) return;
    if (usuario.rol === "Admin") navigate("/admin/dashboard");
    if (usuario.rol === "Recepcion") navigate("/recepcion/agenda");
    if (usuario.rol === "Groomer") navigate("/groomers/agenda");
    if (usuario.rol === "Cliente") navigate("/cliente/vista");
  }, [usuario, navigate]);

  return null;
}
