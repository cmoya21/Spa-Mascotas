import { useEffect, useState } from "react";
import { apiListProductosPublicos } from "../../api/tiendaApi.js";
import { apiGetMisMascotas } from "../../api/clienteApi.js";

const RecomendacionCard = ({ item, onAgregar }) => {
  const producto = item.producto || {};
  return (
    <article className="catalogo-card recomendacion-card">
      <div className="catalogo-card-image">{producto.imagen_url ? <img src={producto.imagen_url} alt={producto.nombre} /> : <div className="catalogo-placeholder">🛍️</div>}</div>
      <div className="catalogo-card-body">
        <h4>{producto.nombre}</h4>
        <div style={{ color: "rgba(255,255,255,0.72)" }}>{item.razones?.[0] || producto.categoria_nombre}</div>
        <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button className="primary-button" onClick={() => onAgregar(producto)}>+ Agregar</button>
          <span style={{ fontWeight: 700 }}>Bs. {Number(producto.precio_base || 0).toFixed(2)}</span>
        </div>
      </div>
    </article>
  );
};

export default function RecomendacionesPersonalizadas({ onAgregar }) {
  const [recomendaciones, setRecomendaciones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const productosData = await apiListProductosPublicos({ per_page: 60 });
        const productos = productosData.productos || [];
        const resp = await fetch(`/api/productos/recomendados`);
        if (!resp.ok) throw new Error("no ok");
        const json = await resp.json();
        if (mounted) setRecomendaciones(json.recomendaciones || []);
      } catch (err) {
        setRecomendaciones([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  if (loading) return <div className="recomendaciones-shell">Cargando recomendaciones...</div>;
  if (!recomendaciones.length) return <div className="recomendaciones-shell">No hay recomendaciones por ahora.</div>;

  return (
    <section className="recomendaciones-grid">
      {recomendaciones.map((item, idx) => (
        <RecomendacionCard key={idx} item={item} onAgregar={(producto) => onAgregar(producto, null)} />
      ))}
    </section>
  );
}
