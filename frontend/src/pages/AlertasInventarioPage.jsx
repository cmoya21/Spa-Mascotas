import { useEffect, useState } from "react";

import Button from "../components/shared/Button";
import InventoryAlertBadge from "../components/shared/InventoryAlertBadge";
import {
  apiGetAlertasInventarioResumen,
} from "../api/alertasApi";
import { apiReabastecerProducto } from "../api/tiendaApi";

const barColor = (producto) => (producto.stock <= producto.stock_minimo * 0.5 ? "#dc2626" : "#f59e0b");

export default function AlertasInventarioPage() {
  const [data, setData] = useState({ criticos_ahora: [], alertas_recientes: [], total_criticos: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [target, setTarget] = useState(null);
  const [cantidad, setCantidad] = useState(1);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGetAlertasInventarioResumen();
      setData(response);
    } catch (loadError) {
      setError("No se pudieron cargar las alertas de inventario.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submitRestock = async () => {
    if (!target) return;
    setError("");
    try {
      await apiReabastecerProducto(target.id, { cantidad_ingresada: Number(cantidad) });
      setTarget(null);
      setCantidad(1);
      await load();
    } catch (restockError) {
      setError(restockError?.response?.data?.message || "No se pudo reabastecer el producto.");
    }
  };

  return (
    <section className="agenda-card agenda-wide">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "start" }}>
        <div>
          <p className="calendar-kicker">Alertas de stock</p>
          <h3 style={{ marginBottom: 6 }}>Productos críticos ahora</h3>
          <InventoryAlertBadge count={data.total_criticos} />
        </div>
        <Button onClick={load}>{loading ? "Actualizando..." : "Refrescar"}</Button>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}

      <div style={{ display: "grid", gap: 16, marginTop: 18 }}>
        {(data.criticos_ahora || []).map((item) => {
          const percent = item.stock_minimo ? Math.max(0, Math.min(100, (item.stock / item.stock_minimo) * 100)) : 0;
          return (
            <article key={item.id} style={{ padding: 16, borderRadius: 18, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <div>
                  <strong>{item.nombre}</strong>
                  <div style={{ color: "rgba(255,255,255,0.72)", fontSize: 13 }}>{item.sku || "Sin SKU"}</div>
                </div>
                <button type="button" className="link-button" onClick={() => setTarget(item)}>+ Reabastecer</button>
              </div>
              <div style={{ marginTop: 10, background: "rgba(255,255,255,0.08)", borderRadius: 999, height: 10, overflow: "hidden" }}>
                <div style={{ width: `${percent}%`, height: "100%", background: barColor(item) }} />
              </div>
              <div style={{ marginTop: 8, color: "rgba(255,255,255,0.72)" }}>
                {item.stock} unidades / mínimo {item.stock_minimo}
              </div>
            </article>
          );
        })}
        {!data.criticos_ahora?.length ? <div className="admin-empty">No hay productos críticos.</div> : null}
      </div>

      <div style={{ marginTop: 28 }}>
        <h3>Historial de alertas (últimos 7 días)</h3>
        <div className="admin-table" style={{ marginTop: 12 }}>
          {(data.alertas_recientes || []).map((item, index) => (
            <div key={`${item.creado_en}-${index}`} className="admin-row">
              <span>{item.creado_en ? new Date(item.creado_en).toLocaleString() : "-"}</span>
              <span>{item.nombre}</span>
              <span>{item.sku || "-"}</span>
              <span>{item.stock_al_momento ?? "-"}</span>
            </div>
          ))}
          {!data.alertas_recientes?.length ? <div className="admin-empty">Sin alertas recientes.</div> : null}
        </div>
      </div>

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
              Cantidad ingresada
              <input type="number" min="1" value={cantidad} onChange={(event) => setCantidad(event.target.value)} />
            </label>
            <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Button onClick={submitRestock}>Confirmar ingreso</Button>
              <button type="button" className="secondary-button" onClick={() => setTarget(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}