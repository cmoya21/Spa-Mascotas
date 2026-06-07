import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListMascotas = (clienteId) =>
  apiClient
    .get("/api/mascotas", { params: clienteId ? { cliente_id: clienteId } : {} })
    .then(unwrap);

export const apiCrearMascota = (payload) =>
  apiClient.post("/api/mascotas", payload).then(unwrap);

export const apiActualizarMascota = (mascotaId, payload) =>
  apiClient.patch(`/api/mascotas/${mascotaId}`, payload).then(unwrap);

export const apiEliminarMascota = (mascotaId) =>
  apiClient.delete(`/api/mascotas/${mascotaId}`).then(unwrap);
