import { useEffect, useMemo, useState } from "react";

import useAuth from "../../hooks/useAuth";
import Alert from "../shared/Alert";
import Button from "../shared/Button";
import InputField from "../shared/InputField";

export default function LoginForm({ onRequire2FA, onSuccess }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  const formattedLockout = useMemo(() => {
    const minutes = Math.floor(lockoutSeconds / 60);
    const seconds = lockoutSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }, [lockoutSeconds]);

  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const timer = setInterval(() => {
      setLockoutSeconds((prev) => Math.max(prev - 1, 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [lockoutSeconds]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      if ((data.requires_2fa || data.requiere_2fa) && onRequire2FA) {
        onRequire2FA(data.temp_token);
        return;
      }
      onSuccess?.();
    } catch (err) {
      const status = err?.response?.status;
      const message = err?.response?.data?.message;
      const retry = err?.response?.data?.details?.retry_after_seconds;
      if (status === 403) {
        setError("Cuenta desactivada. Contacta al administrador.");
        return;
      }
      if (status === 429) {
        setError("Demasiados intentos. Espera 15 minutos.");
        if (typeof retry === "number" && retry > 0) {
          setLockoutSeconds(retry);
        }
        return;
      }
      if (status === 401) {
        setError("Email o contraseña incorrectos");
        return;
      }
      if (typeof retry === "number" && retry > 0) {
        setLockoutSeconds(retry);
        const minutes = Math.floor(retry / 60);
        const seconds = String(retry % 60).padStart(2, "0");
        setError(`Demasiados intentos. Espera ${minutes}:${seconds} para volver a intentar.`);
        return;
      }
      setError(message || "Email o contraseña incorrectos");
    } finally {
      setLoading(false);
    }
  };

  const eyeIcon = (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 5c5 0 9.27 3.11 11 7-1.73 3.89-6 7-11 7S2.73 15.89 1 12c1.73-3.89 6-7 11-7zm0 2c-3.76 0-7.15 2.15-8.74 5 1.59 2.85 4.98 5 8.74 5 3.76 0 7.15-2.15 8.74-5C19.15 9.15 15.76 7 12 7zm0 2.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z"
        fill="currentColor"
      />
    </svg>
  );

  const eyeOffIcon = (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M3.3 4.7 2 6l3.2 3.2C3.6 10.3 2.2 11.9 1 12c1.73 3.89 6 7 11 7 1.77 0 3.45-.35 4.97-.98L20 20.7 21.3 19.4 3.3 4.7zM12 17c-3.76 0-7.15-2.15-8.74-5 .7-1.25 1.7-2.35 2.9-3.2l2.15 2.15A2.5 2.5 0 0 0 11.5 14c.5 0 .98-.14 1.39-.38l2.42 2.42c-.99.59-2.14.96-3.31.96zm9.74-5c-.57 1.02-1.36 2-2.32 2.83l-2.18-2.18c.17-.41.26-.85.26-1.32a2.5 2.5 0 0 0-2.5-2.5c-.47 0-.91.09-1.32.26L9.2 7.61C10.05 7.22 11 7 12 7c3.76 0 7.15 2.15 8.74 5z"
        fill="currentColor"
      />
    </svg>
  );

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <InputField
          label="Correo electrónico"
          icon="✉"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="tu@email.com"
          required
        />
        <InputField
          label="Contraseña"
          type={showPassword ? "text" : "password"}
          icon="🔒"
          value={password}
          onChange={setPassword}
          placeholder="••••••••"
          rightElement={showPassword ? eyeOffIcon : eyeIcon}
          onRightElementClick={() => setShowPassword((prev) => !prev)}
          rightElementLabel={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
          error={""}
          required
        />
        <div style={{ textAlign: "right" }}>
          <a className="link-text" href="/forgot-password">
            ¿Olvidaste tu contraseña?
          </a>
        </div>
        <Button loading={loading} disabled={loading || lockoutSeconds > 0}>
          Iniciar sesión
        </Button>
        {lockoutSeconds > 0 && (
          <div className="alert alert-warn">
            <span>!</span>
            <span>Espera {formattedLockout} para volver a intentar.</span>
          </div>
        )}
        <Alert message={error} />
      </div>
    </form>
  );
}
