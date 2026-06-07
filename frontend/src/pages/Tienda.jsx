import { useEffect, useMemo, useState } from "react";

import { useAuthContext } from "../context/AuthContext.jsx";
import Alert from "../components/shared/Alert";
import CarritoDrawer from "../components/tienda/CarritoDrawer.jsx";
import CatalogoProductos from "../components/tienda/CatalogoProductos.jsx";
import RecomendacionesPersonalizadas from "../components/tienda/RecomendacionesPersonalizadas.jsx";
import {
  apiAgregarItemCarrito,
  apiGetCarritoMe,
  apiListCategoriasProductos,
  apiListProductosPublicos,
} from "../api/tiendaApi";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

export default function Tienda() {
  const { usuario } = useAuthContext();
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [carritoAbierto, setCarritoAbierto] = useState(false);
  const [itemsCount, setItemsCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [carritoVersion, setCarritoVersion] = useState(0);
  const [filtros, setFiltros] = useState({ q: "", categoria: undefined, page: 1 });

  const headerTitle = useMemo(() => {
    const nombre = usuario?.nombre_completo || usuario?.email || "cliente";
    return `Hola, ${nombre}`;
  }, [usuario]);

  const cargarCategorias = async () => {
    try {
      const data = await apiListCategoriasProductos();
      setCategorias(data || []);
    } catch {
      setCategorias([]);
    }
  };

  const cargarProductos = async (nextFiltros = filtros) => {
    setLoading(true);
    setError("");
    try {
      const data = await apiListProductosPublicos({
        q: nextFiltros.q || undefined,
        categoria: nextFiltros.categoria,
        page: nextFiltros.page || 1,
        per_page: 24,
      });
      setProductos(data.productos || []);
    } catch {
      setError("No se pudo cargar la tienda.");
    } finally {
      setLoading(false);
    }
  };

  const cargarCarrito = async () => {
    try {
      const data = await apiGetCarritoMe();
      setItemsCount(data?.total_items || 0);
    } catch {
      setItemsCount(0);
    }
  };

  useEffect(() => {
    cargarCategorias();
    cargarProductos();
    cargarCarrito();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    cargarProductos(filtros);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.page, filtros.categoria, filtros.q]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const handleFiltrar = (nextFiltros) => {
    setFiltros((prev) => ({ ...prev, ...nextFiltros, page: nextFiltros.page || 1 }));
  };

  const handleAgregar = async (producto, variante) => {
    try {
      const response = await apiAgregarItemCarrito({
        producto_id: producto.id,
        variante_id: variante?.id || null,
        cantidad: 1,
      });
      setItemsCount(response.total_items || 0);
      setCarritoVersion((value) => value + 1);
      setToast(`✓ ${variante ? `${producto.nombre} (${variante.valor})` : producto.nombre} agregado al carrito`);
    } catch (errorAgregar) {
      setError(errorAgregar?.response?.data?.message || "No se pudo agregar al carrito.");
    }
  };

  return (
    <div className="tienda-page">
      <div className="tienda-hero">
        <div>
          <p className="tienda-kicker">Spa & Tienda</p>
          <h1>Catálogo de productos con carrito dinámico</h1>
          <p>
            Busca productos, ajusta variantes y genera el pedido exacto para WhatsApp o Telegram.
          </p>
        </div>

        <button type="button" className="carrito-trigger" onClick={() => setCarritoAbierto(true)}>
          <span>🛒</span>
          <span>Carrito</span>
          {itemsCount > 0 ? <span className="carrito-badge">{itemsCount}</span> : null}
        </button>
      </div>

      <div className="tienda-subheader">
        <strong>{headerTitle}</strong>
        <span>{loading ? "Actualizando inventario..." : `${money(0)} de navegación, compra inmediata y pedido directo.`}</span>
      </div>

      {error ? <Alert message={error} /> : null}
      {toast ? <Alert message={toast} success /> : null}

      <RecomendacionesPersonalizadas onAgregar={(producto, variante) => handleAgregar(producto, variante)} />

      <CatalogoProductos
        productos={productos}
        categorias={categorias}
        loading={loading}
        onFiltrar={handleFiltrar}
        onAgregarAlCarrito={handleAgregar}
      />

      <CarritoDrawer
        abierto={carritoAbierto}
        onCerrar={() => setCarritoAbierto(false)}
        onCarritoActualizado={setItemsCount}
        onToast={setToast}
        refreshToken={carritoVersion}
      />
    </div>
  );
}
