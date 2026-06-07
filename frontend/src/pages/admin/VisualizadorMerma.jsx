import { useEffect, useState } from "react";

import { apiListGroomers } from "../../api/adminApi";
import { apiLogSalidaAdmin } from "../../api/insumosApi";

export default function VisualizadorMerma() {
  const [items, setItems] = useState([]);
  const [groomers, setGroomers] = useState([]);
  const [groomerId, setGroomerId] = useState("");
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [error, setError] = useState("");

  const cargar = async () => {
    setError("");
    try {
      const data = await apiLogSalidaAdmin({
        tipo: "merma",
        groomer_id: groomerId || undefined,
        fecha_inicio: fechaInicio || undefined,
        fecha_fin: fechaFin || undefined,
      });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setError("No se pudo cargar el visualizador de mermas.");
    }
  };

  useEffect(() => {
    apiListGroomers()
      .then((data) => setGroomers(data.groomers || []))
      .catch(() => setGroomers([]));
    cargar();
  }, []);

  return (
    <div className="page-shell" style={{ padding: 24 }}>
      <h2>Visualizador de merma de insumos</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <select value={groomerId} onChange={(e) => setGroomerId(e.target.value)}>
          <option value="">Todos los groomers</option>
          {groomers.map((g) => (
            <option key={g.id} value={g.id}>{g.nombre} {g.apellido || ""}</option>
          ))}
        </select>
        <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
        <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
        <button type="button" className="ghost-button" onClick={cargar}>Filtrar</button>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: 8 }}>Groomer</th>
              <th style={{ padding: 8 }}>Producto</th>
              <th style={{ padding: 8 }}>Cantidad desperdiciada</th>
              <th style={{ padding: 8 }}>% desperdicio</th>
              <th style={{ padding: 8 }}>Fecha</th>
              <th style={{ padding: 8 }}>Motivo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.log_id}>
                <td style={{ padding: 8 }}>{item.groomer_nombre || "-"}</td>
                <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                <td style={{ padding: 8 }}>{item.cantidad_desperdicio ?? "-"}</td>
                <td style={{ padding: 8 }}>{item.porcentaje_desperdicio ?? "-"}%</td>
                <td style={{ padding: 8 }}>{item.fecha ? new Date(item.fecha).toLocaleString() : "-"}</td>
                <td style={{ padding: 8 }}>{item.motivo || "-"}</td>
              </tr>
            ))}
            {!items.length ? (
              <tr><td colSpan={6} style={{ padding: 8 }}>Sin mermas registradas.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
