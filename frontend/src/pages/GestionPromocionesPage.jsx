import { useEffect, useMemo, useState } from "react";

import { apiCrearPromocion, apiListPromociones, apiTogglePromocion } from "../api/promocionesApi";

const emptyForm = {
  nombre: "",
  descripcion: "",
  tipo: "porcentaje",
  valor: "",
  fecha_inicio: "",
  fecha_fin: "",
  codigo_cupon: "",
  uso_maximo: "",
  aplica_a: "todo",
};

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

const statusMeta = (promo, hoyIso) => {
  if (promo.uso_maximo && Number(promo.uso_actual || 0) >= Number(promo.uso_maximo)) {
    return { label: "Agotada", className: "status-badge agotada" };
  }
  if (promo.fecha_fin && promo.fecha_fin < hoyIso) {
    return { label: "Vencida", className: "status-badge vencida" };
  }
  return promo.activa
    ? { label: "Activa", className: "status-badge activa" }
    : { label: "Inactiva", className: "status-badge inactiva" };
};

export default function GestionPromocionesPage() {
  const [promociones, setPromociones] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const hoyIso = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const load = async () => {
    const data = await apiListPromociones();
    setPromociones(Array.isArray(data) ? data : data.promociones || []);
  };

  useEffect(() => {
    load().catch(() => setError("No se pudieron cargar las promociones."));
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await apiCrearPromocion({
        ...form,
        valor: Number(form.valor),
        uso_maximo: form.uso_maximo ? Number(form.uso_maximo) : null,
        fecha_inicio: form.fecha_inicio || null,
        fecha_fin: form.fecha_fin || null,
        codigo_cupon: form.codigo_cupon || null,
      });
      setSuccess("Promoción creada.");
      setForm(emptyForm);
      setShowModal(false);
      await load();
    } catch (submitError) {
      setError(submitError?.response?.data?.message || "No se pudo crear la promoción.");
    } finally {
      setLoading(false);
    }
  };

  const toggle = async (promocionId) => {
    try {
      await apiTogglePromocion(promocionId);
      await load();
    } catch {
      setError("No se pudo actualizar el estado de la promoción.");
    }
  };

  return (
    <section className="agenda-card agenda-wide">
      <div className="promos-toolbar">
        <div>
          <p className="calendar-kicker">Promociones y cupones</p>
          <h3 style={{ marginBottom: 6 }}>Gestión de descuentos</h3>
          <p style={{ margin: 0, color: "rgba(255,255,255,0.68)" }}>
            Controla vigencia, cupón, usos máximos y promociones activas.
          </p>
        </div>
        <button type="button" className="primary-button promo-create-button" onClick={() => setShowModal(true)}>
          + Nueva promoción
        </button>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}
      {success ? <div className="alert alert-success" style={{ marginTop: 16 }}>{success}</div> : null}

      <div className="promo-table" style={{ marginTop: 18 }}>
        <div className="promo-row promo-head">
          <span>Nombre</span>
          <span>Tipo</span>
          <span>Valor</span>
          <span>Cupón</span>
          <span>Usos</span>
          <span>Vigencia</span>
          <span>Estado</span>
          <span>Acciones</span>
        </div>
        {promociones.map((promo) => {
          const state = statusMeta(promo, hoyIso);
          const vigencia = `${promo.fecha_inicio || "-"} / ${promo.fecha_fin || "-"}`;
          const usos = promo.uso_maximo ? `${promo.uso_actual || 0}/${promo.uso_maximo}` : `${promo.uso_actual || 0} / ∞`;
          return (
            <div key={promo.id} className="promo-row">
              <span>{promo.nombre}</span>
              <span>{promo.tipo}</span>
              <span>{promo.tipo === "porcentaje" ? `${Number(promo.valor)}%` : money(promo.valor)}</span>
              <span>{promo.codigo_cupon || "—"}</span>
              <span>{usos}</span>
              <span>{vigencia}</span>
              <span>
                <span className={state.className}>{state.label}</span>
                <span className="promo-scope">{promo.aplica_a || "todo"}</span>
              </span>
              <span>
                <button type="button" className="link-button" onClick={() => toggle(promo.id)}>
                  {promo.activa ? "Desactivar" : "Activar"}
                </button>
              </span>
            </div>
          );
        })}
        {!promociones.length ? <div className="admin-empty">No hay promociones registradas.</div> : null}
      </div>

      {showModal ? (
        <div className="modal-backdrop">
          <div className="modal-card promo-modal">
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Nueva promoción</p>
                <h4 style={{ margin: 0 }}>Crear descuento</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setShowModal(false)}>Cerrar</button>
            </div>

            <form onSubmit={submit} className="promo-form">
              <label>
                Nombre
                <input value={form.nombre} onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))} />
              </label>
              <label>
                Descripción
                <textarea value={form.descripcion} onChange={(event) => setForm((prev) => ({ ...prev, descripcion: event.target.value }))} rows={3} />
              </label>
              <div className="promo-grid-2">
                <label>
                  Tipo
                  <select value={form.tipo} onChange={(event) => setForm((prev) => ({ ...prev, tipo: event.target.value }))}>
                    <option value="porcentaje">Porcentaje</option>
                    <option value="monto_fijo">Monto fijo</option>
                  </select>
                </label>
                <label>
                  Valor
                  <input type="number" min="0" step="0.01" value={form.valor} onChange={(event) => setForm((prev) => ({ ...prev, valor: event.target.value }))} />
                </label>
              </div>
              <div className="promo-grid-2">
                <label>
                  Código de cupón
                  <input
                    value={form.codigo_cupon}
                    onChange={(event) => setForm((prev) => ({ ...prev, codigo_cupon: event.target.value }))}
                    placeholder="Dejar vacío si no requiere código"
                  />
                </label>
                <label>
                  Uso máximo
                  <input
                    type="number"
                    min="1"
                    value={form.uso_maximo}
                    onChange={(event) => setForm((prev) => ({ ...prev, uso_maximo: event.target.value }))}
                    placeholder="Opcional"
                  />
                </label>
              </div>
              <div className="promo-grid-2">
                <label>
                  Fecha inicio
                  <input type="date" value={form.fecha_inicio} onChange={(event) => setForm((prev) => ({ ...prev, fecha_inicio: event.target.value }))} />
                </label>
                <label>
                  Fecha fin
                  <input type="date" value={form.fecha_fin} onChange={(event) => setForm((prev) => ({ ...prev, fecha_fin: event.target.value }))} />
                </label>
              </div>
              <label>
                Aplica a
                <select value={form.aplica_a} onChange={(event) => setForm((prev) => ({ ...prev, aplica_a: event.target.value }))}>
                  <option value="todo">Todo</option>
                  <option value="servicios">Servicios</option>
                  <option value="productos">Productos</option>
                  <option value="cliente_frecuente">Cliente frecuente</option>
                </select>
              </label>

              <div className="promo-actions">
                <button type="submit" className="primary-button" disabled={loading}>
                  {loading ? "Guardando..." : "Guardar promoción"}
                </button>
                <button type="button" className="secondary-button" onClick={() => setShowModal(false)}>Cancelar</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
