import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListUsuarios = () => apiClient.get("/api/usuarios").then(unwrap);

export const apiCrearUsuario = (payload) => apiClient.post("/api/usuarios", payload).then(unwrap);

export const apiActualizarEstadoUsuario = (usuarioId, activo) =>
  apiClient.patch(`/api/usuarios/${usuarioId}/estado`, { activo }).then(unwrap);

export const apiCambiarPasswordUsuario = (usuarioId, nueva_password) =>
  apiClient.patch(`/api/usuarios/${usuarioId}/password`, { nueva_password }).then(unwrap);

export const apiListRoles = () => apiClient.get("/api/roles").then(unwrap);