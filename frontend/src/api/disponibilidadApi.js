import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetHorarioGeneral = () =>
  apiClient.get("/api/disponibilidad/horario-general").then(unwrap);

export const apiUpdateHorarioGeneral = (payload) =>
  apiClient.put("/api/disponibilidad/horario-general", payload).then(unwrap);

export const apiGetGroomersDisponibilidad = () =>
  apiClient.get("/api/disponibilidad/groomers").then(unwrap);

export const apiUpdateGroomerDisponibilidad = (groomerId, payload) =>
  apiClient.put(`/api/disponibilidad/groomers/${groomerId}`, payload).then(unwrap);

export const apiListBloqueosDisponibilidad = (params) =>
  apiClient.get("/api/bloqueos", { params }).then(unwrap);

export const apiCrearBloqueoDisponibilidad = (payload, force = false) =>
  apiClient
    .post("/api/bloqueos", payload, {
      params: force ? { forzar: "true" } : {}
    })
    .then(unwrap);

export const apiEliminarBloqueoDisponibilidad = (bloqueoId) =>
  apiClient.delete(`/api/bloqueos/${bloqueoId}`).then(unwrap);
