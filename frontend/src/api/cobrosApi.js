import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListCobrosPendientes = () =>
  apiClient.get("/api/cobros/pendientes").then(unwrap);

export const apiPagarCita = (citaId, payload) =>
  apiClient.post(`/api/cobros/${citaId}/pagar`, payload).then(unwrap);

export const apiGetReciboCobro = (facturaId) =>
  apiClient.get(`/api/cobros/recibo/${facturaId}`).then(unwrap);

export const apiGetCierreCaja = (fecha) =>
  apiClient.get(`/api/cobros/cierre-caja`, { params: { fecha } }).then(unwrap);
