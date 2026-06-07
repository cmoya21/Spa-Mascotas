import { useState } from "react";
import { Link } from "react-router-dom";

import { apiForgotPassword } from "../api/authApi";
import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const response = await apiForgotPassword(email);
      setMessage(response.message || "Si el correo existe, enviaremos un enlace.");
    } catch (err) {
      setError("No se pudo enviar el enlace. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-left">
        <h1>
          Recuperar
          <span>acceso</span>
        </h1>
        <p>Recibe un enlace para restablecer tu contrasena.</p>
      </div>
      <div className="auth-right">
        <div className="auth-card">
          <h2>Olvidaste tu contrasena</h2>
          <p>Ingresa tu correo y enviaremos un enlace seguro.</p>
          <form onSubmit={handleSubmit} className="form-group">
            <InputField
              label="Correo"
              icon="✉"
              value={email}
              onChange={setEmail}
              placeholder="tu@email.com"
            />
            <Button loading={loading}>Enviar enlace</Button>
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
