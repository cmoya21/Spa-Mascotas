import { useEffect, useMemo, useState } from "react";

import Button from "../shared/Button";
import InputField from "../shared/InputField";

const EMPTY_ROW = { producto_id: "", cantidad: "", devuelto: "", desperdicio: "" };

export default function InsumosForm({
  fichaId,
  productos,
  initialItems,
  onSave,
  queryValue = "",
  onQueryChange,
  disabled = false,
}) {
  const [items, setItems] = useState(initialItems || []);
  const [draft, setDraft] = useState(EMPTY_ROW);

  useEffect(() => {
    setItems(initialItems || []);
  }, [initialItems]);

  const productosMap = useMemo(() => {
    const map = new Map();
    (productos || []).forEach((item) => map.set(String(item.id), item));
    return map;
  }, [productos]);

  const handleAdd = () => {
    if (!draft.producto_id || !draft.cantidad) return;
    const cantidad = parseFloat(draft.cantidad);
    if (Number.isNaN(cantidad) || cantidad <= 0) return;

    setItems((prev) => [
      ...prev,
      {
        producto_id: parseInt(draft.producto_id, 10),
        cantidad,
        devuelto: draft.devuelto === "" ? null : parseFloat(draft.devuelto),
        desperdicio: draft.desperdicio === "" ? null : parseFloat(draft.desperdicio),
      }
    ]);
    setDraft(EMPTY_ROW);
  };

  const handleRemove = (index) => {
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSave = (event) => {
    event.preventDefault();
    if (!fichaId) return;
    onSave(items);
  };

  return (
    <form onSubmit={handleSave} className="form-group">
      <div className="input-field">
        <label>Buscar producto</label>
        <div className="input-wrapper">
          <input
            value={queryValue}
            onChange={(event) => onQueryChange?.(event.target.value)}
            placeholder="Escribe al menos 2 caracteres"
            disabled={disabled}
          />
        </div>
        <datalist id="productos-insumos">
          {(productos || []).map((producto) => (
            <option
              key={producto.id}
              value={String(producto.id)}
              label={`${producto.nombre} · ${producto.sku || "sin SKU"} · stock ${producto.stock}`}
            />
          ))}
        </datalist>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: "10px 8px" }}>Producto</th>
              <th style={{ padding: "10px 8px" }}>Cantidad</th>
              <th style={{ padding: "10px 8px" }}>Devuelto</th>
              <th style={{ padding: "10px 8px" }}>Desperdicio</th>
              <th style={{ padding: "10px 8px" }}>Acción</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => {
              const producto = productosMap.get(String(item.producto_id));
              return (
                <tr key={`${item.producto_id || "row"}-${index}`}>
                  <td style={{ padding: 8, verticalAlign: "top" }}>
                    <input
                      list="productos-insumos"
                      value={item.producto_id}
                      onChange={(event) => {
                        const value = event.target.value;
                        setItems((prev) => prev.map((current, currentIndex) => currentIndex === index ? { ...current, producto_id: value } : current));
                      }}
                      placeholder="ID producto"
                      disabled={disabled}
                      style={{ width: "100%" }}
                    />
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginTop: 6 }}>
                      {producto ? `${producto.nombre} · SKU ${producto.sku || "-"}` : "Selecciona un producto"}
                      {producto ? ` · Stock: ${producto.stock}` : ""}
                      {producto && Number(producto.stock) <= 3 ? <span style={{ color: "#ffbf69", marginLeft: 6 }}>⚠ Stock bajo</span> : null}
                    </div>
                  </td>
                  <td style={{ padding: 8, verticalAlign: "top" }}>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={item.cantidad}
                      onChange={(event) => {
                        const value = event.target.value;
                        setItems((prev) => prev.map((current, currentIndex) => currentIndex === index ? { ...current, cantidad: value } : current));
                      }}
                      disabled={disabled}
                      style={{ width: "100%" }}
                    />
                  </td>
                  <td style={{ padding: 8, verticalAlign: "top" }}>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={item.devuelto}
                      onChange={(event) => {
                        const value = event.target.value;
                        setItems((prev) => prev.map((current, currentIndex) => currentIndex === index ? { ...current, devuelto: value } : current));
                      }}
                      disabled={disabled}
                      style={{ width: "100%" }}
                    />
                  </td>
                  <td style={{ padding: 8, verticalAlign: "top" }}>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={item.desperdicio}
                      onChange={(event) => {
                        const value = event.target.value;
                        setItems((prev) => prev.map((current, currentIndex) => currentIndex === index ? { ...current, desperdicio: value } : current));
                      }}
                      disabled={disabled}
                      style={{ width: "100%" }}
                    />
                  </td>
                  <td style={{ padding: 8, verticalAlign: "top" }}>
                    <button type="button" className="ghost-button" onClick={() => handleRemove(index)} disabled={disabled}>×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!items.length ? <p style={{ marginTop: 12 }}>Sin insumos agregados.</p> : null}
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Button type="button" onClick={handleAdd} disabled={disabled}>+ Agregar insumo</Button>
        <Button type="submit" disabled={disabled}>Guardar insumos</Button>
      </div>
    </form>
  );
}
