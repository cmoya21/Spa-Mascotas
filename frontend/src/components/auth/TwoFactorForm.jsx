import { useEffect, useRef, useState } from "react";

import useAuth from "../../hooks/useAuth";
import Alert from "../shared/Alert";
import Button from "../shared/Button";

export default function TwoFactorForm({ tempToken, onSuccess }) {
  const { verificar2FA } = useAuth();
  const [digits, setDigits] = useState(Array(6).fill(""));
  const [error, setError] = useState("");
  const inputsRef = useRef([]);

  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const handleChange = (index, value) => {
    if (!/^[0-9]?$/.test(value)) return;
    const updated = [...digits];
    updated[index] = value;
    setDigits(updated);

    if (value && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (event) => {
    const pasted = event.clipboardData.getData("text").trim();
    if (!/^[0-9]{6}$/.test(pasted)) return;
    setDigits(pasted.split(""));
    inputsRef.current[5]?.focus();
  };

  const handleVerify = async () => {
    setError("");
    const code = digits.join("");
    if (code.length < 6) {
      setError("Ingresa el código completo.");
      return;
    }
    try {
      await verificar2FA(tempToken, code);
      onSuccess?.();
    } catch (err) {
      setError("Código incorrecto, intenta otra vez.");
    }
  };

  return (
    <div className="auth-card" style={{ maxWidth: 380, margin: "0 auto" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 56, marginBottom: 12 }}>🛡️</div>
        <h2>Verificación en dos pasos</h2>
        <p>Abre Google Authenticator e ingresa el código de 6 dígitos</p>
      </div>
      <div className="otp-container" onPaste={handlePaste}>
        {digits.map((digit, index) => (
          <input
            key={index}
            value={digit}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            ref={(el) => (inputsRef.current[index] = el)}
            maxLength={1}
          />
        ))}
      </div>
      <Button onClick={handleVerify}>Verificar</Button>
      <div style={{ textAlign: "center", marginTop: 12 }}>
        <span className="link-text">Usar código de respaldo</span>
      </div>
      <Alert message={error} />
    </div>
  );
}
