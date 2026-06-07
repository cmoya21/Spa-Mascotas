import { useEffect, useMemo, useState } from "react";

import Button from "../shared/Button";
import {
  apiGetReciboCobro,
  apiListCobrosPendientes,
  apiPagarCita,
} from "../../api/cobrosApi";
import { apiListPromociones } from "../../api/promocionesApi";

const QR_NUMBER = import.meta.env.VITE_QR_SPA_NUMBER || "591-70000000";
const BANK_NAME = import.meta.env.VITE_BANCO_NOMBRE || "BANCO NACIONAL";
const ACCOUNT_NUMBER = import.meta.env.VITE_CUENTA_NUMERO || "000-0000000";
const SPA_NAME = import.meta.env.VITE_SPA_NOMBRE || "Pet Spa";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

const readMinutes = (value) => {
  const total = Number(value || 0);
  return Number.isFinite(total) ? total : 0;
};

const buildWaitBadge = (minutos) => {
  if (minutos > 60) return { text: "Esperando 1h+", tone: "danger" };
  if (minutos > 30) return { text: `Esperando ${Math.round(minutos)} min`, tone: "warning" };
  return null;
};

export default function PanelCobros() {
  const [pendientes, setPendientes] = useState([]);
  const [promociones, setPromociones] = useState([]);
  const [selected, setSelected] = useState(null);
  const [manualDiscount, setManualDiscount] = useState(0);
  const [selectedPromotionId, setSelectedPromotionId] = useState("");
  const [metodo, setMetodo] = useState("");
  const [referencia, setReferencia] = useState("");
  const [loading, setLoading] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState(null);

  const loadPendientes = async () => {
    const data = await apiListCobrosPendientes();
    const items = [...(data.pendientes || [])].sort((a, b) => readMinutes(b.minutos_espera) - readMinutes(a.minutos_espera));
    setPendientes(items);
  };

  const loadPromociones = async () => {
    try {
      const data = await apiListPromociones();
      setPromociones(Array.isArray(data) ? data : data.promociones || []);
    } catch {
      setPromociones([]);
    }
  };

  useEffect(() => {
    let mounted = true;
    const bootstrap = async () => {
      setLoading(true);
      try {
        await Promise.all([loadPendientes(), loadPromociones()]);
      } catch (loadError) {
        if (mounted) setError("No se pudieron cargar los cobros pendientes.");
      } finally {
        if (mounted) setLoading(false);
      }
    };

    bootstrap();
    const timer = setInterval(() => {
      loadPendientes().catch(() => undefined);
    }, 60000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!selected) {
      setManualDiscount(0);
      setSelectedPromotionId("");
      setMetodo("");
      setReferencia("");
    }
  }, [selected]);

  const subtotal = Number(selected?.precio_estimado || 0);
  const promotion = promociones.find((item) => String(item.id) === String(selectedPromotionId));
  const promotionDiscount = useMemo(() => {
    if (!promotion) return 0;
    const valor = Number(promotion.valor || 0);
    return promotion.tipo === "porcentaje" ? subtotal * (valor / 100) : valor;
  }, [promotion, subtotal]);
  const discount = promotion ? promotionDiscount : Number(manualDiscount || 0);
  const total = Math.max(0, subtotal - discount);
  const requiresReference = metodo === "qr" || metodo === "transferencia";
  const canSubmit = Boolean(selected && metodo && (!requiresReference || referencia.trim()));

  const openModal = (item) => {
    setSelected(item);
    setManualDiscount(0);
    setSelectedPromotionId("");
    setMetodo("");
    setReferencia("");
    setError("");
  };

  const closeModal = () => {
    setSelected(null);
    setReceipt(null);
  };

  const submitPayment = async (event) => {
    event.preventDefault();
    if (!selected || !canSubmit) return;
    setPaymentLoading(true);
    setError("");
    try {
      const payload = {
        metodo_pago: metodo,
        referencia_transaccion: requiresReference ? referencia.trim() : undefined,
        descuento: promotion ? undefined : Number(manualDiscount || 0),
        promocion_id: promotion ? promotion.id : undefined,
      };
      const response = await apiPagarCita(selected.cita_id, payload);
      const recibo = response.factura_id ? await apiGetReciboCobro(response.factura_id) : response;
      setReceipt(recibo);
      setSelected(null);
      await loadPendientes();
    } catch (paymentError) {
      const message = paymentError?.response?.data?.message || paymentError?.response?.data?.details?.errores?.[0] || "No se pudo registrar el pago.";
      setError(message);
    } finally {
      setPaymentLoading(false);
    }
  };

  const selectedReceipt = receipt || null;

  return (
    <section className="agenda-card agenda-wide">
      <style>{`
        @media print {
          body > *:not(.recibo-container) { display: none !important; }
          .recibo-container { display: block !important; }
        }
      `}</style>

      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "start" }}>
        <div>
          <p className="calendar-kicker">Cobros y caja</p>
          <h3 style={{ marginBottom: 6 }}>Pendientes por cobrar</h3>
          <p style={{ margin: 0, color: "rgba(255,255,255,0.7)" }}>Ordenados por mayor tiempo de espera.</p>
        </div>
        <button type="button" className="secondary-button" onClick={loadPendientes} disabled={loading}>
          {loading ? "Actualizando..." : "Refrescar"}
        </button>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}

      <div style={{ display: "grid", gap: 14, marginTop: 18 }}>
        {!pendientes.length ? <div className="admin-empty">Sin cobros pendientes.</div> : null}
        {pendientes.map((item) => {
          const waitBadge = buildWaitBadge(readMinutes(item.minutos_espera));
          return (
            <article
              key={item.cita_id}
              style={{
                display: "grid",
                gridTemplateColumns: "88px minmax(0,1fr) auto",
                gap: 14,
                alignItems: "center",
                padding: 14,
                borderRadius: 20,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <div style={{ width: 88, height: 88, borderRadius: 20, overflow: "hidden", background: "rgba(255,255,255,0.06)", display: "grid", placeItems: "center" }}>
                {item.foto_url ? <img src={item.foto_url} alt={item.mascota_nombre} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : <span style={{ fontSize: 28 }}>🐾</span>}
              </div>

              <div style={{ display: "grid", gap: 6 }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                  <strong style={{ fontSize: 18 }}>{item.mascota_nombre || "Mascota"}</strong>
                  {waitBadge ? (
                    <span style={{ borderRadius: 999, padding: "4px 10px", fontSize: 12, fontWeight: 700, background: waitBadge.tone === "danger" ? "rgba(220,38,38,0.2)" : "rgba(249,115,22,0.16)", color: waitBadge.tone === "danger" ? "#fca5a5" : "#fdba74" }}>
                      {waitBadge.text}
                    </span>
                  ) : null}
                </div>
                <div style={{ color: "rgba(255,255,255,0.72)" }}>{item.cliente_nombre || "Cliente"}</div>
                <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 13 }}>
                  {item.servicio || "Servicio"} · {item.groomer || "Sin groomer"}
                </div>
                <div style={{ fontWeight: 700, color: "#1D9E75" }}>{money(item.precio_estimado)}</div>
              </div>

              <div style={{ display: "grid", gap: 8, justifyItems: "end" }}>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", textAlign: "right" }}>
                  Espera: {Math.round(readMinutes(item.minutos_espera))} min
                </div>
                <button type="button" className="primary-button" onClick={() => openModal(item)}>
                  💰 Cobrar
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {selected ? (
        <div className="modal-backdrop" style={{ zIndex: 50 }}>
          <div className="modal-card" style={{ width: "min(980px, calc(100vw - 24px))", maxHeight: "92vh", overflowY: "auto" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Registrar pago</p>
                <h4 style={{ margin: 0 }}>{selected.mascota_nombre} · {selected.cliente_nombre}</h4>
                <div style={{ color: "rgba(255,255,255,0.7)", marginTop: 4 }}>{selected.servicio}</div>
              </div>
              <button type="button" className="ghost-button" onClick={closeModal}>Cerrar</button>
            </div>

            <form onSubmit={submitPayment} style={{ display: "grid", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)" }}>
                  <div style={{ color: "rgba(255,255,255,0.68)", fontSize: 13 }}>Monto a cobrar</div>
                  <div style={{ fontSize: 28, fontWeight: 700 }}>{money(subtotal)}</div>
                </div>
                <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)" }}>
                  <div style={{ color: "rgba(255,255,255,0.68)", fontSize: 13 }}>Descuento</div>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={promotion ? promotionDiscount.toFixed(2) : manualDiscount}
                    onChange={(event) => setManualDiscount(event.target.value)}
                    disabled={Boolean(promotion)}
                    style={{ width: "100%", marginTop: 8 }}
                  />
                  {promotion ? <div style={{ marginTop: 8, color: "#86efac" }}>Promoción aplicada: {promotion.nombre}</div> : null}
                </div>
                <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)" }}>
                  <div style={{ color: "rgba(255,255,255,0.68)", fontSize: 13 }}>Total final</div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: "#1D9E75" }}>{money(total)}</div>
                </div>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                <label style={{ fontWeight: 600 }}>Promoción opcional</label>
                  <select value={selectedPromotionId} onChange={(event) => setSelectedPromotionId(event.target.value)} style={{ width: "100%", marginTop: 8 }}>
                    <option value="">Sin promoción</option>
                  {promociones.map((promo) => (
                    <option key={promo.id} value={promo.id}>
                      {promo.nombre} · {promo.tipo === "porcentaje" ? `${Number(promo.valor)}%` : money(promo.valor)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: 600 }}>Método de pago</label>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
                  {[
                    { key: "efectivo", label: "💵 Efectivo" },
                    { key: "qr", label: "📱 QR" },
                    { key: "transferencia", label: "🏦 Transferencia" },
                  ].map((item) => (
                    <button
                      type="button"
                      key={item.key}
                      onClick={() => setMetodo(item.key)}
                      style={{
                        border: `1px solid ${metodo === item.key ? "#1D9E75" : "rgba(255,255,255,0.18)"}`,
                        background: metodo === item.key ? "rgba(29,158,117,0.14)" : "rgba(255,255,255,0.04)",
                        color: "inherit",
                        borderRadius: 14,
                        padding: "12px 16px",
                        fontWeight: 700,
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {metodo === "qr" ? (
                <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 16, textAlign: "center", background: "rgba(255,255,255,0.03)" }}>
                  <p style={{ fontSize: 24, margin: 0 }}>📱</p>
                  <p style={{ fontSize: 13, margin: "8px 0 0" }}>Número QR del spa: {QR_NUMBER}</p>
                  <p style={{ fontSize: 12, color: "rgba(255,255,255,0.66)", margin: "6px 0 0" }}>El cliente escanea el QR y confirma el pago.</p>
                  <label style={{ display: "block", textAlign: "left", marginTop: 14 }}>
                    Código de confirmación *
                      <input value={referencia} onChange={(event) => setReferencia(event.target.value)} style={{ width: "100%", marginTop: 6, padding: "10px 12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.04)" }} />
                  </label>
                </div>
              ) : null}

              {metodo === "transferencia" ? (
                <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 16, background: "rgba(255,255,255,0.03)" }}>
                  <div style={{ lineHeight: 1.8 }}>
                    <div><strong>Banco:</strong> {BANK_NAME}</div>
                    <div><strong>Cuenta:</strong> {ACCOUNT_NUMBER}</div>
                    <div><strong>A nombre de:</strong> {SPA_NAME}</div>
                  </div>
                  <label style={{ display: "block", marginTop: 14 }}>
                    Número de referencia *
                      <input value={referencia} onChange={(event) => setReferencia(event.target.value)} style={{ width: "100%", marginTop: 6, padding: "10px 12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.18)", background: "rgba(255,255,255,0.04)" }} />
                  </label>
                </div>
              ) : null}

              <div style={{ fontSize: 24, fontWeight: 600, color: "#1D9E75", textAlign: "center", margin: "8px 0" }}>
                Bs. {total.toFixed(2)}
              </div>

              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button type="submit" className="primary-button" disabled={!canSubmit || paymentLoading}>
                  {paymentLoading ? "Registrando..." : "✓ Registrar pago"}
                </button>
                <button type="button" className="secondary-button" onClick={closeModal}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {selectedReceipt ? (
        <div className="modal-backdrop recibo-container" style={{ zIndex: 60 }}>
          <div className="modal-card recibo-container" style={{ width: "min(820px, calc(100vw - 24px))", background: "white", color: "#0f1722" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", borderBottom: "1px solid #e2e8f0", paddingBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0 }}>{SPA_NAME}</h3>
                <div style={{ color: "#475569" }}>Recibo de pago</div>
              </div>
              <button type="button" className="ghost-button" onClick={() => apiGetReciboCobro(selectedReceipt.factura_id).then(setReceipt).catch(() => undefined)}>
                Reimprimir
              </button>
            </div>

            <div style={{ display: "grid", gap: 8, marginTop: 16 }}>
              {[
                ["Factura", selectedReceipt.factura_numero],
                ["Fecha emisión", selectedReceipt.fecha_emision],
                ["Cliente", selectedReceipt.cliente],
                ["Mascota", selectedReceipt.mascota],
                ["Servicio", selectedReceipt.servicio],
                ["Groomer", selectedReceipt.groomer],
                ["Subtotal", money(selectedReceipt.subtotal)],
                ["Descuento", money(selectedReceipt.descuento)],
                ["Total", money(selectedReceipt.total)],
                ["Método de pago", selectedReceipt.metodo_pago],
                ["Referencia", selectedReceipt.referencia_transaccion || "-"] ,
                ["Registrado por", selectedReceipt.registrado_por || "-"] ,
              ].map(([label, value]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", gap: 12, borderBottom: label === "Total" ? "2px solid #0f1722" : "1px solid #e2e8f0", paddingBottom: 8, fontWeight: label === "Total" ? 700 : 500, fontSize: label === "Total" ? 18 : 14 }}>
                  <span>{label}</span>
                  <span>{value}</span>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 18 }}>
              <button type="button" className="primary-button" onClick={() => window.print()}>
                🖨 Imprimir
              </button>
              <button type="button" className="secondary-button" onClick={() => setReceipt(null)}>
                ✓ Cerrar
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
