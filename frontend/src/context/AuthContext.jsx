import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import {
  apiClient,
  apiLogin,
  apiVerificar2FA,
  apiRegister,
  apiRefresh,
  apiLogout,
  apiGetPerfil
} from "../api/authApi";

const AuthContext = createContext(null);
const ACCESS_KEY = "spa_access_token";
const REFRESH_KEY = "spa_refresh_token";
const IDLE_TIMEOUT = 30 * 60 * 1000;

const normalizeStoredToken = (value) => {
  if (!value) return null;
  const token = String(value).trim();
  if (!token || token === "null" || token === "undefined") return null;
  return token;
};

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [accessToken, setAccessToken] = useState(normalizeStoredToken(localStorage.getItem(ACCESS_KEY)));
  const [refreshToken, setRefreshToken] = useState(
    normalizeStoredToken(localStorage.getItem(REFRESH_KEY))
  );
  const [isLoading, setIsLoading] = useState(true);
  const accessRef = useRef(null);

  useEffect(() => {
    accessRef.current = accessToken;
  }, [accessToken]);

  useEffect(() => {
    const reqInterceptor = apiClient.interceptors.request.use((config) => {
      if (accessRef.current) {
        config.headers.Authorization = `Bearer ${accessRef.current}`;
      }
      return config;
    });

    const resInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const original = error.config;
        const url = original?.url || "";
        const skipRefresh =
          url.includes("/api/auth/login") ||
          url.includes("/api/auth/refresh") ||
          url.includes("/api/auth/verificar-2fa") ||
          url.includes("/api/auth/login-2fa") ||
          url.includes("/api/auth/setup-2fa") ||
          url.includes("/api/auth/verify-2fa");

        if (error.response?.status === 401 && !original._retry && !skipRefresh) {
          original._retry = true;
          const newAccess = await refreshAccessToken();
          if (newAccess) {
            original.headers.Authorization = `Bearer ${newAccess}`;
            return apiClient(original);
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      apiClient.interceptors.request.eject(reqInterceptor);
      apiClient.interceptors.response.eject(resInterceptor);
    };
  }, []);

  const setSession = (payload) => {
    setUsuario(payload.usuario || null);
    setAccessToken(payload.access_token || null);
    if (payload.access_token) {
      localStorage.setItem(ACCESS_KEY, payload.access_token);
    }
    if (payload.refresh_token) {
      setRefreshToken(payload.refresh_token);
      localStorage.setItem(REFRESH_KEY, payload.refresh_token);
    }
  };

  const loadPerfil = async (token) => {
    const perfil = await apiGetPerfil(token);
    setUsuario(perfil || null);
    return perfil || null;
  };

  const clearSession = () => {
    setUsuario(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  };

  const login = async (email, password) => {
    const data = await apiLogin(email, password);
    if (data.requires_2fa || data.requiere_2fa) {
      return data;
    }
    setSession(data);
    return data;
  };

  const verificar2FA = async (tempToken, codigoTotp) => {
    const data = await apiVerificar2FA(tempToken, codigoTotp);
    setSession(data);
    return data;
  };

  const register = async (payload) => {
    const data = await apiRegister(payload);
    if (data.access_token) {
      setSession(data);
    }
    return data;
  };

  const logout = async () => {
    const currentAccess = accessToken;
    const currentRefresh = refreshToken;
    if (accessToken) {
      try {
        await apiLogout(currentAccess, currentRefresh);
      } catch (_) {
        // ignore
      }
    }
    clearSession();
  };

  const refreshAccessToken = async () => {
    const token = normalizeStoredToken(refreshToken);
    if (!token) {
      clearSession();
      return null;
    }
    try {
      const data = await apiRefresh(token);
      const newAccess = data.access_token || null;
      setAccessToken(newAccess);
      if (newAccess) {
        localStorage.setItem(ACCESS_KEY, newAccess);
      }
      return newAccess;
    } catch (_) {
      clearSession();
      return null;
    }
  };

  const hasRole = (...roles) => {
    if (!usuario?.rol) return false;
    return roles.includes(usuario.rol);
  };

  useEffect(() => {
    const bootstrap = async () => {
      if (accessToken) {
        try {
          await loadPerfil(accessToken);
        } catch (_) {
          if (refreshToken) {
            const newAccess = await refreshAccessToken();
            if (newAccess) {
              try {
                await loadPerfil(newAccess);
              } catch (_) {
                clearSession();
              }
            }
          } else {
            clearSession();
          }
        }
      } else if (refreshToken) {
        const newAccess = await refreshAccessToken();
        if (newAccess) {
          try {
            await loadPerfil(newAccess);
          } catch (_) {
            clearSession();
          }
        }
      }
      setIsLoading(false);
    };
    bootstrap();
  }, []);

  useEffect(() => {
    if (!accessToken) return;
    let timerId;

    const resetTimer = () => {
      if (timerId) clearTimeout(timerId);
      timerId = setTimeout(() => {
        logout();
      }, IDLE_TIMEOUT);
    };

    const events = ["mousemove", "keydown", "scroll", "click"];
    events.forEach((event) => window.addEventListener(event, resetTimer));
    resetTimer();

    return () => {
      if (timerId) clearTimeout(timerId);
      events.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [accessToken]);

  const value = useMemo(
    () => ({
      usuario,
      accessToken,
      refreshToken,
      isAuthenticated: !!accessToken,
      isLoading,
      login,
      verificar2FA,
      register,
      logout,
      refreshAccessToken,
      hasRole,
      setSessionFromOAuth: setSession
    }),
    [usuario, accessToken, refreshToken, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuthContext = () => useContext(AuthContext);
