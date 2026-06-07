import { useEffect, useMemo, useState } from "react";

import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";
import {
  apiActualizarEstadoServicio,
  apiActualizarServicio,
  apiCrearServicio,
  apiListServicios,
} from "../api/agendaApi.js";
import { apiListProductos } from "../api/inventarioApi.js";

const emptyFactor = {
  pequeno: "1.0",
  mediano: "1.15",
  grande: "1.30",
  gigante: "1.30",
};

const emptyChecklistItem = () => ({
  nombre: "",
  requiere_obs: false,
  orden: 1,
  activo: true,
});

const emptyInsumo = () => ({
  producto_id: "",
  cantidad: "",
});

const baseForm = {
  nombre: "",
  descripcion: "",
  precio_base: "",
  duracion_base_minutos: 30,
  activo: true,
  permite_doble_booking: false,
  requiere_bloqueo_consecutivo: false,
  factor_tamano_raza: emptyFactor,
  consumo_insumos: [emptyInsumo()],
  checklist_items: [emptyChecklistItem()],
};

function cloneChecklist(checklist = []) {
  if (!checklist.length) {
    return [emptyChecklistItem()];
  }
  return checklist.map((item, index) => ({
    nombre: item.nombre || "",
    requiere_obs: Boolean(item.requiere_obs),
    orden: Number(item.orden || index + 1),
    activo: item.activo !== false,
  }));
}

function cloneInsumos(insumos = []) {
  if (!insumos.length) {
    return [emptyInsumo()];
  }
  return insumos.map((item) => ({
    producto_id: item.producto_id ? String(item.producto_id) : "",
    cantidad: item.cantidad ?? "",
  }));
}

function normalizeNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function durationBadgeClass(duration) {
  if (duration >= 120) return { background: "#5a3e91", color: "#fff" };
  if (duration >= 90) return { background: "#1f7a8c", color: "#fff" };
  if (duration >= 60) return { background: "#2f855a", color: "#fff" };
  return { background: "#264653", color: "#fff" };
}

function resolveMessage(err, fallback) {
  const data = err?.response?.data;
  if (!data) return fallback;
  const details = data.details;
  if (typeof details === "string") return details;
  if (details && typeof details === "object") {
    const firstKey = Object.keys(details)[0];
    if (firstKey && Array.isArray(details[firstKey]) && details[firstKey].length > 0) {
      return details[firstKey][0];
    }
    if (typeof details.citas_afectadas === "number" && details.citas_afectadas > 0) {
      return `${data.message || fallback} (${details.citas_afectadas} citas futuras)`;
    }
  }
  return data.message || fallback;
}

function buildPayload(form) {
  return {
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim() || null,
    precio_base: normalizeNumber(form.precio_base),
    duracion_base_minutos: Number(form.duracion_base_minutos),
    activo: Boolean(form.activo),
    permite_doble_booking: Boolean(form.permite_doble_booking),
    requiere_bloqueo_consecutivo: Boolean(form.requiere_bloqueo_consecutivo),
    factor_tamano_raza: {
      pequeno: normalizeNumber(form.factor_tamano_raza.pequeno),
      mediano: normalizeNumber(form.factor_tamano_raza.mediano),
      grande: normalizeNumber(form.factor_tamano_raza.grande),
      gigante: normalizeNumber(form.factor_tamano_raza.gigante),
    },
    consumo_insumos: form.consumo_insumos
      .filter((item) => item.producto_id && Number(item.cantidad) > 0)
      .map((item) => ({
        producto_id: Number(item.producto_id),
        cantidad: Number(item.cantidad),
      })),
    checklist_items: form.checklist_items
      .filter((item) => item.nombre.trim())
      .map((item, index) => ({
        nombre: item.nombre.trim(),
        requiere_obs: Boolean(item.requiere_obs),
        orden: Number(item.orden || index + 1),
        activo: Boolean(item.activo),
      })),
  };
}

