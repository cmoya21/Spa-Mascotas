import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListPromociones = () =>
  apiClient.get("/api/promociones").then(unwrap);

export const apiCrearPromocion = (payload) =>
  apiClient.post("/api/promociones", payload).then(unwrap);

export const apiTogglePromocion = (promocionId) =>
  apiClient.patch(`/api/promociones/${promocionId}/toggle`).then(unwrap);

export const apiValidarCupon = (payload) =>
  apiClient.post("/api/promociones/validar-cupon", payload).then(unwrap);

export const apiAplicarPromocionAFactura = (promocionId, payload) =>
  apiClient.post(`/api/promociones/${promocionId}/aplicar-a-factura`, payload).then(unwrap);

export const apiGetBeneficiosFrecuente = () =>
  apiClient.get("/api/clientes/me/beneficios-frecuente").then(unwrap);
