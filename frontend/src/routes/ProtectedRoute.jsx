import { Navigate } from "react-router-dom";

import useAuth from "../hooks/useAuth";
import LoadingSpinner from "../components/shared/LoadingSpinner";
import AppLayout from "../components/layout/AppLayout";

export default function ProtectedRoute({ roles = [], children }) {
  const { isLoading, isAuthenticated, usuario } = useAuth();

  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (roles.length && !roles.includes(usuario?.rol)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
}
