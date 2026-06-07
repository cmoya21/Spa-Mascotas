import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import useAuth from "../hooks/useAuth";

export default function OAuthGoogleCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { setSessionFromOAuth } = useAuth();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const rol = params.get("rol");
    const email = params.get("email");

    if (accessToken) {
      setSessionFromOAuth({
        access_token: accessToken,
        refresh_token: refreshToken,
        usuario: { email, rol }
      });
      navigate("/cliente/vista", { replace: true });
      return;
    }

    navigate("/login", { replace: true });
  }, [params, navigate, setSessionFromOAuth]);

  return null;
}
