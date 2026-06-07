import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiRegistrarInsumo = (payload) =>
  apiClient.post("/api/insumos/salida", payload).then(unwrap);

export const apiListInsumosFicha = (fichaId) =>
  apiClient.get(`/api/insumos/salida/ficha/${fichaId}`).then((response) => response.data);

export const apiLogSalidaGroomer = (params) =>
  apiClient.get("/api/insumos/log-groomer", { params }).then((response) => response.data);

export const apiLogSalidaAdmin = (params) =>
  apiClient.get("/api/insumos/log-admin", { params }).then((response) => response.data);

export const apiProductosDisponiblesParaInsumos = (params) =>
  apiClient.get("/api/productos/disponibles-para-insumos", { params }).then((response) => response.data);

export const apiConfirmarUsoInsumo = (salidaId, payload) =>
  apiClient.patch(`/api/insumos/salida/${salidaId}/confirmar-uso`, payload).then((response) => response.data);

export const apiConfirmarTodosInsumosFicha = (fichaId, payload) =>
  apiClient.patch(`/api/insumos/salida/ficha/${fichaId}/confirmar-todos`, payload).then((response) => response.data);

export const apiDevolverInsumo = (salidaId, payload) =>
  apiClient.patch(`/api/insumos/salida/${salidaId}/devolver`, payload).then((response) => response.data);

export const apiRegistrarMermaInsumo = (salidaId, payload) =>
  apiClient.patch(`/api/insumos/salida/${salidaId}/merma`, payload).then((response) => response.data);
