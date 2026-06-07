import { useEffect, useMemo, useState } from "react";

import { apiListGroomers } from "../../api/adminApi";
import { apiLogSalidaAdmin } from "../../api/insumosApi";

function toCsv(rows) {
  const header = ["Groomer", "Fecha", "Ficha", "Cita", "Producto", "Cantidad", "Estado"];
  const lines = rows.map((r) => [
    r.groomer_nombre || "",
    r.entregado_en || "",
    r.ficha_id || "",
    r.cita_id || "",
    r.producto_nombre || r.producto_id,
    r.cantidad_entregada || "",
    r.estado || "",
  ]);
  return [header, ...lines]
    .map((cols) => cols.map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
}

export default function LogSalidaAdmin() {
  const [items, setItems] = useState([]);
  const [groomers, setGroomers] = useState([]);
  const [groomerId, setGroomerId] = useState("");
  const [fecha, setFecha] = useState("");
  const [error, setError] = useState("");

  const cargar = async () => {
    setError("");
    try {
      const data = await apiLogSalidaAdmin({ fecha: fecha || undefined, groomer_id: groomerId || undefined });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setError("No se pudo cargar el log administrativo.");
    }
  };

  useEffect(() => {
    apiListGroomers()
      .then((data) => setGroomers(data.groomers || []))
      .catch(() => setGroomers([]));
    cargar();
  }, []);

  const csvData = useMemo(() => toCsv(items), [items]);

  const exportarCsv = () => {
    const blob = new Blob([csvData], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "log_salida_insumos_admin.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-shell" style={{ padding: 24 }}>
      <h2>Log de salida de insumos (Admin)</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <select value={groomerId} onChange={(e) => setGroomerId(e.target.value)}>
          <option value="">Todos los groomers</option>
          {groomers.map((g) => (
            <option key={g.id} value={g.id}>{g.nombre} {g.apellido || ""}</option>
          ))}
        </select>
        <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
        <button type="button" className="ghost-button" onClick={cargar}>Filtrar</button>
        <button type="button" className="ghost-button" onClick={exportarCsv}>Exportar CSV</button>
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: 8 }}>Groomer</th>
              <th style={{ padding: 8 }}>Fecha</th>
              <th style={{ padding: 8 }}>Producto</th>
              <th style={{ padding: 8 }}>Cantidad</th>
              <th style={{ padding: 8 }}>Ficha</th>
              <th style={{ padding: 8 }}>Cita</th>
              <th style={{ padding: 8 }}>Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td style={{ padding: 8 }}>{item.groomer_nombre || "-"}</td>
                <td style={{ padding: 8 }}>{item.entregado_en ? new Date(item.entregado_en).toLocaleString() : "-"}</td>
                <td style={{ padding: 8 }}>{item.producto_nombre || `Producto ${item.producto_id}`}</td>
                <td style={{ padding: 8 }}>{item.cantidad_entregada}</td>
                <td style={{ padding: 8 }}>{item.ficha_id}</td>
                <td style={{ padding: 8 }}>{item.cita_id || "-"}</td>
                <td style={{ padding: 8 }}>{item.estado}</td>
              </tr>
            ))}
            {!items.length ? (
              <tr><td colSpan={7} style={{ padding: 8 }}>Sin registros.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
