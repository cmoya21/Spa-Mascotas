import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { apiActivarCuenta } from "../api/authApi";

export default function ActivatePage() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      setMessage("Token inválido o faltante.");
      return;
    }

    apiActivarCuenta(token)
      .then((data) => {
        setStatus("success");
        setMessage(data.message || "Cuenta activada correctamente.");
      })
      .catch(() => {
        setStatus("error");
        setMessage("El enlace es inválido o expiró.");
      });
  }, [params]);

  return (
    <div style={{ padding: 40, maxWidth: 520, margin: "0 auto" }}>
      <h2>Activación de cuenta</h2>
      {status === "loading" && <p>Verificando enlace...</p>}
      {status === "success" && <p>{message}</p>}
      {status === "error" && <p>{message}</p>}
      <div style={{ marginTop: 16 }}>
        <a href="/login" className="ghost-button">Volver al login</a>
      </div>
    </div>
  );
}
