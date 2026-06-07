import { useMemo, useState } from "react";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

export default function CatalogoProductos({
  productos = [],
  categorias = [],
  loading = false,
  onFiltrar,
  onAgregarAlCarrito,
}) {
  const [query, setQuery] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [variantePorProducto, setVariantePorProducto] = useState({});

  const cards = useMemo(() => productos || [], [productos]);

  const handleSubmit = (event) => {
    event.preventDefault();
    onFiltrar?.({
      q: query.trim(),
      categoria: categoriaId || undefined,
      page: 1,
    });
  };

  const handleAgregar = (producto) => {
    const variantes = producto.variantes || [];
    const varianteId = variantePorProducto[producto.id] || variantes[0]?.id || null;
    const variante = variantes.find((item) => String(item.id) === String(varianteId)) || null;
    onAgregarAlCarrito?.(producto, variante);
  };

  return (
    <section className="catalogo-shell">
      <form className="catalogo-filters" onSubmit={handleSubmit}>
        <div className="catalogo-filter-field">
          <label htmlFor="busqueda-productos">Buscar</label>
          <input
            id="busqueda-productos"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Shampoo, collar, snack..."
          />
        </div>
        <div className="catalogo-filter-field">
          <label htmlFor="categoria-productos">Categoría</label>
          <select
            id="categoria-productos"
            value={categoriaId}
            onChange={(event) => setCategoriaId(event.target.value)}
          >
            <option value="">Todas</option>
            {(categorias || []).map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nombre}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className="primary-button catalogo-submit">
          Filtrar catálogo
        </button>
      </form>

      <div className="catalogo-meta">
        <span>{cards.length} productos visibles</span>
        <span>{loading ? "Actualizando inventario..." : "Catálogo sincronizado"}</span>
      </div>

      <div className="catalogo-grid">
        {cards.map((producto) => {
          const variantes = producto.variantes || [];
          const selectedVariantId = variantePorProducto[producto.id] || variantes[0]?.id || "";
          const variante = variantes.find((item) => String(item.id) === String(selectedVariantId)) || null;
          const precio = Number(producto.precio_base || 0) + Number(variante?.precio_extra || 0);
          const stock = variante ? variante.stock : producto.stock;
          return (
            <article key={producto.id} className="catalogo-card">
              <div className="catalogo-card-image">
                {producto.imagen_url ? (
                  <img src={producto.imagen_url} alt={producto.nombre} />
                ) : (
                  <div className="catalogo-placeholder">🛍️</div>
                )}
              </div>
              <div className="catalogo-card-body">
                <div className="catalogo-card-head">
                  <div>
                    <h3>{producto.nombre}</h3>
                    <p>{producto.categoria_nombre || "Sin categoría"}</p>
                  </div>
                  <span className={stock <= 5 ? "stock-pill low" : "stock-pill"}>
                    Stock {stock}
                  </span>
                </div>
                <p className="catalogo-description">{producto.descripcion || "Producto disponible en tienda"}</p>

                {variantes.length ? (
                  <div className="catalogo-filter-field compact">
                    <label>Variante</label>
                    <select
                      value={selectedVariantId}
                      onChange={(event) =>
                        setVariantePorProducto((prev) => ({
                          ...prev,
                          [producto.id]: event.target.value,
                        }))
                      }
                    >
                      {variantes.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.atributo}: {item.valor} (+{money(item.precio_extra)})
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}

                <div className="catalogo-card-footer">
                  <div>
                    <span className="price-label">Precio</span>
                    <strong>{money(precio)}</strong>
                  </div>
                  <button type="button" className="primary-button add-cart-button" onClick={() => handleAgregar(producto)}>
                    + Agregar
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {!cards.length && !loading ? (
        <div className="empty-catalogo">
          No hay productos para los filtros seleccionados.
        </div>
      ) : null}
    </section>
  );
}
