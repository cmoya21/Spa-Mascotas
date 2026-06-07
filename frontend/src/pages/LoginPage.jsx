import { useState } from "react";
import { useNavigate } from "react-router-dom";

import logo from "../assets/logo-spa.svg";
import LoginForm from "../components/auth/LoginForm";
import TwoFactorForm from "../components/auth/TwoFactorForm";

export default function LoginPage() {
  const [tempToken, setTempToken] = useState(null);
  const navigate = useNavigate();

  const handleGoogle = () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/auth/google/start`;
  };

  return (
    <div className="auth-layout">
      <div className="auth-left">
        <img src={logo} alt="Logo Spa" className="logo" />
        <h1>
          Spa & Tienda
          <span>de Mascotas</span>
        </h1>
        <p>Cuidamos a tus mascotas como si fueran nuestras</p>
        <div className="auth-bubbles">
          <span style={{ width: 140, height: 140, top: 40, right: 40 }} />
          <span style={{ width: 80, height: 80, bottom: 60, left: 60 }} />
          <span style={{ width: 40, height: 40, bottom: 120, right: 120 }} />
        </div>
      </div>
      <div className="auth-right">
        {tempToken ? (
          <TwoFactorForm
            tempToken={tempToken}
            onSuccess={() => {
              setTempToken(null);
              navigate("/redirect");
            }}
          />
        ) : (
          <div className="auth-card">
            <h2>Bienvenido de vuelta</h2>
            <p>Ingresa a tu cuenta para continuar</p>
            <button type="button" onClick={handleGoogle} className="google-button">
              <span className="google-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" role="img" focusable="false">
                  <path
                    d="M21.35 11.1h-9.18v2.99h5.26c-.23 1.5-1.74 4.4-5.26 4.4-3.16 0-5.73-2.62-5.73-5.84s2.57-5.84 5.73-5.84c1.8 0 3 .76 3.69 1.43l2.51-2.43C17 4.19 15 3.1 12.17 3.1 7.58 3.1 3.86 6.9 3.86 11.65S7.58 20.2 12.17 20.2c5.15 0 8.56-3.72 8.56-8.95 0-.6-.07-1.05-.16-1.5z"
                    fill="#4285F4"
                  />
                  <path
                    d="M5.18 7.86l2.46 1.82c.66-2.05 2.5-3.52 4.53-3.52 1.8 0 3 .76 3.69 1.43l2.51-2.43C17 4.19 15 3.1 12.17 3.1c-3.15 0-5.86 1.8-6.99 4.76z"
                    fill="#EA4335"
                  />
                  <path
                    d="M12.17 20.2c2.79 0 5.13-1.03 6.84-2.79l-3.17-2.45c-.85.6-1.99 1.01-3.67 1.01-2.99 0-5.53-2.02-6.44-4.75l-2.48 1.91c1.2 2.35 3.69 3.94 6.92 3.94z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.73 11.22c-.23-.69-.36-1.43-.36-2.2s.13-1.51.36-2.2l-2.48-1.91C2.48 6.44 2 8 2 9.02s.48 2.58 1.25 3.73l2.48-1.91z"
                    fill="#FBBC05"
                  />
                </svg>
              </span>
              Continuar con Google
            </button>
            <div className="divider">o</div>
            <LoginForm
              onRequire2FA={(token) => setTempToken(token)}
              onSuccess={() => navigate("/redirect")}
            />
            <div className="divider">o</div>
            <div style={{ textAlign: "center" }}>
              <span style={{ fontSize: 14, color: "#7a7672" }}>
                ¿No tienes cuenta? <a className="link-text" href="/register">Regístrate</a>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
