import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListProductos = () =>
  apiClient.get("/api/inventario/productos").then(unwrap);
