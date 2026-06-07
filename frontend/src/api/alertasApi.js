import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiGetAlertasInventario = () =>
  apiClient.get("/api/alertas/inventario").then(unwrap);

export const apiGetAlertasInventarioActivos = () =>
  apiClient.get("/api/alertas/inventario/activos").then(unwrap);

export const apiGetAlertasInventarioResumen = () =>
  apiClient.get("/api/alertas/inventario").then(unwrap);

export const apiGetConsumoPorGroomer = (params) =>
  apiClient.get("/api/alertas/consumo-por-groomer", { params }).then(unwrap);

export const apiReabastecerProductoAlerta = (productoId, payload) =>
  apiClient.post(`/api/productos/${productoId}/reabastecer`, payload).then(unwrap);
