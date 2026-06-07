import { useEffect, useMemo, useState } from "react";

import { apiGetAlertasInventarioResumen, apiGetConsumoPorGroomer, apiReabastecerProductoAlerta } from "../../api/alertasApi";

function toCsv(rows) {
  const header = ["Groomer", "Producto", "Total usado", "Total desperdicio", "% Merma", "Servicios"];
  const data = rows.map((item) => [
    item.groomer,
    item.producto,
    item.total_usado,
    item.total_desperdicio,
    item.porcentaje_merma,
    item.total_servicios,
  ]);
  return [header, ...data]
    .map((cols) => cols.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
}

const TABS = {
  STOCK: "stock",
  ALTO_CONSUMO: "alto_consumo",
  GROOMER: "groomer",
  REABASTECER: "reabastecer",
};

export default function PanelAlertas() {
  const [tab, setTab] = useState(TABS.STOCK);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [alertas, setAlertas] = useState({
    bajo_stock_tienda: [],
    alto_consumo: [],
    recomendaciones: [],
    total_criticos: 0,
    total_alto_consumo: 0,
    resumen: { urgentes: 0, altos: 0, medios: 0 },
  });

  const [fechaInicio, setFechaInicio] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [fechaFin, setFechaFin] = useState(() => new Date().toISOString().slice(0, 10));
  const [consumoGroomer, setConsumoGroomer] = useState([]);

  const [target, setTarget] = useState(null);
  const [cantidad, setCantidad] = useState(1);
  const [notas, setNotas] = useState("");

  const cargarAlertas = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiGetAlertasInventarioResumen();
      setAlertas({
        bajo_stock_tienda: data.bajo_stock_tienda || [],
        alto_consumo: data.alto_consumo || [],
        recomendaciones: data.recomendaciones || [],
        total_criticos: data.total_criticos || 0,
        total_alto_consumo: data.total_alto_consumo || 0,
        resumen: data.resumen || { urgentes: 0, altos: 0, medios: 0 },
      });
    } catch {
      setError("No se pudieron cargar las alertas de inventario.");
    } finally {
      setLoading(false);
    }
  };

  const cargarConsumoGroomer = async () => {
    try {
      const data = await apiGetConsumoPorGroomer({ fecha_inicio: fechaInicio, fecha_fin: fechaFin });
      setConsumoGroomer(Array.isArray(data) ? data : []);
    } catch {
      setConsumoGroomer([]);
      setError("No se pudo cargar consumo por groomer.");
    }
  };

  useEffect(() => {
    cargarAlertas();
    const intervalId = setInterval(cargarAlertas, 5 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (tab === TABS.GROOMER) {
      cargarConsumoGroomer();
    }
  }, [tab]);

  const csvData = useMemo(() => toCsv(consumoGroomer), [consumoGroomer]);

  const exportarCsv = () => {
    const blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "consumo_por_groomer.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const colorPrioridad = (item) => {
    const stock = Number(item.stock || 0);
    const minimo = Number(item.stock_minimo || 0);
    if (stock <= 0) return "#ef4444";
    if (stock <= minimo * 0.5) return "#f97316";
    return "#eab308";
  };

  const badgeAltoConsumo = (porcentaje) => {
    if (porcentaje > 50) return { text: "Alto desperdicio", color: "#ef4444" };
    if (porcentaje >= 20) return { text: "Merma significativa", color: "#f97316" };
    return { text: "Merma menor", color: "#eab308" };
  };

  const confirmarReabastecer = async () => {
    if (!target) return;
    setError("");
    try {
      await apiReabastecerProductoAlerta(target.id, { cantidad: Number(cantidad), notas });
      setTarget(null);
      setCantidad(1);
      setNotas("");
      await cargarAlertas();
    } catch {
      setError("No se pudo reabastecer el producto.");
    }
  };

  return (
    <div className="page-shell" style={{ padding: 24, display: "grid", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Panel de alertas de inventario</h2>
        <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.72)" }}>Monitoreo integral de stock, consumo y merma.</p>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className={tab === TABS.STOCK ? "side-nav-button active" : "side-nav-button"} onClick={() => setTab(TABS.STOCK)}>
          🔴 Stock crítico ({alertas.total_criticos || 0})
        </button>
        <button type="button" className={tab === TABS.ALTO_CONSUMO ? "side-nav-button active" : "side-nav-button"} onClick={() => setTab(TABS.ALTO_CONSUMO)}>
          ⚡ Alto consumo ({alertas.total_alto_consumo || 0})
        </button>
        <button type="button" className={tab === TABS.GROOMER ? "side-nav-button active" : "side-nav-button"} onClick={() => setTab(TABS.GROOMER)}>
          📊 Por groomer
        </button>
        <button type="button" className={tab === TABS.REABASTECER ? "side-nav-button active" : "side-nav-button"} onClick={() => setTab(TABS.REABASTECER)}>
          📦 Reabastecer
        </button>
      </div>

      {tab === TABS.STOCK ? (
        <section className="agenda-card" style={{ display: "grid", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
            <div className="alert" style={{ background: "rgba(239,68,68,0.16)", color: "#ffd3d3" }}>🔴 Urgentes (stock=0): {alertas.resumen.urgentes || 0}</div>
            <div className="alert" style={{ background: "rgba(249,115,22,0.16)", color: "#ffd9bf" }}>🟠 Críticos (&lt;50% min): {alertas.resumen.altos || 0}</div>
            <div className="alert" style={{ background: "rgba(234,179,8,0.16)", color: "#fff0b8" }}>🟡 Bajos (≤ min): {alertas.resumen.medios || 0}</div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th style={{ padding: 8 }}>Nombre</th>
                  <th style={{ padding: 8 }}>SKU</th>
                  <th style={{ padding: 8 }}>Stock actual</th>
                  <th style={{ padding: 8 }}>Stock mínimo</th>
                  <th style={{ padding: 8 }}>Faltantes</th>
                  <th style={{ padding: 8 }}>Prioridad</th>
                  <th style={{ padding: 8 }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {(alertas.bajo_stock_tienda || []).map((item) => {
                  const stock = Number(item.stock || 0);
                  const min = Number(item.stock_minimo || 1);
                  const percent = Math.max(0, Math.min(100, (stock / min) * 100));
                  return (
                    <tr key={item.id}>
                      <td style={{ padding: 8 }}>{item.nombre}</td>
                      <td style={{ padding: 8 }}>{item.sku || "-"}</td>
                      <td style={{ padding: 8 }}>{item.stock}</td>
                      <td style={{ padding: 8 }}>{item.stock_minimo}</td>
                      <td style={{ padding: 8 }}>{item.unidades_faltantes}</td>
                      <td style={{ padding: 8 }}>{item.prioridad}</td>
                      <td style={{ padding: 8 }}>
                        <button type="button" className="ghost-button" onClick={() => setTarget(item)}>+ Reabastecer</button>
                      </td>
                      <td style={{ padding: 8, minWidth: 180 }}>
                        <div style={{ background: "rgba(255,255,255,0.12)", borderRadius: 999, height: 10, overflow: "hidden" }}>
                          <div style={{ width: `${percent}%`, height: "100%", background: colorPrioridad(item) }} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {!alertas.bajo_stock_tienda?.length ? (
                  <tr><td colSpan={8} style={{ padding: 8 }}>Sin productos críticos.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {tab === TABS.ALTO_CONSUMO ? (
        <section className="agenda-card" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th style={{ padding: 8 }}>Groomer</th>
                <th style={{ padding: 8 }}>Producto</th>
                <th style={{ padding: 8 }}>% Desperdicio</th>
                <th style={{ padding: 8 }}>Fecha</th>
                <th style={{ padding: 8 }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {(alertas.alto_consumo || []).map((item, idx) => {
                const badge = badgeAltoConsumo(Number(item.porcentaje || 0));
                return (
                  <tr key={`${item.groomer_id}-${item.producto_id}-${idx}`}>
                    <td style={{ padding: 8 }}>{item.groomer_nombre || "-"}</td>
                    <td style={{ padding: 8 }}>{item.producto_nombre || "-"}</td>
                    <td style={{ padding: 8 }}>{item.porcentaje}%</td>
                    <td style={{ padding: 8 }}>{item.creado_en ? new Date(item.creado_en).toLocaleString() : "-"}</td>
                    <td style={{ padding: 8 }}>
                      <span className="pill" style={{ background: `${badge.color}33`, color: badge.color }}>{badge.text}</span>
                    </td>
                  </tr>
                );
              })}
              {!alertas.alto_consumo?.length ? (
                <tr><td colSpan={5} style={{ padding: 8 }}>Sin alertas de alto consumo.</td></tr>
              ) : null}
            </tbody>
          </table>
        </section>
      ) : null}

      {tab === TABS.GROOMER ? (
        <section className="agenda-card" style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
            <button type="button" className="ghost-button" onClick={cargarConsumoGroomer}>Filtrar</button>
            <button type="button" className="ghost-button" onClick={exportarCsv}>Exportar CSV</button>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th style={{ padding: 8 }}>Groomer</th>
                  <th style={{ padding: 8 }}>Producto</th>
                  <th style={{ padding: 8 }}>Total usado</th>
                  <th style={{ padding: 8 }}>Total desperdicio</th>
                  <th style={{ padding: 8 }}>% Merma</th>
                </tr>
              </thead>
              <tbody>
                {consumoGroomer.map((item, idx) => (
                  <tr key={`${item.groomer_id}-${item.producto_id}-${idx}`}>
                    <td style={{ padding: 8 }}>{item.groomer}</td>
                    <td style={{ padding: 8 }}>{item.producto}</td>
                    <td style={{ padding: 8 }}>{item.total_usado}</td>
                    <td style={{ padding: 8 }}>{item.total_desperdicio}</td>
                    <td style={{ padding: 8 }}>{item.porcentaje_merma}%</td>
                  </tr>
                ))}
                {!consumoGroomer.length ? (
                  <tr><td colSpan={5} style={{ padding: 8 }}>Sin datos de consumo.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {tab === TABS.REABASTECER ? (
        <section className="agenda-card" style={{ display: "grid", gap: 12 }}>
          {(alertas.recomendaciones || []).map((item) => {
            const consumoMensual = Number(item.consumo_mensual || 0);
            const diasRestantes = consumoMensual > 0 ? Number(item.stock || 0) / (consumoMensual / 30) : Infinity;
            return (
              <div key={`rec-${item.id}`} className="alert" style={{ background: "rgba(255,255,255,0.05)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                  <strong>{item.nombre} · {item.sku || "sin SKU"}</strong>
                  <span className="pill">{item.prioridad}</span>
                </div>
                <div style={{ marginTop: 6 }}>Stock: {item.stock} / mínimo {item.stock_minimo}</div>
                <div>Consumo mensual: {consumoMensual.toFixed(2)}</div>
                <div style={{ color: diasRestantes < 7 ? "#ffb4b4" : "rgba(255,255,255,0.8)" }}>
                  {Number.isFinite(diasRestantes) ? `Se agotará en ${Math.max(0, diasRestantes).toFixed(1)} días` : "Se agotará en ∞ días"}
                </div>
              </div>
            );
          })}
          {!alertas.recomendaciones?.length ? <div className="admin-empty">Sin recomendaciones.</div> : null}
        </section>
      ) : null}

      {target ? (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ width: "min(560px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Reabastecer</p>
                <h4 style={{ margin: 0 }}>{target.nombre}</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setTarget(null)}>Cerrar</button>
            </div>
            <label>
              Cantidad
              <input type="number" min="1" value={cantidad} onChange={(event) => setCantidad(event.target.value)} />
            </label>
            <label>
              Notas
              <textarea rows={3} value={notas} onChange={(event) => setNotas(event.target.value)} style={{ width: "100%" }} />
            </label>
            <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button type="button" className="ghost-button" onClick={confirmarReabastecer}>Confirmar</button>
              <button type="button" className="secondary-button" onClick={() => setTarget(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      ) : null}

      {loading ? <div className="admin-empty">Cargando alertas...</div> : null}
    </div>
  );
}
