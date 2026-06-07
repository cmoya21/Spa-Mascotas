import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiCrearEmpleado = (payload) =>
  apiClient.post("/api/admin/empleados", payload).then(unwrap);

export const apiListUsuarios = (rol) =>
  apiClient
    .get("/api/admin/usuarios", { params: rol ? { rol } : {} })
    .then(unwrap);

export const apiListClientes = () =>
  apiClient.get("/api/admin/clientes").then(unwrap);

export const apiActualizarEstadoUsuario = (usuarioId, activo) =>
  apiClient
    .patch(`/api/admin/usuarios/${usuarioId}/estado`, { activo })
    .then(unwrap);

export const apiListGroomers = () =>
  apiClient.get("/api/admin/groomers").then(unwrap);

export const apiListGroomersActivos = () =>
  apiClient.get("/api/groomers/activos").then(unwrap);
