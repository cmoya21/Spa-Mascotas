import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetDashboard = () =>
  apiClient.get("/api/reportes/dashboard").then(unwrap);

export const apiGetTopServicios = () =>
  apiClient.get("/api/reportes/top-servicios").then(unwrap);

export const apiGetVentasReporte = (params = {}) =>
  apiClient.get("/api/reportes/ventas", { params }).then(unwrap);

export const apiGetRankingRentabilidad = () =>
  apiClient.get("/api/reportes/ranking-rentabilidad").then(unwrap);

export const apiGetOcupacion = (params = {}) =>
  apiClient.get("/api/reportes/ocupacion", { params }).then(unwrap);

export const apiGetAuditoriaInsumos = (params = {}) =>
  apiClient.get("/api/reportes/auditoria-insumos", { params }).then(unwrap);

export const apiGetTicketPorCita = () =>
  apiClient.get("/api/reportes/ticket-por-cita").then(unwrap);

export const apiGetClientesFrecuentes = () =>
  apiClient.get("/api/reportes/clientes-frecuentes").then(unwrap);

export const apiGetClientesFrecuentesRecepcion = () =>
  apiClient.get("/api/reportes/clientes-frecuentes").then(unwrap);

export const apiGetSatisfaccionClientes = () =>
  apiClient.get("/api/reportes/satisfaccion-clientes").then(unwrap);

export const apiGetSatisfaccion = () =>
  apiClient.get("/api/reportes/satisfaccion").then(unwrap);

export const apiGetCronogramaDiario = (params = {}) =>
  apiClient.get("/api/reportes/cronograma-diario", { params }).then(unwrap);

export const apiGetCancelacionesReporte = (params = {}) =>
  apiClient.get("/api/reportes/cancelaciones", { params }).then(unwrap);

export const apiGetInventarioCritico = () =>
  apiClient.get("/api/reportes/inventario-critico").then(unwrap);

export const apiGetGroomerAgendaHoy = () =>
  apiClient.get("/api/reportes/groomer/agenda-hoy").then(unwrap);

export const apiGetGroomerProductividad = (params = {}) =>
  apiClient.get("/api/reportes/groomer/productividad", { params }).then(unwrap);

export const apiGetGroomerHistorialServicios = (params = {}) =>
  apiClient.get("/api/reportes/groomer/historial-servicios", { params }).then(unwrap);

export const apiGetGroomerConsumoInsumos = (params = {}) =>
  apiClient.get("/api/reportes/groomer/consumo-insumos", { params }).then(unwrap);

export const apiGetClienteHistorial = () =>
  apiClient.get("/api/reportes/cliente/historial").then(unwrap);

export const apiGetClienteHistorialMascota = (mascotaId) =>
  apiClient.get(`/api/reportes/cliente/historial-mascota/${mascotaId}`).then(unwrap);

export const apiGetClienteGaleria = (mascotaId) =>
  apiClient.get(`/api/reportes/cliente/galeria/${mascotaId}`).then(unwrap);

export const apiGetClientePuntos = () =>
  apiClient.get("/api/reportes/cliente/puntos").then(unwrap);

export const apiGetMisCitasReporte = () =>
  apiClient.get("/api/reportes/mis-citas").then(unwrap);
