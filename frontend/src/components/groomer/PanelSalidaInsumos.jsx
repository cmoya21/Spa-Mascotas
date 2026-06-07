import { useEffect, useMemo, useState } from "react";

import Button from "../shared/Button";
import {
  apiConfirmarTodosInsumosFicha,
  apiConfirmarUsoInsumo,
  apiListInsumosFicha,
  apiProductosDisponiblesParaInsumos,
  apiRegistrarInsumo,
} from "../../api/insumosApi";

const EMPTY_ROW = { producto_id: "", cantidad_entregada: "", notas: "" };

export default function PanelSalidaInsumos({ fichaId, servicioId, fichaEstado, onInsumosSaved, readOnly = false }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState([EMPTY_ROW]);
  const [registrados, setRegistrados] = useState([]);
  const [productos, setProductos] = useState([]);
  const [confirmDrafts, setConfirmDrafts] = useState({});

  const productosMap = useMemo(() => {
    const map = new Map();
    (productos || []).forEach((p) => map.set(String(p.id), p));
    return map;
  }, [productos]);

  const sugeridos = useMemo(() => (productos || []).filter((p) => p.es_sugerido), [productos]);
  const pendientes = useMemo(() => (registrados || []).filter((item) => item.estado === "entregado"), [registrados]);
  const confirmacionHabilitada = !readOnly && fichaEstado === "en_curso" && registrados.length > 0;

  const cargar = async () => {
    if (!fichaId) return;
    setLoading(true);
    setError("");
    try {
      const [existentes, disponibles] = await Promise.all([
        apiListInsumosFicha(fichaId),
        apiProductosDisponiblesParaInsumos({ servicio_id: servicioId }),
      ]);
      setRegistrados(Array.isArray(existentes) ? existentes : []);
      setProductos(Array.isArray(disponibles) ? disponibles : []);
      setConfirmDrafts((prev) => {
        const next = { ...prev };
        (Array.isArray(existentes) ? existentes : []).forEach((item) => {
          if (!next[item.id]) {
            next[item.id] = {
              cantidad_usada: item.cantidad_usada ?? "",
              cantidad_devuelta: item.cantidad_devuelta ?? "",
              cantidad_desperdicio: item.cantidad_desperdicio ?? "",
              notas: item.notas || "",
            };
          }
        });
        return next;
      });
    } catch (err) {
      setError("No se pudo cargar insumos de salida.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
  }, [fichaId, servicioId]);

  const addRow = (preset) => {
    setRows((prev) => [...prev, preset || { ...EMPTY_ROW }]);
  };

  const removeRow = (idx) => {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  };

  const setRowField = (idx, field, value) => {
    setRows((prev) => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
  };

  const guardarSalida = async () => {
    if (!fichaId) return;
    const payloadRows = rows
      .filter((r) => r.producto_id && r.cantidad_entregada)
      .map((r) => ({
        producto_id: Number(r.producto_id),
        cantidad_entregada: Number(r.cantidad_entregada),
        notas: r.notas || "",
      }));

    if (!payloadRows.length) {
      setError("Agrega al menos un insumo válido.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await apiRegistrarInsumo({ ficha_id: fichaId, insumos: payloadRows });
      await cargar();
      setRows([EMPTY_ROW]);
      onInsumosSaved?.();
    } catch (err) {
      setError(err?.response?.data?.mensaje || err?.response?.data?.message || "No se pudo registrar la salida de insumos.");
    } finally {
      setSaving(false);
    }
  };

  const addSuggested = (producto) => {
    addRow({
      producto_id: String(producto.id),
      cantidad_entregada: producto.cantidad_sugerida ? String(producto.cantidad_sugerida) : "",
      notas: "",
    });
  };

  const setConfirmField = (salidaId, field, value) => {
    setConfirmDrafts((prev) => ({
      ...prev,
      [salidaId]: {
        ...(prev[salidaId] || {}),
        [field]: value,
      },
    }));
  };

  const asNumber = (value) => {
    if (value === "" || value === null || value === undefined) return 0;
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  };

  const totalConfirmacion = (salidaId) => {
    const draft = confirmDrafts[salidaId] || {};
    return asNumber(draft.cantidad_usada) + asNumber(draft.cantidad_devuelta) + asNumber(draft.cantidad_desperdicio);
  };

  const confirmarUsoFila = async (item) => {
    const draft = confirmDrafts[item.id] || {};
    const payload = {
      cantidad_usada: asNumber(draft.cantidad_usada),
      cantidad_devuelta: asNumber(draft.cantidad_devuelta),
      cantidad_desperdicio: asNumber(draft.cantidad_desperdicio),
      notas: draft.notas || "",
    };
    setConfirming(true);
    setError("");
    try {
      await apiConfirmarUsoInsumo(item.id, payload);
      await cargar();
      onInsumosSaved?.();
    } catch (err) {
      setError(err?.response?.data?.mensaje || "No se pudo confirmar uso del insumo.");
    } finally {
      setConfirming(false);
    }
  };

  const confirmarTodos = async () => {
    const payload = {
      insumos: pendientes.map((item) => {
        const draft = confirmDrafts[item.id] || {};
        return {
          salida_id: item.id,
          cantidad_usada: asNumber(draft.cantidad_usada),
          cantidad_devuelta: asNumber(draft.cantidad_devuelta),
          cantidad_desperdicio: asNumber(draft.cantidad_desperdicio),
        };
      }),
    };

    setConfirming(true);
    setError("");
    try {
      await apiConfirmarTodosInsumosFicha(fichaId, payload);
      await cargar();
      onInsumosSaved?.();
    } catch (err) {
      setError(err?.response?.data?.mensaje || "No se pudo confirmar todos los insumos.");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
      <div>
        <h3 style={{ margin: 0 }}>Insumos recibidos</h3>
        <p style={{ margin: "6px 0 0", color: "#475569" }}>
          Registro de salida previo al servicio. Queda trazado en el log del groomer.
        </p>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <div className="admin-empty">Cargando insumos...</div> : null}

      {!loading && sugeridos.length ? (
        <div className="alert" style={{ background: "rgba(90,167,255,0.12)", color: "#d8ebff" }}>
          <div style={{ marginBottom: 8, fontWeight: 700 }}>📋 Insumos sugeridos para el servicio</div>
          <div style={{ display: "grid", gap: 8 }}>
            {sugeridos.map((p) => (
              <div key={`suggest-${p.id}`} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <span>{p.nombre} · Stock: {p.stock}</span>
                {!readOnly ? (
                  <button type="button" className="ghost-button" onClick={() => addSuggested(p)}>+ Agregar</button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {!loading && registrados.length ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th style={{ padding: "10px 8px" }}>Producto</th>
                <th style={{ padding: "10px 8px" }}>Cantidad entregada</th>
                <th style={{ padding: "10px 8px" }}>Notas</th>
                <th style={{ padding: "10px 8px" }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {registrados.map((item) => (
                <tr key={`reg-${item.id}`}>
                  <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                  <td style={{ padding: 8 }}>{item.cantidad_entregada}</td>
                  <td style={{ padding: 8 }}>{item.notas || "-"}</td>
                  <td style={{ padding: 8 }}><span className="pill">{item.estado === "usado" ? "Confirmado" : item.estado}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {confirmacionHabilitada ? (
        <section className="groomer-card" style={{ display: "grid", gap: 12 }}>
          <div>
            <h3 style={{ margin: 0 }}>Confirmación de uso</h3>
            <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>
              Confirma cuánto se usó realmente durante el servicio.
            </p>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th style={{ padding: "10px 8px" }}>Producto</th>
                  <th style={{ padding: "10px 8px" }}>Entregada</th>
                  <th style={{ padding: "10px 8px" }}>Usada</th>
                  <th style={{ padding: "10px 8px" }}>Devuelto</th>
                  <th style={{ padding: "10px 8px" }}>Desperdicio</th>
                  <th style={{ padding: "10px 8px" }}>Total</th>
                  <th style={{ padding: "10px 8px" }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {registrados.map((item) => {
                  if (item.estado === "usado") {
                    return (
                      <tr key={`confirm-${item.id}`}>
                        <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                        <td style={{ padding: 8 }}>{item.cantidad_entregada}</td>
                        <td style={{ padding: 8 }}>{item.cantidad_usada ?? 0}</td>
                        <td style={{ padding: 8 }}>{item.cantidad_devuelta ?? 0}</td>
                        <td style={{ padding: 8 }}>{item.cantidad_desperdicio ?? 0}</td>
                        <td style={{ padding: 8 }}>{Number(item.cantidad_usada || 0) + Number(item.cantidad_devuelta || 0) + Number(item.cantidad_desperdicio || 0)}</td>
                        <td style={{ padding: 8 }}><span className="pill" style={{ background: "rgba(56,189,93,0.2)", color: "#bff5ca" }}>Confirmado</span></td>
                      </tr>
                    );
                  }

                  const draft = confirmDrafts[item.id] || {};
                  const total = totalConfirmacion(item.id);
                  const excede = total > Number(item.cantidad_entregada || 0);
                  return (
                    <tr key={`confirm-${item.id}`}>
                      <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                      <td style={{ padding: 8 }}>{item.cantidad_entregada}</td>
                      <td style={{ padding: 8 }}>
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          value={draft.cantidad_usada ?? ""}
                          onChange={(e) => setConfirmField(item.id, "cantidad_usada", e.target.value)}
                          style={{ width: 110 }}
                          required
                        />
                      </td>
                      <td style={{ padding: 8 }}>
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          value={draft.cantidad_devuelta ?? ""}
                          onChange={(e) => setConfirmField(item.id, "cantidad_devuelta", e.target.value)}
                          style={{ width: 110 }}
                        />
                      </td>
                      <td style={{ padding: 8 }}>
                        <input
                          type="number"
                          step="0.001"
                          min="0"
                          value={draft.cantidad_desperdicio ?? ""}
                          onChange={(e) => setConfirmField(item.id, "cantidad_desperdicio", e.target.value)}
                          style={{ width: 110 }}
                        />
                      </td>
                      <td style={{ padding: 8, color: excede ? "#ffb4b4" : "inherit", fontWeight: excede ? 700 : 400 }}>
                        {total.toFixed(3)}
                        {excede ? <div style={{ fontSize: 12 }}>⚠ Supera lo entregado</div> : null}
                      </td>
                      <td style={{ padding: 8 }}>
                        <button type="button" className="ghost-button" disabled={confirming || excede} onClick={() => confirmarUsoFila(item)}>
                          ✓ Confirmar uso
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {pendientes.length ? (
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Button type="button" onClick={confirmarTodos} disabled={confirming}>✓ Confirmar todos</Button>
            </div>
          ) : null}
        </section>
      ) : null}

      {!readOnly ? (
        <>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left" }}>
                  <th style={{ padding: "10px 8px" }}>Producto</th>
                  <th style={{ padding: "10px 8px" }}>Cantidad entregada</th>
                  <th style={{ padding: "10px 8px" }}>Notas</th>
                  <th style={{ padding: "10px 8px" }}>Estado</th>
                  <th style={{ padding: "10px 8px" }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => {
                  const producto = productosMap.get(String(row.producto_id));
                  return (
                    <tr key={`draft-${idx}`}>
                      <td style={{ padding: 8 }}>
                        <input
                          list="productos-salida"
                          value={row.producto_id}
                          onChange={(e) => setRowField(idx, "producto_id", e.target.value)}
                          placeholder="ID producto"
                          style={{ width: "100%" }}
                        />
                        <div style={{ fontSize: 12, color: "#475569", marginTop: 6 }}>
                          {producto ? `${producto.nombre} · Stock: ${producto.stock}` : "Selecciona un producto"}
                        </div>
                      </td>
                      <td style={{ padding: 8 }}>
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={row.cantidad_entregada}
                          onChange={(e) => setRowField(idx, "cantidad_entregada", e.target.value)}
                          style={{ width: "100%" }}
                        />
                      </td>
                      <td style={{ padding: 8 }}>
                        <input
                          value={row.notas}
                          onChange={(e) => setRowField(idx, "notas", e.target.value)}
                          placeholder="Notas opcionales"
                          style={{ width: "100%" }}
                        />
                      </td>
                      <td style={{ padding: 8 }}><span className="pill">entregado</span></td>
                      <td style={{ padding: 8 }}>
                        <button type="button" className="ghost-button" onClick={() => removeRow(idx)}>×</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <datalist id="productos-salida">
              {productos.map((p) => (
                <option key={`p-${p.id}`} value={String(p.id)} label={`${p.nombre} · ${p.sku || "sin SKU"} · stock ${p.stock}`} />
              ))}
            </datalist>
          </div>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Button type="button" onClick={() => addRow()} disabled={saving}>+ Agregar insumo</Button>
            <Button type="button" onClick={guardarSalida} disabled={saving}>
              {saving ? "Registrando..." : (registrados.length ? "Actualizar insumos" : "📦 Registrar salida")}
            </Button>
          </div>
        </>
      ) : null}
    </section>
  );
}
