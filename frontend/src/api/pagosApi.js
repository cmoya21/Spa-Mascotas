import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiCrearFactura = (payload) =>
  apiClient.post("/api/pagos/facturas", payload).then(unwrap);

export const apiRegistrarPago = (payload) =>
  apiClient.post("/api/pagos/pagos", payload).then(unwrap);

export const apiListFacturas = () =>
  apiClient.get("/api/pagos/facturas").then(unwrap);
