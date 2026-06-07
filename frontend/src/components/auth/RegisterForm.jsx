import { useState } from "react";

import useAuth from "../../hooks/useAuth";
import Alert from "../shared/Alert";
import Button from "../shared/Button";
import InputField from "../shared/InputField";

const passwordStrength = (value) => {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (/[A-Z]/.test(value)) score += 1;
  if (/[0-9]/.test(value)) score += 1;
  if (/[!@#$%^&*]/.test(value)) score += 1;
  return score;
};

export default function RegisterForm() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    nombres: "",
    apellidos: "",
    email: "",
    telefono: "",
    ci: "",
    direccion: "",
    password: "",
    confirmPassword: "",
    acepta: false
  });
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
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const strength = passwordStrength(form.password);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (form.password !== form.confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    const hasUpper = /[A-Z]/.test(form.password);
    const hasLower = /[a-z]/.test(form.password);
    const hasNumber = /[0-9]/.test(form.password);
    const hasSymbol = /[!@#$%^&*()_+\-=[\]{};:,.?/]/.test(form.password);
    if (!(hasUpper && hasLower && hasNumber && hasSymbol)) {
      setError("La contraseña debe incluir mayúsculas, minúsculas, números y símbolos.");
      return;
    }
    if (!form.acepta) {
      setError("Debes aceptar los términos y condiciones.");
      return;
    }

    try {
      const response = await register({
        nombres: form.nombres,
        apellidos: form.apellidos,
        email: form.email,
        telefono: form.telefono,
        ci: form.ci,
        direccion: form.direccion,
        password: form.password
      });
      setSuccess(response.message || "Cuenta creada. Revisa tu correo para activarla.");
    } catch (err) {
      const message = err?.response?.data?.message;
      setError(message || "No se pudo registrar. Revisa los datos.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <InputField
            label="Nombres"
            value={form.nombres}
            onChange={(value) => handleChange("nombres", value)}
          />
          <InputField
            label="Apellidos"
            value={form.apellidos}
            onChange={(value) => handleChange("apellidos", value)}
          />
        </div>
        <InputField
          label="Correo electrónico"
          icon="✉"
          value={form.email}
          onChange={(value) => handleChange("email", value)}
        />
        <InputField
          label="Teléfono (Opcional)"
          value={form.telefono}
          onChange={(value) => handleChange("telefono", value)}
        />
        <InputField
          label="CI"
          value={form.ci}
          onChange={(value) => handleChange("ci", value)}
        />
        <InputField
          label="Dirección"
          value={form.direccion}
          onChange={(value) => handleChange("direccion", value)}
        />
        <InputField
          label="Contraseña"
          type={showPassword ? "text" : "password"}
          icon="🔒"
          value={form.password}
          onChange={(value) => handleChange("password", value)}
          rightElement={showPassword ? eyeOffIcon : eyeIcon}
          onRightElementClick={() => setShowPassword((prev) => !prev)}
          rightElementLabel={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
        />
        <div style={{ display: "flex", gap: 8 }}>
          {[0, 1, 2, 3].map((index) => (
            <span
              key={index}
              style={{
                flex: 1,
                height: 6,
                borderRadius: 6,
                background:
                  strength > index
                    ? ["#d63b3b", "#d4820a", "#f0c02a", "#1a9b74"][index]
                    : "#e8e5de"
              }}
            />
          ))}
        </div>
        <span style={{ fontSize: 12, color: "#7a7672" }}>
          Usa 8+ caracteres con mayúsculas, minúsculas, números y símbolos.
          Se recomienda una passphrase de 3 a 4 palabras.
        </span>
        <InputField
          label="Confirmar contraseña"
          type={showConfirm ? "text" : "password"}
          value={form.confirmPassword}
          onChange={(value) => handleChange("confirmPassword", value)}
          rightElement={showConfirm ? eyeOffIcon : eyeIcon}
          onRightElementClick={() => setShowConfirm((prev) => !prev)}
          rightElementLabel={showConfirm ? "Ocultar contraseña" : "Mostrar contraseña"}
        />
        <label style={{ display: "flex", gap: 8, fontSize: 13, color: "#3d3a38" }}>
          <input
            type="checkbox"
            checked={form.acepta}
            onChange={(e) => handleChange("acepta", e.target.checked)}
          />
          Acepto los términos y condiciones
        </label>
        <Button>Crear cuenta</Button>
        {success && (
          <div
            style={{
              marginTop: 16,
              padding: "12px 14px",
              background: "#ecfdf5",
              borderLeft: "3px solid #10b981",
              borderRadius: 8,
              color: "#0f766e",
              display: "flex",
              alignItems: "center",
              gap: 8
            }}
          >
            <span>✓</span>
            <span>{success}</span>
          </div>
        )}
        <Alert message={error} />
      </div>
    </form>
  );
}
