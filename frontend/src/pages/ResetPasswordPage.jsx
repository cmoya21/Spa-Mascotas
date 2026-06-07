import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { apiResetPassword } from "../api/authApi";
import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
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
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setToken(params.get("token") || "");
  }, [params]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("Token invalido o expirado.");
      return;
    }
    if (password !== confirm) {
      setError("Las contrasenas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      const response = await apiResetPassword(token, password);
      setMessage(response.message || "Contrasena actualizada.");
    } catch (err) {
      setError("No se pudo actualizar la contrasena.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-left">
        <h1>
          Nueva
          <span>contrasena</span>
        </h1>
        <p>Define una nueva clave segura para tu cuenta.</p>
      </div>
      <div className="auth-right">
        <div className="auth-card">
          <h2>Restablecer contrasena</h2>
          <p>Usa una clave con mayusculas, minusculas, numeros y simbolos.</p>
          <form onSubmit={handleSubmit} className="form-group">
            <InputField
              label="Nueva contrasena"
              type={showPassword ? "text" : "password"}
              icon="🔒"
              value={password}
              onChange={setPassword}
              placeholder="Minimo 8 caracteres"
              rightElement={showPassword ? eyeOffIcon : eyeIcon}
              onRightElementClick={() => setShowPassword((prev) => !prev)}
              rightElementLabel={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            />
            <InputField
              label="Confirmar contrasena"
              type={showConfirm ? "text" : "password"}
              icon="🔒"
              value={confirm}
              onChange={setConfirm}
              placeholder="Repite tu contrasena"
              rightElement={showConfirm ? eyeOffIcon : eyeIcon}
              onRightElementClick={() => setShowConfirm((prev) => !prev)}
              rightElementLabel={showConfirm ? "Ocultar contraseña" : "Mostrar contraseña"}
            />
            <Button loading={loading}>Guardar contrasena</Button>
            {message && <Alert message={message} success />}
            <Alert message={error} />
          </form>
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Link className="ghost-button" to="/login">Volver al login</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
