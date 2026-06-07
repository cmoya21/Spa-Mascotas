import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json"
  }
});

const unwrap = (response) => response.data.data ?? response.data;

export const apiLogin = (email, password) =>
  apiClient.post("/api/auth/login", { email, password }).then(unwrap);

export const apiLogin2FA = (tempToken, codigo) =>
  apiClient
    .post("/api/auth/login-2fa", { temp_token: tempToken, code: codigo })
    .then(unwrap);

export const apiVerificar2FA = apiLogin2FA;

export const apiRegister = (datos) =>
  apiClient.post("/api/auth/register", datos).then(unwrap);

export const apiRefresh = (refreshToken) =>
  apiClient
    .post("/api/auth/refresh", null, {
      headers: { Authorization: `Bearer ${refreshToken}` }
    })
    .then(unwrap);

export const apiLogout = (accessToken, refreshToken = null) =>
  apiClient.post(
    "/api/auth/logout",
    refreshToken ? { refresh_token: refreshToken } : {},
    { headers: { Authorization: `Bearer ${accessToken}` } }
  ).then(unwrap);

export const apiGetPerfil = (accessToken) =>
  apiClient
    .get("/api/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` }
    })
    .then(unwrap);

export const apiSetup2FA = (accessToken) =>
  apiClient
    .post(
      "/api/auth/setup-2fa",
      {},
      { headers: { Authorization: `Bearer ${accessToken}` } }
    )
    .then(unwrap);

export const apiVerify2FASetup = (accessToken, code) =>
  apiClient
    .post(
      "/api/auth/verify-2fa",
      { code },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    )
    .then(unwrap);

export const apiConfigurar2FA = apiSetup2FA;

export const apiActivar2FA = (accessToken, secreto, codigoVerificacion) =>
  apiClient
    .post(
      "/api/auth/verify-2fa",
      { secret: secreto, code: codigoVerificacion },
      { headers: { Authorization: `Bearer ${accessToken}` } }
    )
    .then(unwrap);

export const apiActivarCuenta = (token) =>
  apiClient.get(`/api/auth/activar-cuenta?token=${encodeURIComponent(token)}`).then(unwrap);

export const apiForgotPassword = (email) =>
  apiClient.post("/api/auth/forgot-password", { email }).then(unwrap);

export const apiResetPassword = (token, password) =>
  apiClient.post("/api/auth/reset-password", { token, password }).then(unwrap);
