import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import { apiGetMisMascotas } from "../api/clienteApi.js";
import useAuth from "../hooks/useAuth";
import {
  apiGetAuditoriaInsumos,
  apiGetCancelacionesReporte,
  apiGetClienteGaleria,
  apiGetClienteHistorialMascota,
  apiGetClientePuntos,
  apiGetCronogramaDiario,
  apiGetInventarioCritico,
  apiGetOcupacion,
  apiGetRankingRentabilidad,
  apiGetSatisfaccion,
  apiGetVentasReporte,
} from "../api/reportesApi";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

const downloadCsv = (rows, headers, filename) => {
  const headerLine = headers.map((item) => item.label).join(",");
  const lines = rows.map((row) => headers.map((item) => JSON.stringify(row[item.key] ?? "")).join(","));
  const blob = new Blob([headerLine, "\n", lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

const getLast30Days = () => {
  const today = new Date();
  const start = new Date();
  start.setDate(today.getDate() - 30);
  return {
    inicio: start.toISOString().slice(0, 10),
    fin: today.toISOString().slice(0, 10),
  };
};

const DateField = ({ label, value, onChange }) => (
  <label className="input-field">
    <span>{label}</span>
    <div className="input-wrapper">
      <input type="date" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  </label>
);

const ReportesAdmin = () => {
  const [tab, setTab] = useState("ventas");
  const [error, setError] = useState("");
  const [ventas, setVentas] = useState([]);
  const [ranking, setRanking] = useState({ servicios: [], productos: [] });
  const [ocupacion, setOcupacion] = useState({ por_groomer: [], porcentaje_global: 0 });
  const [insumos, setInsumos] = useState([]);
  const [satisfaccion, setSatisfaccion] = useState({ por_mes: [], comentarios_recientes: [] });
  const [rangoVentas, setRangoVentas] = useState(getLast30Days());
  const [rangoOcupacion, setRangoOcupacion] = useState(getLast30Days());
  const [rangoInsumos, setRangoInsumos] = useState(getLast30Days());
  const [groomerId, setGroomerId] = useState("");

  useEffect(() => {
    setError("");
    if (tab === "ventas") {
      apiGetVentasReporte({ fecha_inicio: rangoVentas.inicio, fecha_fin: rangoVentas.fin })
        .then((data) => setVentas(data.items || []))
        .catch(() => setError("No se pudieron cargar las ventas."));
    }
    if (tab === "ranking") {
      apiGetRankingRentabilidad()
        .then((data) => setRanking({ servicios: data.servicios || [], productos: data.productos || [] }))
        .catch(() => setError("No se pudo cargar el ranking."));
    }
    if (tab === "ocupacion") {
      apiGetOcupacion({ fecha_inicio: rangoOcupacion.inicio, fecha_fin: rangoOcupacion.fin })
        .then((data) => setOcupacion({ por_groomer: data.por_groomer || [], porcentaje_global: data.porcentaje_global || 0 }))
        .catch(() => setError("No se pudo cargar la ocupacion."));
    }
    if (tab === "insumos") {
      apiGetAuditoriaInsumos({
        fecha_inicio: rangoInsumos.inicio,
        fecha_fin: rangoInsumos.fin,
        groomer_id: groomerId || undefined,
      })
        .then((data) => setInsumos(data.items || []))
        .catch(() => setError("No se pudo cargar la auditoria de insumos."));
    }
    if (tab === "satisfaccion") {
      apiGetSatisfaccion()
        .then((data) => setSatisfaccion({ por_mes: data.por_mes || [], comentarios_recientes: data.comentarios_recientes || [] }))
        .catch(() => setError("No se pudo cargar la satisfaccion."));
    }
  }, [tab, rangoVentas, rangoOcupacion, rangoInsumos, groomerId]);

  const maxVenta = Math.max(...ventas.map((item) => Number(item.ingresos_totales || 0)), 1);

  return (
    <div className="admin-grid">
      <section className="admin-card">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { key: "ventas", label: "Ventas" },
            { key: "ranking", label: "Ranking" },
            { key: "ocupacion", label: "Ocupacion" },
            { key: "insumos", label: "Insumos" },
            { key: "satisfaccion", label: "Satisfaccion" },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              className={tab === item.key ? "primary-button" : "ghost-button"}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {tab === "ventas" && (
        <section className="admin-card">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <DateField label="Inicio" value={rangoVentas.inicio} onChange={(value) => setRangoVentas((prev) => ({ ...prev, inicio: value }))} />
            <DateField label="Fin" value={rangoVentas.fin} onChange={(value) => setRangoVentas((prev) => ({ ...prev, fin: value }))} />
            <Button type="button" onClick={() => downloadCsv(ventas, [
              { key: "fecha", label: "Fecha" },
              { key: "total_facturas", label: "Facturas" },
              { key: "ingresos_servicios", label: "Servicios" },
              { key: "ingresos_productos", label: "Productos" },
              { key: "ingresos_totales", label: "Total" },
            ], "reporte_ventas.csv")}>
              Exportar CSV
            </Button>
          </div>
          <div className="admin-table" style={{ marginTop: 12 }}>
            <div className="admin-row admin-head">
              <span>Fecha</span>
              <span>Facturas</span>
              <span>Servicios</span>
              <span>Productos</span>
              <span>Total</span>
            </div>
            {ventas.map((item) => (
              <div className="admin-row" key={`venta-${item.fecha}`}>
                <div>{item.fecha}</div>
                <div>{item.total_facturas}</div>
                <div>{money(item.ingresos_servicios)}</div>
                <div>{money(item.ingresos_productos)}</div>
                <div>{money(item.ingresos_totales)}</div>
              </div>
            ))}
            {!ventas.length && <div className="admin-empty">Sin datos.</div>}
          </div>
          <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
            {ventas.map((item) => (
              <div key={`bar-${item.fecha}`} style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 8, alignItems: "center" }}>
                <span>{item.fecha}</span>
                <div style={{ height: 8, background: "rgba(255,255,255,0.12)", borderRadius: 999 }}>
                  <div style={{ width: `${(Number(item.ingresos_totales || 0) / maxVenta) * 100}%`, height: "100%", background: "#4ade80", borderRadius: 999 }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === "ranking" && (
        <section className="admin-card">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            <div>
              <h3>Top servicios</h3>
              <div className="admin-table">
                {ranking.servicios.map((item, index) => (
                  <div className="admin-row" key={`svc-${index}`}>
                    <div>{item.nombre}</div>
                    <div>{item.total_citas}</div>
                    <div>{money(item.ingresos_totales)}</div>
                  </div>
                ))}
                {!ranking.servicios.length && <div className="admin-empty">Sin datos.</div>}
              </div>
            </div>
            <div>
              <h3>Top productos</h3>
              <div className="admin-table">
                {ranking.productos.map((item, index) => (
                  <div className="admin-row" key={`prod-${index}`}>
                    <div>{item.nombre}</div>
                    <div>{item.vendidos}</div>
                    <div>{money(item.ingresos)}</div>
                  </div>
                ))}
                {!ranking.productos.length && <div className="admin-empty">Sin datos.</div>}
              </div>
            </div>
          </div>
        </section>
      )}

      {tab === "ocupacion" && (
        <section className="admin-card">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <DateField label="Inicio" value={rangoOcupacion.inicio} onChange={(value) => setRangoOcupacion((prev) => ({ ...prev, inicio: value }))} />
            <DateField label="Fin" value={rangoOcupacion.fin} onChange={(value) => setRangoOcupacion((prev) => ({ ...prev, fin: value }))} />
          </div>
          <div style={{ marginTop: 12, fontSize: 20, fontWeight: 700 }}>
            Ocupacion global: {ocupacion.porcentaje_global}%
          </div>
          <div className="admin-table" style={{ marginTop: 12 }}>
            <div className="admin-row admin-head">
              <span>Groomer</span>
              <span>Citas</span>
              <span>Minutos</span>
              <span>Completadas</span>
              <span>Canceladas</span>
            </div>
            {ocupacion.por_groomer.map((item, index) => (
              <div className="admin-row" key={`occ-${index}`}>
                <div>{item.groomer}</div>
                <div>{item.total_citas}</div>
                <div>{item.minutos_ocupados}</div>
                <div>{item.completadas}</div>
                <div>{item.canceladas}</div>
              </div>
            ))}
            {!ocupacion.por_groomer.length && <div className="admin-empty">Sin datos.</div>}
          </div>
        </section>
      )}

      {tab === "insumos" && (
        <section className="admin-card">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <DateField label="Inicio" value={rangoInsumos.inicio} onChange={(value) => setRangoInsumos((prev) => ({ ...prev, inicio: value }))} />
            <DateField label="Fin" value={rangoInsumos.fin} onChange={(value) => setRangoInsumos((prev) => ({ ...prev, fin: value }))} />
            <label className="input-field">
              <span>Groomer</span>
              <div className="input-wrapper">
                <input value={groomerId} onChange={(event) => setGroomerId(event.target.value)} placeholder="ID opcional" />
              </div>
            </label>
            <Button type="button" onClick={() => downloadCsv(insumos, [
              { key: "groomer", label: "Groomer" },
              { key: "producto", label: "Producto" },
              { key: "entregado", label: "Entregado" },
              { key: "usado", label: "Usado" },
              { key: "devuelto", label: "Devuelto" },
              { key: "desperdicio", label: "Desperdicio" },
              { key: "diferencia", label: "Diferencia" },
            ], "auditoria_insumos.csv")}>
              Exportar CSV
            </Button>
          </div>
          <div className="admin-table" style={{ marginTop: 12 }}>
            <div className="admin-row admin-head">
              <span>Groomer</span>
              <span>Producto</span>
              <span>Entregado</span>
              <span>Usado</span>
              <span>Devuelto</span>
              <span>Desperdicio</span>
              <span>Diferencia</span>
            </div>
            {insumos.map((item, index) => (
              <div className="admin-row" key={`ins-${index}`} style={{ color: Number(item.diferencia || 0) < 0 ? "#fca5a5" : undefined }}>
                <div>{item.groomer}</div>
                <div>{item.producto}</div>
                <div>{item.entregado}</div>
                <div>{item.usado}</div>
                <div>{item.devuelto}</div>
                <div>{item.desperdicio}</div>
                <div>{item.diferencia}</div>
              </div>
            ))}
            {!insumos.length && <div className="admin-empty">Sin datos.</div>}
          </div>
        </section>
      )}

      {tab === "satisfaccion" && (
        <section className="admin-card">
          <div className="admin-table">
            <div className="admin-row admin-head">
              <span>Mes</span>
              <span>Promedio</span>
              <span>NPS</span>
              <span>Encuestas</span>
            </div>
            {satisfaccion.por_mes.map((item) => (
              <div className="admin-row" key={`sat-${item.mes}`}>
                <div>{item.mes}</div>
                <div>{item.promedio_estrellas}</div>
                <div>{item.promedio_nps}</div>
                <div>{item.total_encuestas}</div>
              </div>
            ))}
            {!satisfaccion.por_mes.length && <div className="admin-empty">Sin datos.</div>}
          </div>
          <div style={{ marginTop: 16, display: "grid", gap: 8 }}>
            {satisfaccion.comentarios_recientes.map((item, index) => (
              <div key={`coment-${index}`} className="admin-row">
                <div>{item.mascota} · {item.servicio}</div>
                <div>⭐ {item.calificacion} / NPS {item.nps}</div>
                <div>{item.comentario || "(sin comentario)"}</div>
              </div>
            ))}
            {!satisfaccion.comentarios_recientes.length && <div className="admin-empty">Sin comentarios.</div>}
          </div>
        </section>
      )}

      {error ? <Alert message={error} /> : null}
    </div>
  );
};

const ReportesRecepcion = () => {
  const [tab, setTab] = useState("cronograma");
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [cronograma, setCronograma] = useState([]);
  const [cancelaciones, setCancelaciones] = useState([]);
  const [inventario, setInventario] = useState([]);
  const [rangoCancel, setRangoCancel] = useState(getLast30Days());
  const [tipoCancel, setTipoCancel] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    if (tab === "cronograma") {
      apiGetCronogramaDiario({ fecha })
        .then((data) => setCronograma(data.items || []))
        .catch(() => setError("No se pudo cargar el cronograma."));
    }
    if (tab === "cancelaciones") {
      apiGetCancelacionesReporte({ fecha_inicio: rangoCancel.inicio, fecha_fin: rangoCancel.fin, tipo: tipoCancel || undefined })
        .then((data) => setCancelaciones(data.items || []))
        .catch(() => setError("No se pudieron cargar cancelaciones."));
    }
    if (tab === "inventario") {
      apiGetInventarioCritico()
        .then((data) => setInventario(data.items || []))
        .catch(() => setError("No se pudo cargar inventario critico."));
    }
  }, [tab, fecha, rangoCancel, tipoCancel]);

  const resumen = useMemo(() => {
    const total = cronograma.length;
    const completadas = cronograma.filter((item) => item.estado === "completada").length;
    const porCobrar = cronograma.filter((item) => item.estado_pago !== "pagada").length;
    return { total, completadas, porCobrar };
  }, [cronograma]);

  return (
    <div className="admin-grid">
      <section className="admin-card">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { key: "cronograma", label: "Cronograma" },
            { key: "cancelaciones", label: "Cancelaciones" },
            { key: "inventario", label: "Inventario critico" },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              className={tab === item.key ? "primary-button" : "ghost-button"}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {tab === "cronograma" && (
        <section className="admin-card">
          <DateField label="Fecha" value={fecha} onChange={setFecha} />
          <div className="admin-table" style={{ marginTop: 12 }}>
            {cronograma.map((item) => (
              <div className="admin-row" key={`cron-${item.id}`}>
                <div>{new Date(item.fecha_hora_inicio).toLocaleTimeString()}</div>
                <div>{item.mascota}</div>
                <div>{item.servicio}</div>
                <div>{item.groomer || "-"}</div>
                <div>{item.estado}</div>
                <div>{item.estado_pago}</div>
              </div>
            ))}
            {!cronograma.length && <div className="admin-empty">Sin citas para la fecha.</div>}
          </div>
          <div style={{ marginTop: 12 }}>
            {resumen.total} citas | {resumen.completadas} completadas | {resumen.porCobrar} por cobrar
          </div>
          <button type="button" className="ghost-button" onClick={() => window.print()} style={{ marginTop: 10 }}>
            Imprimir
          </button>
        </section>
      )}

      {tab === "cancelaciones" && (
        <section className="admin-card">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <DateField label="Inicio" value={rangoCancel.inicio} onChange={(value) => setRangoCancel((prev) => ({ ...prev, inicio: value }))} />
            <DateField label="Fin" value={rangoCancel.fin} onChange={(value) => setRangoCancel((prev) => ({ ...prev, fin: value }))} />
            <label className="input-field">
              <span>Tipo</span>
              <div className="input-wrapper">
                <select value={tipoCancel} onChange={(event) => setTipoCancel(event.target.value)}>
                  <option value="">Todos</option>
                  <option value="cancelada">Canceladas</option>
                  <option value="no_asistio">No-show</option>
                </select>
              </div>
            </label>
          </div>
          <div className="admin-table" style={{ marginTop: 12 }}>
            {cancelaciones.map((item) => (
              <div className="admin-row" key={`can-${item.id}`}>
                <div>{new Date(item.fecha_hora_inicio).toLocaleDateString()}</div>
                <div>{item.cliente}</div>
                <div>{item.mascota}</div>
                <div>{item.servicio}</div>
                <div>{item.motivo_cancelacion || "-"}</div>
              </div>
            ))}
            {!cancelaciones.length && <div className="admin-empty">Sin cancelaciones.</div>}
          </div>
        </section>
      )}

      {tab === "inventario" && (
        <section className="admin-card">
          <Button type="button" onClick={() => downloadCsv(inventario, [
            { key: "nombre", label: "Nombre" },
            { key: "sku", label: "SKU" },
            { key: "stock", label: "Stock" },
            { key: "stock_minimo", label: "Minimo" },
          ], "inventario_critico.csv")}>
            Exportar CSV
          </Button>
          <div className="admin-table" style={{ marginTop: 12 }}>
            {inventario.map((item, index) => {
              const faltantes = Math.max(0, Number(item.stock_minimo || 0) - Number(item.stock || 0));
              return (
                <div className="admin-row" key={`inv-${index}`}>
                  <div>{item.nombre}</div>
                  <div>{item.sku}</div>
                  <div>{item.stock}</div>
                  <div>{item.stock_minimo}</div>
                  <div>{faltantes}</div>
                </div>
              );
            })}
            {!inventario.length && <div className="admin-empty">Sin alertas criticas.</div>}
          </div>
        </section>
      )}

      {error ? <Alert message={error} /> : null}
    </div>
  );
};

const ReportesCliente = () => {
  const [error, setError] = useState("");
  const [mascotas, setMascotas] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [historial, setHistorial] = useState([]);
  const [galeria, setGaleria] = useState([]);
  const [beneficios, setBeneficios] = useState(null);
  const [fotoActiva, setFotoActiva] = useState("");

  useEffect(() => {
    apiGetMisMascotas()
      .then((data) => {
        const list = data.mascotas || [];
        setMascotas(list);
        setSelectedId((current) => current || (list[0] ? String(list[0].id) : ""));
      })
      .catch(() => setError("No se pudieron cargar mascotas."));
    apiGetClientePuntos()
      .then(setBeneficios)
      .catch(() => setBeneficios(null));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    apiGetClienteHistorialMascota(selectedId)
      .then((data) => setHistorial(data.items || []))
      .catch(() => setError("No se pudo cargar historial."));
    apiGetClienteGaleria(selectedId)
      .then((data) => setGaleria(data.citas || []))
      .catch(() => setError("No se pudo cargar galeria."));
  }, [selectedId]);

  const progreso = beneficios ? Math.min(100, (beneficios.total_visitas / 10) * 100) : 0;

  return (
    <div className="admin-grid">
      <section className="admin-card">
        <h3>Mis mascotas</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {mascotas.map((m) => (
            <button
              key={m.id}
              type="button"
              className={String(m.id) === String(selectedId) ? "primary-button" : "ghost-button"}
              onClick={() => setSelectedId(String(m.id))}
            >
              {m.nombre}
            </button>
          ))}
        </div>
      </section>

      <section className="admin-card">
        <h3>Historial</h3>
        <div className="admin-table">
          {historial.map((item) => (
            <div className="admin-row" key={`hist-${item.id}`}>
              <div>{new Date(item.fecha_hora_inicio).toLocaleDateString()}</div>
              <div>{item.servicio}</div>
              <div>{item.groomer || "-"}</div>
              <div>{item.estado_final || "-"}</div>
              <div>{item.recomendacion || "Sin recomendacion"}</div>
            </div>
          ))}
          {!historial.length && <div className="admin-empty">Sin historial.</div>}
        </div>
      </section>

      <section className="admin-card">
        <h3>Galeria</h3>
        <div style={{ display: "grid", gap: 12 }}>
          {galeria.map((cita) => (
            <div key={`gal-${cita.cita_id}`}>
              <strong>{cita.fecha} · {cita.servicio}</strong>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8, marginTop: 8 }}>
                {(cita.fotos?.antes || []).map((url, idx) => (
                  <img key={`a-${idx}`} src={url} alt="antes" style={{ width: "100%", borderRadius: 12 }} onClick={() => setFotoActiva(url)} />
                ))}
                {(cita.fotos?.despues || []).map((url, idx) => (
                  <img key={`d-${idx}`} src={url} alt="despues" style={{ width: "100%", borderRadius: 12 }} onClick={() => setFotoActiva(url)} />
                ))}
              </div>
            </div>
          ))}
          {!galeria.length && <div className="admin-empty">Sin fotos registradas.</div>}
        </div>
      </section>

      <section className="admin-card">
        <h3>Mis beneficios</h3>
        {beneficios ? (
          <div>
            <div><strong>Nivel:</strong> {beneficios.nivel}</div>
            <div><strong>Visitas:</strong> {beneficios.total_visitas}</div>
            <div><strong>Descuento:</strong> {beneficios.descuento_disponible}%</div>
            <div style={{ marginTop: 6 }}>{beneficios.mensaje}</div>
            <div style={{ height: 6, background: "rgba(255,255,255,0.12)", borderRadius: 999, overflow: "hidden", marginTop: 8 }}>
              <div style={{ width: `${progreso}%`, height: "100%", background: "#4ade80" }} />
            </div>
          </div>
        ) : (
          <div className="admin-empty">Sin beneficios disponibles.</div>
        )}
      </section>

      {fotoActiva ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "grid", placeItems: "center", zIndex: 60 }}>
          <div style={{ position: "relative", maxWidth: "80vw", maxHeight: "80vh" }}>
            <button type="button" className="ghost-button" onClick={() => setFotoActiva("")} style={{ position: "absolute", right: 0, top: -40 }}>
              Cerrar
            </button>
            <img src={fotoActiva} alt="detalle" style={{ maxWidth: "80vw", maxHeight: "80vh", borderRadius: 14 }} />
          </div>
        </div>
      ) : null}

      {error ? <Alert message={error} /> : null}
    </div>
  );
};

export default function ReportesPage() {
  const { usuario } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (usuario?.rol === "Groomer") {
      navigate("/groomers/agenda", { replace: true });
    }
  }, [usuario, navigate]);

  if (usuario?.rol === "Groomer") {
    return <Navigate to="/groomers/agenda" replace />;
  }

  return (
    <div className="page-shell admin-layout">
      <div className="page-content">
        <header className="admin-hero">
          <div>
            <h2>Reportes</h2>
            <p>Vista filtrada por rol.</p>
          </div>
        </header>

        {usuario?.rol === "Admin" && <ReportesAdmin />}
        {usuario?.rol === "Recepcion" && <ReportesRecepcion />}
        {usuario?.rol === "Cliente" && <ReportesCliente />}
      </div>
    </div>
  );
}
