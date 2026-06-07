import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetChecklistTemplate = (servicioId) =>
  apiClient
    .get("/api/grooming/checklist-template", { params: { servicio_id: servicioId } })
    .then(unwrap);

export const apiListCitasGroomer = () =>
  apiClient.get("/api/grooming/citas").then(unwrap);

export const apiListFichas = () =>
  apiClient.get("/api/grooming/fichas").then(unwrap);

export const apiCrearFicha = (payload) =>
  apiClient.post("/api/grooming/fichas", payload).then(unwrap);

export const apiGetFicha = (fichaId) =>
  apiClient.get(`/api/grooming/fichas/${fichaId}`).then(unwrap);

export const apiActualizarChecklist = (fichaId, payload) =>
  apiClient.post(`/api/grooming/fichas/${fichaId}/checklist`, payload).then(unwrap);

export const apiAgregarFoto = (fichaId, payload) =>
  apiClient.post(`/api/grooming/fichas/${fichaId}/fotos`, payload).then(unwrap);

export const apiCerrarFicha = (fichaId, payload) =>
  apiClient.patch(`/api/grooming/fichas/${fichaId}/cerrar`, payload).then(unwrap);

export const apiGuardarInsumosFicha = (fichaId, payload) =>
  apiClient.patch(`/api/grooming/fichas/${fichaId}/insumos`, payload).then(unwrap);
