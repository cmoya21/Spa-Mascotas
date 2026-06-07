import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiListCategoriasProductos = () =>
  apiClient.get("/api/categorias").then(unwrap);

export const apiListProductosPublicos = (params = {}) =>
  apiClient.get("/api/productos", { params }).then(unwrap);

export const apiGetProductoPublico = (productoId) =>
  apiClient.get(`/api/productos/${productoId}`).then(unwrap);

export const apiGetCarritoMe = () =>
  apiClient.get("/api/carrito/me").then(unwrap);

export const apiAgregarItemCarrito = (payload) =>
  apiClient.post("/api/carrito/me/items", payload).then(unwrap);

export const apiActualizarItemCarrito = (itemId, payload) =>
  apiClient.patch(`/api/carrito/me/items/${itemId}`, payload).then(unwrap);

export const apiEliminarItemCarrito = (itemId) =>
  apiClient.delete(`/api/carrito/me/items/${itemId}`).then(unwrap);

export const apiVaciarCarrito = () => apiClient.delete("/api/carrito/me").then(unwrap);

export const apiGenerarPedidoWhatsApp = (payload = {}) =>
  apiClient.post("/api/pedidos/generar-whatsapp", payload).then(unwrap);

export const apiListPedidosMe = () => apiClient.get("/api/pedidos/me").then(unwrap);

export const apiReabastecerProducto = (productoId, payload) =>
  apiClient.post(`/api/productos/${productoId}/stock`, payload).then(unwrap);
