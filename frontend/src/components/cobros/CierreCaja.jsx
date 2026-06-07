import { useEffect, useMemo, useState } from "react";

import Button from "../shared/Button";
import { useAuthContext } from "../../context/AuthContext.jsx";
import { apiGetCierreCaja } from "../../api/cobrosApi";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

const exportarCSV = (fecha, datos) => {
  const headers = ["Hora", "Cliente", "Servicio", "Método", "Monto", "Referencia", "Factura"];
  const rows = (datos?.detalle || []).map((item) => [
    item.hora,
    item.cliente,
    item.servicio,
    item.metodo,
    item.monto,
    item.referencia || "",
    item.factura,
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","))
    .join("\n");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `cierre-caja-${fecha}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
};

export default function CierreCaja() {
  const { hasRole } = useAuthContext();
  const [fecha, setFecha] = useState(new Date().toISOString().split("T")[0]);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await apiGetCierreCaja(fecha);
      setData(res || null);
    } catch (err) {
      setError("No se pudo cargar el cierre de caja.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!hasRole("Admin")) return;
    fetchData();
  }, [fecha]);

  if (!hasRole("Admin")) return null;

  return (
    <section className="agenda-card agenda-wide">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "start" }}>
        <div>
          <p className="calendar-kicker">Cierre de caja</p>
          <h3 style={{ marginBottom: 6 }}>Resumen diario</h3>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <Button onClick={fetchData}>{loading ? "Cargando..." : "Actualizar"}</Button>
          <Button onClick={() => exportarCSV(fecha, data)} disabled={!data}>📥 Exportar CSV</Button>
        </div>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}

      {data ? (
        <div style={{ display: "grid", gap: 18, marginTop: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
            {[
              ["💵 Efectivo", money(data.total_efectivo)],
              ["📱 QR", money(data.total_qr)],
              ["🏦 Transferencia", money(data.total_transferencia)],
              ["📊 Total general", money(data.total_general)],
            ].map(([label, value]) => (
              <article key={label} style={{ borderRadius: 18, padding: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{label}</div>
                <div style={{ fontSize: 24, fontWeight: 700, marginTop: 6 }}>{value}</div>
              </article>
            ))}
          </div>

          <div className="admin-table">
            <div className="admin-row admin-head">
              <span>Hora</span>
              <span>Cliente</span>
              <span>Servicio</span>
              <span>Método</span>
              <span>Monto</span>
              <span>Referencia</span>
              <span>Factura</span>
            </div>
            {(data.detalle || []).map((item, index) => (
              <div className="admin-row" key={`${item.factura}-${index}`}>
                <span>{item.hora}</span>
                <span>{item.cliente}</span>
                <span>{item.servicio}</span>
                <span className="pill">{item.metodo}</span>
                <span>{money(item.monto)}</span>
                <span>{item.referencia || "-"}</span>
                <span>{item.factura}</span>
              </div>
            ))}
            {!data.detalle?.length ? <div className="admin-empty">Sin transacciones para la fecha elegida.</div> : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
