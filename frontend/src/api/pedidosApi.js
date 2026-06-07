import { apiClient } from "./authApi.js";

const unwrap = (response) => response.data.data ?? response.data;

export const apiEnviarPedido = (pedidoId, payload) =>
  apiClient.post(`/api/pedidos/${pedidoId}/enviar`, payload).then(unwrap);
