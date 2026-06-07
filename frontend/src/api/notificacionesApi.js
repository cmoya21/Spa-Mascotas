import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetNotificacionesAdmin = (params) =>
  apiClient.get("/api/notificaciones/admin", { params }).then(unwrap);

export const apiGetStatsNotificaciones = () =>
  apiClient.get("/api/notificaciones/stats").then(unwrap);

export const apiReenviarNotificacion = (notifId) =>
  apiClient.post(`/api/notificaciones/reenviar/${notifId}`).then(unwrap);