export default function GestionServicios() {
  const [servicios, setServicios] = useState([]);
  const [productos, setProductos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [toggleConflict, setToggleConflict] = useState(null);
  const [form, setForm] = useState(baseForm);

  const totalActivos = useMemo(
    () => servicios.filter((servicio) => servicio.activo).length,
    [servicios]
  );

  const loadData = async () => {
    setLoading(true);
    try {
      const [serviciosData, productosData] = await Promise.all([
        apiListServicios(),
        apiListProductos(),
      ]);
      setServicios(serviciosData.servicios || []);
      setProductos(productosData.productos || []);
    } catch (err) {
      setError(resolveMessage(err, "No se pudo cargar el catalogo de servicios."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setToggleConflict(null);
    setForm(baseForm);
    setDrawerOpen(true);
  };

  const openEdit = (servicio) => {
    setEditingId(servicio.id);
    setToggleConflict(null);
    setForm({
      nombre: servicio.nombre || "",
      descripcion: servicio.descripcion || "",
      precio_base: servicio.precio_base ?? "",
      duracion_base_minutos: servicio.duracion_base_minutos ?? 30,
      activo: Boolean(servicio.activo),
      permite_doble_booking: Boolean(servicio.permite_doble_booking),
      requiere_bloqueo_consecutivo: Boolean(servicio.requiere_bloqueo_consecutivo),
      factor_tamano_raza: {
        pequeno: String(servicio.factor_tamano_raza?.pequeno ?? emptyFactor.pequeno),
        mediano: String(servicio.factor_tamano_raza?.mediano ?? emptyFactor.mediano),
        grande: String(servicio.factor_tamano_raza?.grande ?? emptyFactor.grande),
        gigante: String(servicio.factor_tamano_raza?.gigante ?? emptyFactor.gigante),
      },
      consumo_insumos: cloneInsumos(servicio.consumo_insumos),
      checklist_items: cloneChecklist(servicio.checklist_items),
    });
    setDrawerOpen(true);
  };

  const updateField = (key) => (value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const updateFactor = (key, value) => {
    setForm((prev) => ({
      ...prev,
      factor_tamano_raza: { ...prev.factor_tamano_raza, [key]: value },
    }));
  };

  const updateChecklistItem = (index, key, value) => {
    setForm((prev) => ({
      ...prev,
      checklist_items: prev.checklist_items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item
      ),
    }));
  };

  const moveChecklistItem = (index, direction) => {
    setForm((prev) => {
      const next = [...prev.checklist_items];
      const target = index + direction;
      if (target < 0 || target >= next.length) return prev;
      const temp = next[index];
      next[index] = next[target];
      next[target] = temp;
      return {
        ...prev,
        checklist_items: next.map((item, itemIndex) => ({ ...item, orden: itemIndex + 1 })),
      };
    });
  };

  const addChecklistItem = () => {
    setForm((prev) => ({
      ...prev,
      checklist_items: [...prev.checklist_items, { ...emptyChecklistItem(), orden: prev.checklist_items.length + 1 }],
    }));
  };

  const removeChecklistItem = (index) => {
    setForm((prev) => {
      const next = prev.checklist_items.filter((_, itemIndex) => itemIndex !== index);
      return {
        ...prev,
        checklist_items: next.length
          ? next.map((item, itemIndex) => ({ ...item, orden: itemIndex + 1 }))
          : [emptyChecklistItem()],
      };
    });
  };

  const updateInsumo = (index, key, value) => {
    setForm((prev) => ({
      ...prev,
      consumo_insumos: prev.consumo_insumos.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [key]: value } : item
      ),
    }));
  };

  const addInsumo = () => {
    setForm((prev) => ({
      ...prev,
      consumo_insumos: [...prev.consumo_insumos, emptyInsumo()],
    }));
  };

  const removeInsumo = (index) => {
    setForm((prev) => {
      const next = prev.consumo_insumos.filter((_, itemIndex) => itemIndex !== index);
      return { ...prev, consumo_insumos: next.length ? next : [emptyInsumo()] };
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const payload = buildPayload(form);
      if (editingId) {
        await apiActualizarServicio(editingId, payload);
        setSuccess("Servicio actualizado correctamente.");
      } else {
        await apiCrearServicio(payload);
        setSuccess("Servicio creado correctamente.");
      }
      setDrawerOpen(false);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setError(resolveMessage(err, "No se pudo guardar el servicio."));
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (servicio) => {
    setError("");
    setSuccess("");
    try {
      await apiActualizarEstadoServicio(servicio.id, { activo: !servicio.activo });
      await loadData();
    } catch (err) {
      if (err?.response?.status === 409) {
        setToggleConflict({
          servicio,
          mensaje: err.response.data?.message || "El servicio tiene citas futuras pendientes.",
          citas_afectadas: err.response.data?.details?.citas_afectadas || 0,
        });
        return;
      }
      setError(resolveMessage(err, "No se pudo cambiar el estado del servicio."));
    }
  };

  const forceDeactivate = async () => {
    if (!toggleConflict) return;
    setSaving(true);
    setError("");
    try {
      await apiActualizarEstadoServicio(toggleConflict.servicio.id, {
        activo: false,
        forzar: true,
      });
      setToggleConflict(null);
      setSuccess("Servicio desactivado.");
      await loadData();
    } catch (err) {
      setError(resolveMessage(err, "No se pudo forzar la desactivacion."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-layout" style={{ background: "linear-gradient(180deg, #08111b 0%, #0f1722 100%)", minHeight: "100vh" }}>
      <div className="admin-shell" style={{ padding: 24 }}>
        <div className="admin-hero">
          <div>
            <h2>Gestion de servicios</h2>
            <p>Catalogo maestro para precios, duraciones, checklist e insumos.</p>
          </div>
          <div className="admin-metrics">
            <div>
              <span>Servicios activos</span>
              <strong>{totalActivos}</strong>
            </div>
            <div>
              <span>Total catalogados</span>
              <strong>{servicios.length}</strong>
            </div>
          </div>
        </div>

        {error ? <div style={{ marginTop: 12 }}><Alert message={error} /></div> : null}
        {success ? <div style={{ marginTop: 12 }}><Alert message={success} success /></div> : null}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 18 }}>
          <div>
            <h3 style={{ margin: 0, color: "#f4f7fb" }}>Servicios</h3>
            <p style={{ margin: "4px 0 0", color: "rgba(244,247,251,0.7)" }}>
              {loading ? "Cargando catalogo..." : "Edita, activa o desactiva servicios y revisa su configuracion."}
            </p>
          </div>
          <Button type="button" onClick={openCreate}>
            Nuevo servicio
          </Button>
        </div>

        <div style={{ overflowX: "auto", marginTop: 16 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", color: "#eef3f8", background: "rgba(255,255,255,0.03)", borderRadius: 18, overflow: "hidden" }}>
            <thead>
              <tr style={{ textAlign: "left", background: "rgba(255,255,255,0.05)" }}>
                <th style={{ padding: 14 }}>Servicio</th>
                <th style={{ padding: 14 }}>Duracion</th>
                <th style={{ padding: 14 }}>Precio</th>
                <th style={{ padding: 14 }}>Checklist</th>
                <th style={{ padding: 14 }}>Insumos</th>
                <th style={{ padding: 14 }}>Estado</th>
                <th style={{ padding: 14 }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {servicios.map((servicio) => (
                <tr key={servicio.id} style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                  <td style={{ padding: 14 }}>
                    <div style={{ fontWeight: 700 }}>{servicio.nombre}</div>
                    <div style={{ color: "rgba(238,243,248,0.7)", fontSize: 13 }}>{servicio.descripcion || "Sin descripcion"}</div>
                  </td>
                  <td style={{ padding: 14 }}>
                    <span style={{ ...durationBadgeClass(servicio.duracion_base_minutos), borderRadius: 999, padding: "6px 10px", display: "inline-block", fontWeight: 700 }}>
                      {servicio.duracion_base_minutos} min
                    </span>
                  </td>
                  <td style={{ padding: 14 }}>
                    Bs {Number(servicio.precio_base || 0).toFixed(0)}
                  </td>
                  <td style={{ padding: 14 }}>{servicio.checklist_items?.length || 0}</td>
                  <td style={{ padding: 14 }}>{servicio.consumo_insumos?.length || 0}</td>
                  <td style={{ padding: 14 }}>
                    <span style={{ padding: "6px 10px", borderRadius: 999, background: servicio.activo ? "rgba(93,211,164,0.18)" : "rgba(255,255,255,0.08)", color: servicio.activo ? "#8df0c4" : "#d4d9df" }}>
                      {servicio.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td style={{ padding: 14 }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button type="button" className="secondary-button" onClick={() => openEdit(servicio)}>
                        Editar
                      </button>
                      <button type="button" className="secondary-button" onClick={() => handleToggle(servicio)}>
                        {servicio.activo ? "Desactivar" : "Activar"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && servicios.length === 0 ? (
                <tr>
                  <td style={{ padding: 18 }} colSpan={7}>
                    No hay servicios cargados.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      {drawerOpen ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "flex",
            justifyContent: "flex-end",
            zIndex: 60,
          }}
        >
          <div
            style={{
              width: "min(720px, 100%)",
              height: "100%",
              background: "#0f1824",
              color: "#f4f7fb",
              overflowY: "auto",
              padding: 24,
              borderLeft: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <div>
                <h3 style={{ marginTop: 0 }}>{editingId ? "Editar servicio" : "Nuevo servicio"}</h3>
                <p style={{ marginTop: 0, color: "rgba(244,247,251,0.72)" }}>
                  Define precio, duracion, consumos y checklist.
                </p>
              </div>
              <button type="button" className="secondary-button" onClick={() => setDrawerOpen(false)}>
                Cerrar
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
              <InputField label="Nombre" value={form.nombre} onChange={updateField("nombre")} />
              <InputField label="Descripcion" value={form.descripcion} onChange={updateField("descripcion")} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
                <InputField label="Precio base" type="number" value={form.precio_base} onChange={updateField("precio_base")} />
                <div className="input-field">
                  <label>Duracion base (min)</label>
                  <div className="input-wrapper">
                    <select
                      className="select-field"
                      value={form.duracion_base_minutos}
                      onChange={(e) => updateField("duracion_base_minutos")(e.target.value)}
                    >
                      {Array.from({ length: 24 }, (_, index) => (index + 1) * 15).map((minutes) => (
                        <option key={minutes} value={minutes}>
                          {minutes} min
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
                {Object.entries(form.factor_tamano_raza).map(([key, value]) => (
                  <InputField
                    key={key}
                    label={`Factor ${key}`}
                    type="number"
                    step="0.01"
                    value={value}
                    onChange={(nextValue) => updateFactor(key, nextValue)}
                  />
                ))}
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <h4 style={{ margin: 0 }}>Consumo de insumos</h4>
                  <button type="button" className="secondary-button" onClick={addInsumo}>
                    Agregar insumo
                  </button>
                </div>
                <div style={{ display: "grid", gap: 10 }}>
                  {form.consumo_insumos.map((item, index) => (
                    <div key={`${index}-${item.producto_id}`} style={{ display: "grid", gridTemplateColumns: "2fr 1fr auto", gap: 10, alignItems: "end" }}>
                      <div className="input-field">
                        <label>Producto</label>
                        <div className="input-wrapper">
                          <select
                            className="select-field"
                            value={item.producto_id}
                            onChange={(e) => updateInsumo(index, "producto_id", e.target.value)}
                          >
                            <option value="">Seleccionar producto</option>
                            {productos.map((producto) => (
                              <option key={producto.id} value={producto.id}>
                                {producto.nombre} ({producto.sku})
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <InputField
                        label="Cantidad"
                        type="number"
                        step="0.01"
                        value={item.cantidad}
                        onChange={(value) => updateInsumo(index, "cantidad", value)}
                      />
                      <button type="button" className="secondary-button" onClick={() => removeInsumo(index)}>
                        Quitar
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <h4 style={{ margin: 0 }}>Checklist base</h4>
                  <button type="button" className="secondary-button" onClick={addChecklistItem}>
                    Agregar paso
                  </button>
                </div>
                <div style={{ display: "grid", gap: 10 }}>
                  {form.checklist_items.map((item, index) => (
                    <div key={`${index}-${item.nombre}`} style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 14, padding: 12 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 0.6fr 0.6fr auto", gap: 10, alignItems: "end" }}>
                        <InputField
                          label="Nombre del paso"
                          value={item.nombre}
                          onChange={(value) => updateChecklistItem(index, "nombre", value)}
                        />
                        <InputField
                          label="Orden"
                          type="number"
                          value={item.orden}
                          onChange={(value) => updateChecklistItem(index, "orden", value)}
                        />
                        <div className="input-field">
                          <label>Obs</label>
                          <div className="input-wrapper" style={{ paddingTop: 8 }}>
                            <input
                              type="checkbox"
                              checked={item.requiere_obs}
                              onChange={(e) => updateChecklistItem(index, "requiere_obs", e.target.checked)}
                            />
                          </div>
                        </div>
                        <button type="button" className="secondary-button" onClick={() => removeChecklistItem(index)}>
                          Quitar
                        </button>
                      </div>
                      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                        <button type="button" className="secondary-button" onClick={() => moveChecklistItem(index, -1)} disabled={index === 0}>
                          Subir
                        </button>
                        <button type="button" className="secondary-button" onClick={() => moveChecklistItem(index, 1)} disabled={index === form.checklist_items.length - 1}>
                          Bajar
                        </button>
                        <label style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
                          <input
                            type="checkbox"
                            checked={item.activo}
                            onChange={(e) => updateChecklistItem(index, "activo", e.target.checked)}
                          />
                          Paso activo
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input type="checkbox" checked={form.activo} onChange={(e) => updateField("activo")(e.target.checked)} />
                Servicio activo
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  checked={form.permite_doble_booking}
                  onChange={(e) => updateField("permite_doble_booking")(e.target.checked)}
                />
                Permite doble booking
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  checked={form.requiere_bloqueo_consecutivo}
                  onChange={(e) => updateField("requiere_bloqueo_consecutivo")(e.target.checked)}
                />
                Requiere bloqueo consecutivo
              </label>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button type="button" className="secondary-button" onClick={() => setDrawerOpen(false)}>
                  Cancelar
                </button>
                <Button loading={saving}>{editingId ? "Guardar cambios" : "Crear servicio"}</Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {toggleConflict ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.52)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 70,
            padding: 20,
          }}
        >
          <div style={{ width: "min(520px, 100%)", background: "#101923", color: "#f4f7fb", borderRadius: 18, padding: 24 }}>
            <h3 style={{ marginTop: 0 }}>Confirmar desactivacion</h3>
            <p style={{ color: "rgba(244,247,251,0.78)" }}>
              {toggleConflict.mensaje} {toggleConflict.citas_afectadas ? `Hay ${toggleConflict.citas_afectadas} citas futuras pendientes.` : ""}
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button type="button" className="secondary-button" onClick={() => setToggleConflict(null)}>
                Cancelar
              </button>
              <Button loading={saving} onClick={forceDeactivate}>
                Desactivar de todas formas
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
