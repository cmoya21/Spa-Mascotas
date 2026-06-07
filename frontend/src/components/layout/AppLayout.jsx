import { useMemo } from "react";
import { useAuthContext } from "../../context/AuthContext";
import TopBar from "./TopBar";
import SidebarAdmin from "./SidebarAdmin";
import SidebarRecepcion from "./SidebarRecepcion";
import SidebarGroomer from "./SidebarGroomer";
import SidebarCliente from "./SidebarCliente";

export default function AppLayout({ children }) {
  const { usuario } = useAuthContext();
  const rol = usuario?.rol;

  const Sidebar = useMemo(() => {
    if (rol === "Admin") return <SidebarAdmin />;
    if (rol === "Recepcion") return <SidebarRecepcion />;
    if (rol === "Groomer") return <SidebarGroomer />;
    return <SidebarCliente />;
  }, [rol]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {Sidebar}
      <main style={{ flex: 1, overflow: "auto" }}>
        <TopBar />
        <div style={{ padding: 24 }}>{children}</div>
      </main>
    </div>
  );
}
