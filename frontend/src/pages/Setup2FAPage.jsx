import { useEffect, useState } from "react";

import { apiActivar2FA, apiConfigurar2FA } from "../api/authApi";
import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";
import useAuth from "../hooks/useAuth";

export default function Setup2FAPage() {
  const { accessToken } = useAuth();
  const [secret, setSecret] = useState("");
  const [qrUri, setQrUri] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleActivar = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const data = await apiConfigurar2FA(accessToken);
      setSecret(data.secret || data.secreto || "");
      setQrUri(data.qr_uri || data.qr_base64 || "");
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo generar el 2FA.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerificar = async () => {
    setError("");
    setSuccess("");
    if (code.length !== 6) {
      setError("Ingresa el código de 6 dígitos.");
      return;
    }
    setLoading(true);
    try {
      await apiActivar2FA(accessToken, secret, code);
      setSuccess("✅ 2FA activado correctamente");
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo activar el 2FA.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setError("");
    setSuccess("");
  }, [accessToken]);

  const qrImage = qrUri
    ? `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(qrUri)}&size=220x220`
    : "";

  return (
    <div className="page-shell" style={{ maxWidth: 840, margin: "0 auto" }}>
      <section className="agenda-card">
        <p className="calendar-kicker">Seguridad</p>
        <h2 style={{ marginTop: 0 }}>Activación de 2FA</h2>
        <p className="section-note">Escanea el QR con tu app autenticadora y confirma el código de 6 dígitos.</p>

        <div style={{ display: "grid", gap: 16 }}>
          <Button loading={loading} disabled={loading} onClick={handleActivar}>
            Activar 2FA
          </Button>

          {qrUri ? (
            <div style={{ display: "grid", gap: 16, justifyItems: "center", padding: 20, borderRadius: 20, background: "rgba(255,255,255,0.04)" }}>
              <img src={qrImage} alt="QR de autenticación" width="220" height="220" />
              <div style={{ maxWidth: 420, width: "100%" }}>
                <InputField label="Código de verificación" value={code} onChange={setCode} maxLength={6} inputMode="numeric" required />
                <Button loading={loading} disabled={loading} onClick={handleVerificar}>
                  Confirmar 2FA
                </Button>
              </div>
              <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", wordBreak: "break-all", textAlign: "center" }}>
                Secret: {secret}
              </div>
            </div>
          ) : null}
        </div>

        {success ? <Alert message={success} success /> : null}
        {error ? <Alert message={error} /> : null}
      </section>
    </div>
  );
}