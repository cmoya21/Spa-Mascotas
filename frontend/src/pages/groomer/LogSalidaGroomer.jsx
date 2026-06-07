import { useEffect, useState } from "react";

import { apiLogSalidaGroomer } from "../../api/insumosApi";

export default function LogSalidaGroomer() {
  const [items, setItems] = useState([]);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [error, setError] = useState("");

  const cargar = async () => {
    setError("");
    try {
      const data = await apiLogSalidaGroomer({ fecha_inicio: fechaInicio || undefined, fecha_fin: fechaFin || undefined, limit: 50 });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setError("No se pudo cargar el log de salida.");
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  return (
    <div className="page-shell" style={{ padding: 24 }}>
      <h2>Log de salida de insumos (Groomer)</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
        <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
        <button type="button" className="ghost-button" onClick={cargar}>Filtrar</button>
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: 8 }}>Fecha</th>
              <th style={{ padding: 8 }}>Ficha</th>
              <th style={{ padding: 8 }}>Cita</th>
              <th style={{ padding: 8 }}>Producto</th>
              <th style={{ padding: 8 }}>Cantidad</th>
              <th style={{ padding: 8 }}>Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td style={{ padding: 8 }}>{item.entregado_en ? new Date(item.entregado_en).toLocaleString() : "-"}</td>
                <td style={{ padding: 8 }}>{item.ficha_id}</td>
                <td style={{ padding: 8 }}>{item.cita_id || "-"}</td>
                <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                <td style={{ padding: 8 }}>{item.cantidad_entregada}</td>
                <td style={{ padding: 8 }}>{item.estado}</td>
              </tr>
            ))}
            {!items.length ? (
              <tr><td colSpan={6} style={{ padding: 8 }}>Sin registros.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
