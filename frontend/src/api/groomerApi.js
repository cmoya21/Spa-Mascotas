import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetAgendaPersonal = (fecha) =>
  apiClient.get("/api/groomers/me/agenda", { params: fecha ? { fecha } : {} }).then(unwrap);

export const apiGetAgendaSemanaPersonal = (params) =>
  apiClient.get("/api/groomers/me/agenda/semana", { params }).then(unwrap);

export const apiGetAgendaStats = () =>
  apiClient.get("/api/groomers/me/stats").then(unwrap);

export const apiListFichas = (citaId) => {
  if (!citaId) {
    return Promise.resolve({ fichas: [] });
  }
  return apiClient.get(`/api/fichas/cita/${citaId}`).then((response) => {
    const data = unwrap(response);
    return { fichas: data.ficha ? [data.ficha] : [] };
  });
};

export const apiCrearFicha = (payload) =>
  apiClient.post("/api/fichas", payload).then(unwrap);

export const apiGetFicha = (fichaId) =>
  apiClient.get(`/api/fichas/${fichaId}`).then(unwrap);

export const apiGetFichaByCita = (citaId) =>
  apiClient.get(`/api/fichas/cita/${citaId}`).then(unwrap);

export const apiUpdateFichaBase = (fichaId, payload) =>
  apiClient.patch(`/api/fichas/${fichaId}`, payload).then(unwrap);

export const apiUpdateChecklistItem = (fichaId, itemId, payload) =>
  apiClient.patch(`/api/fichas/${fichaId}/checklist/${itemId}`, payload).then(unwrap);

export const apiUploadFichaPhoto = (fichaId, formData) =>
  apiClient.post(`/api/fichas/${fichaId}/fotos`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then(unwrap);

export const apiDeleteFichaPhoto = (fichaId, fotoId) =>
  apiClient.delete(`/api/fichas/${fichaId}/fotos/${fotoId}`).then(unwrap);

export const apiGetFichaFotos = (fichaId) =>
  apiClient.get(`/api/fichas/${fichaId}/fotos`).then(unwrap);

export const apiGetEstadoCierre = (fichaId) =>
  apiClient.get(`/api/fichas/${fichaId}/estado-cierre`).then(unwrap);

export const apiUpdateFichaInsumos = (fichaId, payload) =>
  apiClient.patch(`/api/fichas/${fichaId}/insumos`, payload).then(unwrap);

export const apiGetInsumosDisponibles = (fichaId, q = "") =>
  apiClient.get(`/api/fichas/${fichaId}/insumos-disponibles`, { params: q ? { q } : {} }).then(unwrap);

export const apiCerrarFicha = (fichaId, payload) =>
  apiClient.patch(`/api/fichas/${fichaId}/cerrar`, payload).then(unwrap);
