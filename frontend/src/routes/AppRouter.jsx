import { BrowserRouter, Route, Routes } from "react-router-dom";

import ActivatePage from "../pages/ActivatePage";
import AdminDashboard from "../pages/AdminDashboard";
import AgendaPage from "../pages/AgendaPage";
import BandejaSolicitudes from "../components/agenda/BandejaSolicitudes.jsx";
import CierreCaja from "../components/cobros/CierreCaja.jsx";
import ClienteVista from "../pages/ClienteVista";
import DashboardRedirect from "../pages/DashboardRedirect";
import ForgotPasswordPage from "../pages/ForgotPasswordPage";
import LoginPage from "../pages/LoginPage";
import GestionServicios from "../pages/GestionServicios";
import UnauthorizedPage from "../pages/UnauthorizedPage";
import OAuthGoogleCallback from "../pages/OAuthGoogleCallback";
import RegisterPage from "../pages/RegisterPage";
import ReportesPage from "../pages/ReportesPage";
import ResetPasswordPage from "../pages/ResetPasswordPage";
import FichaTecnica from "../pages/FichaTecnica";
import PanelDisponibilidad from "../pages/PanelDisponibilidad";
import CobrosPage from "../pages/CobrosPage";
import GestionPromocionesPage from "../pages/GestionPromocionesPage.jsx";
import GestionUsuariosPage from "../pages/admin/GestionUsuariosPage.jsx";
import PanelAlertas from "../pages/admin/PanelAlertas.jsx";
import DashboardCliente from "../pages/DashboardCliente";
import Tienda from "../pages/Tienda";
import AgendaPersonal from "../pages/AgendaPersonal";
import FichasActivasPage from "../pages/groomer/FichasActivasPage.jsx";
import LogSalidaGroomer from "../pages/groomer/LogSalidaGroomer.jsx";
import LogSalidaAdmin from "../pages/admin/LogSalidaAdmin.jsx";
import VisualizadorMerma from "../pages/admin/VisualizadorMerma.jsx";
import PanelNotificacionesAdmin from "../pages/admin/PanelNotificacionesAdmin.jsx";
import Setup2FAPage from "../pages/Setup2FAPage.jsx";
import ProtectedRoute from "./ProtectedRoute";
import { Navigate } from "react-router-dom";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/activar" element={<ActivatePage />} />
        <Route path="/oauth/google" element={<OAuthGoogleCallback />} />
        <Route path="/redirect" element={<DashboardRedirect />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/no-autorizado" element={<UnauthorizedPage />} />

        <Route
          path="/agenda"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <AgendaPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cobros"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <CobrosPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alertas"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <PanelAlertas />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alertas-inventario"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <PanelAlertas />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cierre-caja"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <CierreCaja />
            </ProtectedRoute>
          }
        />
        <Route
          path="/promociones"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <GestionPromocionesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/setup-2fa"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <Setup2FAPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/usuarios"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <GestionUsuariosPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/solicitudes"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <BandejaSolicitudes />
            </ProtectedRoute>
          }
        />
        <Route
          path="/disponibilidad"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <PanelDisponibilidad />
            </ProtectedRoute>
          }
        />
        <Route
          path="/servicios"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <GestionServicios />
            </ProtectedRoute>
          }
        />
        <Route
          path="/groomers/agenda"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <AgendaPersonal />
            </ProtectedRoute>
          }
        />
        <Route
          path="/groomers/fichas"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <FichasActivasPage />
            </ProtectedRoute>
          }
        />
        <Route path="/groomer/mis-citas" element={<Navigate to="/groomers/agenda" replace />} />
        <Route
          path="/cliente"
          element={
            <ProtectedRoute roles={["Cliente"]}>
              <DashboardCliente />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tienda"
          element={
            <ProtectedRoute roles={["Cliente"]}>
              <Tienda />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reportes"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <ReportesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/reportes"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <ReportesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/servicios"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <GestionServicios />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recepcion/agenda"
          element={
            <ProtectedRoute roles={["Recepcion"]}>
              <AgendaPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/groomer/log-salida-insumos"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <LogSalidaGroomer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/groomer/ficha/:citaId"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <FichaTecnica />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fichas/nueva"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <FichaTecnica />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fichas/:fichaId"
          element={
            <ProtectedRoute roles={["Groomer"]}>
              <FichaTecnica />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/log-salida-insumos"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <LogSalidaAdmin />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/mermas-insumos"
          element={
            <ProtectedRoute roles={["Admin"]}>
              <VisualizadorMerma />
            </ProtectedRoute>
          }
        />
        <Route
          path="/notificaciones"
          element={
            <ProtectedRoute roles={["Admin", "Recepcion"]}>
              <PanelNotificacionesAdmin />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cliente/vista"
          element={
            <ProtectedRoute roles={["Cliente"]}>
              <ClienteVista />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<LoginPage />} />
      </Routes>
    </BrowserRouter>
  );
}
