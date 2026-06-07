import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

const unwrapList = (key) => (response) => {
  const data = unwrap(response);
  return data?.[key] ? data : { [key]: data?.[key] ?? [] };
};

export const apiListServicios = () =>
  apiClient.get("/api/servicios").then(unwrap);

export const apiCrearServicio = (payload) =>
  apiClient.post("/api/servicios", payload).then(unwrap);

export const apiActualizarServicio = (servicioId, payload) =>
  apiClient.put(`/api/servicios/${servicioId}`, payload).then(unwrap);

export const apiActualizarEstadoServicio = (servicioId, payload) =>
  apiClient.patch(`/api/servicios/${servicioId}/estado`, payload).then(unwrap);

export const apiGetServicio = (servicioId) =>
  apiClient.get(`/api/servicios/${servicioId}`).then(unwrap);

export const apiGetChecklistTemplate = (servicioId) =>
  apiClient.get(`/api/servicios/${servicioId}/checklist-template`).then(unwrap);

export const apiGetDuracionEstimada = (servicioId, mascotaId) =>
  apiClient.get(`/api/servicios/${servicioId}/duracion-estimada`, {
    params: { mascota_id: mascotaId },
  }).then(unwrap);

export const apiGetHorarioSpa = () =>
  apiClient.get("/api/agenda/horario-spa").then(unwrap);

export const apiUpdateHorarioSpa = (payload) =>
  apiClient.put("/api/agenda/horario-spa", payload).then(unwrap);

export const apiGetDisponibilidadGroomers = () =>
  apiClient.get("/api/agenda/disponibilidad-groomers").then(unwrap);

export const apiUpdateDisponibilidadGroomer = (groomerId, payload) =>
  apiClient.put(`/api/agenda/disponibilidad-groomers/${groomerId}`, payload).then(unwrap);

export const apiListHorarios = (groomerId) =>
  apiClient.get("/api/agenda/horarios", { params: { groomer_id: groomerId } }).then(unwrap);

export const apiGuardarHorario = (payload) =>
  apiClient.post("/api/agenda/horarios", payload).then(unwrap);

export const apiCrearBloqueo = (payload, force = false) =>
  apiClient
    .post("/api/agenda/bloqueos", payload, {
      params: force ? { forzar: "true" } : {},
    })
    .then(unwrap);

export const apiListBloqueos = (params) =>
  apiClient.get("/api/agenda/bloqueos", { params }).then(unwrap);

export const apiEliminarBloqueo = (bloqueoId) =>
  apiClient.delete(`/api/agenda/bloqueos/${bloqueoId}`).then(unwrap);

export const apiGetSlotsDisponibles = (payload) => {
  return apiClient.get("/api/agenda/slots-disponibles", { params: payload }).then(unwrap);
};

export const apiGetFechasDisponibles = (payload) =>
  apiClient.get("/api/agenda/fechas-disponibles", { params: payload }).then(unwrap);

export const apiValidarCita = (payload) =>
  apiClient.post("/api/agenda/validar-cita", payload).then(unwrap);

export const apiCrearCita = (payload) =>
  apiClient.post("/api/citas", payload).then(unwrap);

export const apiListCitas = (params) =>
  apiClient.get("/api/citas", { params }).then(unwrap);

export const apiConfirmarCita = (citaId) =>
  apiClient.patch(`/api/citas/${citaId}/confirmar`).then(unwrap);

export const apiCancelarCita = (citaId, payload) =>
  apiClient.patch(`/api/citas/${citaId}/cancelar`, payload).then(unwrap);

export const apiActualizarEstadoCita = (citaId, payload) =>
  apiClient.patch(`/api/citas/${citaId}/estado`, payload).then(unwrap);

export const apiReprogramarCita = (citaId, payload) =>
  apiClient.patch(`/api/citas/${citaId}/reprogramar`, payload).then(unwrap);

export const apiGetAgendaSemana = (fecha) =>
  apiClient.get("/api/agenda/semana", { params: { fecha } }).then(unwrap);

export const apiGetAgendaDia = (params) =>
  apiClient.get("/api/agenda/dia", { params }).then(unwrap);
