import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetMisMascotas = () =>
  apiClient.get("/api/clientes/me/mascotas").then(unwrap);

export const apiCrearMiMascota = (payload) =>
  (payload instanceof FormData
    ? apiClient.post("/api/clientes/me/mascotas", payload, { headers: { "Content-Type": "multipart/form-data" } })
    : apiClient.post("/api/clientes/me/mascotas", payload)
  ).then(unwrap);

export const apiActualizarMiMascota = (mascotaId, payload) =>
  (payload instanceof FormData
    ? apiClient.put(`/api/clientes/me/mascotas/${mascotaId}`, payload, { headers: { "Content-Type": "multipart/form-data" } })
    : apiClient.put(`/api/clientes/me/mascotas/${mascotaId}`, payload)
  ).then(unwrap);

export const apiEliminarMiMascota = (mascotaId) =>
  apiClient.delete(`/api/clientes/me/mascotas/${mascotaId}`).then(unwrap);

export const apiRegistrarVacunaMascota = (mascotaId, payload) =>
  apiClient.post(`/api/clientes/me/mascotas/${mascotaId}/vacunas`, payload).then(unwrap);

export const apiSolicitarCitaCliente = (payload) =>
  apiClient.post("/api/solicitudes-cita", payload).then(unwrap);

export const apiGetMisCitas = (params) =>
  apiClient.get("/api/clientes/me/citas", { params }).then(unwrap);

export const apiCancelarMiCita = (citaId, payload) =>
  apiClient.patch(`/api/clientes/me/citas/${citaId}/cancelar`, payload).then(unwrap);

export const apiGetHistorialMascota = (mascotaId) =>
  apiClient.get(`/api/clientes/me/mascotas/${mascotaId}/historial`).then(unwrap);

export const apiGetCitasHistorialMascota = (mascotaId) =>
  apiClient.get(`/api/clientes/me/mascotas/${mascotaId}/citas-historial`).then(unwrap);

export const apiGetMisNotificaciones = () =>
  apiClient.get("/api/clientes/me/notificaciones").then(unwrap);

export const apiResponderEncuestaCita = (citaId, payload) =>
  apiClient.post(`/api/encuestas/${citaId}`, payload).then(unwrap);

export const apiGetBeneficiosFrecuente = () =>
  apiClient.get("/api/clientes/me/beneficios-frecuente").then(unwrap);
