import { useEffect, useState } from "react";

import Alert from "../components/shared/Alert";
import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";
import CalendarGrid from "../components/agenda/CalendarGrid.jsx";
import {
  apiActualizarEstadoServicio,
  apiActualizarServicio,
  apiCrearBloqueo,
  apiCrearServicio,
  apiEliminarBloqueo,
  apiGetDisponibilidadGroomers,
  apiGetHorarioSpa,
  apiListBloqueos,
  apiListServicios,
  apiGetAgendaDia,
  apiUpdateDisponibilidadGroomer,
  apiUpdateHorarioSpa,
} from "../api/agendaApi";
import { apiGetAlertasInventarioActivos } from "../api/alertasApi";
import { apiListClientes, apiListGroomers } from "../api/adminApi";
import { apiListProductos } from "../api/inventarioApi";
import { apiListMascotas } from "../api/mascotasApi";
// pagosApi queda disponible para futuras integraciones de factura manual.
import { apiListCobrosPendientes, apiPagarCita } from "../api/cobrosApi";
import PanelCobros from "../components/cobros/PanelCobros";
import { apiClient } from "../api/authApi";
import { calcularDesglose } from "../utils/calcularDuracion";
import CampanaNotificaciones from "../components/shared/CampanaNotificaciones.jsx";
import useAuth from "../hooks/useAuth";

const diasSemana = [
  "Domingo",
  "Lunes",
  "Martes",
  "Miercoles",
  "Jueves",
  "Viernes",
  "Sabado"
];

const createServicioForm = () => ({
  nombre: "",
  descripcion: "",
  precio_base: "",
  duracion_base_minutos: "",
  permite_doble_booking: false,
  requiere_bloqueo_consecutivo: false,
  factor_tamano_raza: {
    pequeno: 1.0,
    mediano: 1.15,
    grande: 1.3,
    gigante: 1.3
  },
  consumo_insumos: []
});

const buildDefaultSchedule = (activoDefault = true) =>
  diasSemana.map((_, index) => ({
    dia_semana: index,
    hora_inicio: "09:00",
    hora_fin: "18:00",
    activo: activoDefault,
    buffer_minutos: 15,
    intervalo_descanso: { inicio: "13:00", fin: "14:00" }
  }));

const mergeSchedule = (entries, activoDefault = true) => {
  const base = buildDefaultSchedule(activoDefault);
  (entries || []).forEach((item) => {
    const idx = item.dia_semana;
    if (idx === undefined) return;
    base[idx] = {
      ...base[idx],
      ...item,
      activo: item.activo !== undefined ? item.activo : true
    };
  });
  return base;
};

export default function AgendaPage() {
  const { usuario } = useAuth();
  const esAdmin = usuario?.rol === "Admin";
  const [servicios, setServicios] = useState([]);
  const [productos, setProductos] = useState([]);
  const [spaSchedule, setSpaSchedule] = useState([]);
  const [disponibilidadGroomers, setDisponibilidadGroomers] = useState([]);
  const [groomerScheduleId, setGroomerScheduleId] = useState("");
  const [groomerSchedule, setGroomerSchedule] = useState([]);
  const [bloqueos, setBloqueos] = useState([]);
  const [bloqueosRange, setBloqueosRange] = useState({
    fecha_inicio: "",
    fecha_fin: ""
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [section, setSection] = useState("slots");
  const [groomers, setGroomers] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [mascotas, setMascotas] = useState([]);
  const [clienteId, setClienteId] = useState("");
  const [mascotaId, setMascotaId] = useState("");

  const [servicioForm, setServicioForm] = useState(createServicioForm());
  const [servicioEditId, setServicioEditId] = useState(null);
  const [insumoDraft, setInsumoDraft] = useState({ producto_id: "", cantidad: "" });
  const [insumos, setInsumos] = useState(servicioForm.consumo_insumos || []);
  const [slotForm, setSlotForm] = useState({ groomer_id: null, groomer_nombre: "", fecha: "", hora_inicio: "" });
  const [slotGroomerId, setSlotGroomerId] = useState("");
  const [durationInfo, setDurationInfo] = useState(null);
  const [diaData, setDiaData] = useState(null);
  const [totalCriticos, setTotalCriticos] = useState(0);

  const [bloqueoForm, setBloqueoForm] = useState({
    groomer_id: "",
    fecha_inicio: "",
    fecha_fin: "",
    tipo_bloqueo: "feriado",
    descripcion: ""
  });
  const [cobrosPendientes, setCobrosPendientes] = useState([]);

  useEffect(() => {
    if (esAdmin && section === "slots") {
      setSection("servicios");
      return;
    }
    if (!esAdmin && (section === "servicios" || section === "disponibilidad")) {
      setSection("slots");
    }
  }, [esAdmin]);

  useEffect(() => {
    apiListServicios()
      .then((data) => setServicios(data.servicios || []))
      .catch(() => setError("No se pudieron cargar servicios."));
    apiListProductos()
      .then((data) => setProductos(data.productos || []))
      .catch(() => setError("No se pudieron cargar productos."));
    apiListGroomers()
      .then((data) => setGroomers(data.groomers || []))
      .catch(() => setError("No se pudieron cargar groomers."));
    apiListClientes()
      .then((data) => setClientes(data.clientes || []))
      .catch(() => setError("No se pudieron cargar clientes."));
    apiGetHorarioSpa()
      .then((data) => setSpaSchedule(data.dias || []))
      .catch(() => setError("No se pudo cargar el horario del spa."));
    apiGetDisponibilidadGroomers()
      .then((data) => setDisponibilidadGroomers(data.groomers || []))
      .catch(() => setError("No se pudo cargar la disponibilidad."));
    apiListBloqueos()
      .then((data) => setBloqueos(data.bloqueos || []))
      .catch(() => setError("No se pudieron cargar bloqueos."));
    apiListCobrosPendientes()
      .then((data) => setCobrosPendientes(data.pendientes || []))
      .catch(() => setError("No se pudieron cargar cobros pendientes."));
  }, []);

  useEffect(() => {
    const cargarAlertas = async () => {
      try {
        const data = await apiGetAlertasInventarioActivos();
        setTotalCriticos(data.total_criticos || 0);
      } catch {
        setTotalCriticos(0);
      }
    };

    cargarAlertas();
    const intervalId = setInterval(cargarAlertas, 5 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    if (!clienteId) {
      setMascotas([]);
      setMascotaId("");
      return;
    }
    apiListMascotas(parseInt(clienteId, 10))
      .then((data) => setMascotas(data.mascotas || []))
      .catch(() => setError("No se pudieron cargar mascotas."));
  }, [clienteId]);

  useEffect(() => {
    const mascota = mascotas.find((item) => String(item.id) === String(mascotaId));
    const servicio = servicios.find((item) => String(item.id) === String(slotForm.servicio_id));
    if (!mascota || !servicio) {
      setDurationInfo(null);
      return;
    }
    const info = calcularDesglose(
      servicio.duracion_base_minutos,
      mascota.peso_kg,
      mascota.temperamento,
      servicio.factor_tamano_raza
    );
    setDurationInfo(info);
  }, [mascotaId, mascotas, servicios, slotForm.servicio_id]);

  useEffect(() => {
    if (!slotGroomerId && groomers.length) {
      setSlotGroomerId(String(groomers[0].id));
    }
  }, [groomers, slotGroomerId]);

  useEffect(() => {
    if (!groomerScheduleId) {
      setGroomerSchedule([]);
      return;
    }
    const item = disponibilidadGroomers.find(
      (groomer) => String(groomer.id) === String(groomerScheduleId)
    );
    setGroomerSchedule(mergeSchedule(item?.disponibilidad, true));
  }, [groomerScheduleId, disponibilidadGroomers]);

  const resetServicioForm = () => {
    setServicioForm(createServicioForm());
    setServicioEditId(null);
  };

  const handleGuardarServicio = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    const payload = {
      ...servicioForm,
      precio_base: parseFloat(servicioForm.precio_base || 0),
      duracion_base_minutos: parseInt(servicioForm.duracion_base_minutos || 0, 10)
    };
    try {
      if (servicioEditId) {
        await apiActualizarServicio(servicioEditId, payload);
        setSuccess("Servicio actualizado.");
      } else {
        await apiCrearServicio(payload);
        setSuccess("Servicio guardado.");
      }
      const data = await apiListServicios();
      setServicios(data.servicios || []);
      resetServicioForm();
    } catch (err) {
      setError("No se pudo guardar el servicio.");
    }
  };

  const handleEditarServicio = (servicio) => {
    setServicioEditId(servicio.id);
    setServicioForm({
      nombre: servicio.nombre || "",
      descripcion: servicio.descripcion || "",
      precio_base: servicio.precio_base || "",
      duracion_base_minutos: servicio.duracion_base_minutos || "",
      permite_doble_booking: !!servicio.permite_doble_booking,
      requiere_bloqueo_consecutivo: !!servicio.requiere_bloqueo_consecutivo,
      factor_tamano_raza: servicio.factor_tamano_raza || createServicioForm().factor_tamano_raza,
      consumo_insumos: servicio.consumo_insumos || []
    });
  };

  const handleEliminarBloqueo = async (bloqueoId) => {
    setError("");
    try {
      await apiEliminarBloqueo(bloqueoId);
      const data = await apiListBloqueos();
      setBloqueos(data.bloqueos || []);
    } catch (err) {
      setError("No se pudo eliminar el bloqueo.");
    }
  };

  // Sync servicioForm.consumo_insumos with local `insumos` state
  useEffect(() => {
    setServicioForm((prev) => ({ ...prev, consumo_insumos: insumos }));
  }, [insumos]);

  useEffect(() => {
    setInsumos(servicioForm.consumo_insumos || []);
  }, [servicioForm]);

  // Handlers requested by user
  const handleAgregarInsumo = () => {
    setInsumos((prev) => [...prev, { producto_id: "", cantidad: 1 }]);
  };

  const handleEliminarInsumo = (index) => {
    setInsumos((prev) => prev.filter((_, i) => i !== index));
  };

  const handleToggleServicio = async (servicio, desiredActivo) => {
    setError("");
    setSuccess("");
    const nuevoActivo = typeof desiredActivo === "boolean" ? desiredActivo : !servicio.activo;
    try {
      await apiActualizarEstadoServicio(servicio.id, { activo: nuevoActivo });
      const data = await apiListServicios();
      setServicios(data.servicios || []);
      setSuccess("Estado de servicio actualizado.");
    } catch (err) {
      const status = err?.response?.status;
      const payload = err?.response?.data || {};
      if (status === 409) {
        const citas = payload?.citas_afectadas || [];
        const confirmMsg = `Hay ${citas.length} cita(s) que se verían afectadas. ¿Deseas continuar?`;
        // Simple confirmation modal prompt
        if (window.confirm(confirmMsg)) {
          try {
            await apiClient.patch(`/api/servicios/${servicio.id}/estado?forzar=true`, { activo: nuevoActivo });
            const data = await apiListServicios();
            setServicios(data.servicios || []);
            setSuccess("Estado de servicio actualizado (forzado).");
          } catch (err2) {
            setError("No se pudo forzar el cambio de estado.");
          }
        } else {
          setError("Operación cancelada por el usuario.");
        }
      } else {
        setError("No se pudo actualizar el estado del servicio.");
      }
    }
  };

  // updateSpaDay: dual behavior — si se llama con (index, field, value) actualiza localmente;
  // si se llama sin argumentos, recarga datos del dia actual desde el servidor.
  const updateSpaDay = async (index, field, value) => {
    if (typeof index === "number") {
      setSpaSchedule((prev) => {
        const next = Array.isArray(prev) ? [...prev] : buildDefaultSchedule(true);
        next[index] = { ...next[index], [field]: value };
        return next;
      });
      return;
    }
    try {
      const fechaActual = new Date();
      const fecha = fechaActual.toISOString().split("T")[0];
      const datos = await apiGetAgendaDia({ fecha });
      setDiaData(datos);
    } catch (err) {
      setError("No se pudieron cargar los datos del dia.");
    }
  };

  // Minimal stubs / implementations to keep JSX functional
  const handleGuardarSpa = async () => {
    setError("");
    setSuccess("");
    try {
      await apiUpdateHorarioSpa(spaSchedule);
      setSuccess("Horario del spa actualizado.");
    } catch (err) {
      setError("No se pudo guardar el horario del spa.");
    }
  };

  const updateGroomerDay = (index, field, value) => {
    setGroomerSchedule((prev) => {
      const next = Array.isArray(prev) ? [...prev] : buildDefaultSchedule(true);
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleGuardarGroomer = async () => {
    setError("");
    setSuccess("");
    if (!groomerScheduleId) {
      setError("Selecciona un groomer antes de guardar.");
      return;
    }
    try {
      await apiUpdateDisponibilidadGroomer(groomerScheduleId, { disponibilidad: groomerSchedule });
      setSuccess("Disponibilidad del groomer guardada.");
    } catch (err) {
      setError("No se pudo guardar la disponibilidad del groomer.");
    }
  };

  const handleRefrescarBloqueos = async () => {
    try {
      const data = await apiListBloqueos(bloqueosRange);
      setBloqueos(data.bloqueos || []);
    } catch (err) {
      setError("No se pudieron cargar bloqueos.");
    }
  };

  const handleCrearBloqueo = async (event) => {
    if (event && event.preventDefault) event.preventDefault();
    setError("");
    setSuccess("");
    try {
      await apiCrearBloqueo(bloqueoForm);
      setSuccess("Bloqueo creado.");
      const data = await apiListBloqueos();
      setBloqueos(data.bloqueos || []);
    } catch (err) {
      setError("No se pudo crear el bloqueo.");
    }
  };

  return (
    <div className="page-shell agenda-layout">
      <div className="page-content">
        <header className="agenda-header">
          <div>
            <h2>Agenda y Slots</h2>
            <p>Admin y Recepcion pueden definir horarios del spa y controlar reservas.</p>
          </div>
        </header>

        <div className="agenda-grid">

          {esAdmin && section === "servicios" && (
            <section className="agenda-card">
              <h3>Servicios</h3>
                <form onSubmit={handleGuardarServicio} className="form-group">

                  <div className="input-field">
                  <div className="input-wrapper">
                  <select
                      className="select-field"
                      value={insumoDraft.producto_id}
                      onChange={(e) => setInsumoDraft((prev) => ({ ...prev, producto_id: e.target.value }))}
                    >
                      <option value="">Producto</option>
                      {productos.map((producto) => (
                        <option key={producto.id} value={producto.id}>
                          {producto.nombre}
                        </option>
                      ))}
                    </select>
                    </div>
                    <InputField
                      label="Cantidad"
                      value={insumoDraft.cantidad}
                      onChange={(value) =>
                        setInsumoDraft((prev) => ({ ...prev, cantidad: value }))
                      }
                    />
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={handleAgregarInsumo}
                    >
                      Agregar
                    </button>
                  </div>
                  <div className="insumo-list">
                    {servicioForm.consumo_insumos.map((item, index) => (
                      <div key={`${item.producto_id}-${index}`} className="insumo-item">
                        <span>
                          {productos.find((p) => String(p.id) === String(item.producto_id))?.nombre ||
                            `Producto ${item.producto_id}`}
                        </span>
                        <span>{item.cantidad}</span>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => handleEliminarInsumo(index)}
                        >
                          Quitar
                        </button>
                      </div>
                    ))}
                  </div>
                <Button>{servicioEditId ? "Guardar cambios" : "Guardar servicio"}</Button>
                {servicioEditId && (
                  <button type="button" className="ghost-button" onClick={resetServicioForm}>
                    Cancelar edicion
                  </button>
                )}
              </form>
              <div className="agenda-list">
                {servicios.map((item) => (
                  <div key={item.id} className="agenda-row">
                    <span>{item.nombre}</span>
                    <span>{item.duracion_base_minutos} min</span>
                    <span>Bs {item.precio_base}</span>
                    <div className="agenda-row-actions">
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleEditarServicio(item)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleToggleServicio(item, false)}
                      >
                        Desactivar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {esAdmin && section === "disponibilidad" && (
            <section className="agenda-card agenda-wide">
              <h3>Horario del spa</h3>
              <p className="section-note">
                La edición detallada de horarios y disponibilidad vive en el panel dedicado.
              </p>
              <div className="admin-empty" style={{ marginBottom: 16 }}>
                Aquí solo dejamos acceso directo al panel para evitar una vista saturada en Recepción.
              </div>
              <a className="primary-button" href="/disponibilidad">
                Abrir panel de disponibilidad
              </a>
            </section>
          )}

          {section === "bloqueos" && (
            <section className="agenda-card">
              <h3>Bloqueos</h3>
              <div className="agenda-filters">
                <InputField
                  label="Desde (YYYY-MM-DD)"
                  value={bloqueosRange.fecha_inicio}
                  onChange={(value) =>
                    setBloqueosRange((prev) => ({ ...prev, fecha_inicio: value }))
                  }
                />
                <InputField
                  label="Hasta (YYYY-MM-DD)"
                  value={bloqueosRange.fecha_fin}
                  onChange={(value) =>
                    setBloqueosRange((prev) => ({ ...prev, fecha_fin: value }))
                  }
                />
                <button type="button" className="ghost-button" onClick={handleRefrescarBloqueos}>
                  Filtrar bloqueos
                </button>
              </div>
              <form onSubmit={handleCrearBloqueo} className="form-group">
                <div className="input-field">
                  <label>Groomer (opcional)</label>
                  <div className="input-wrapper">
                    <select
                      className="select-field"
                      value={bloqueoForm.groomer_id}
                      onChange={(e) => setBloqueoForm((prev) => ({ ...prev, groomer_id: e.target.value }))}
                    >
                      <option value="">Global (todos)</option>
                      {groomers.map((groomer) => (
                        <option key={groomer.id} value={groomer.id}>
                          {groomer.nombre} {groomer.apellido || ""}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <InputField
                  label="Fecha inicio (YYYY-MM-DDTHH:MM)"
                  value={bloqueoForm.fecha_inicio}
                  onChange={(value) => setBloqueoForm((prev) => ({ ...prev, fecha_inicio: value }))}
                />
                <InputField
                  label="Fecha fin (YYYY-MM-DDTHH:MM)"
                  value={bloqueoForm.fecha_fin}
                  onChange={(value) => setBloqueoForm((prev) => ({ ...prev, fecha_fin: value }))}
                />
                <InputField
                  label="Tipo"
                  value={bloqueoForm.tipo_bloqueo}
                  onChange={(value) => setBloqueoForm((prev) => ({ ...prev, tipo_bloqueo: value }))}
                />
                <InputField
                  label="Descripcion"
                  value={bloqueoForm.descripcion}
                  onChange={(value) => setBloqueoForm((prev) => ({ ...prev, descripcion: value }))}
                />
                <Button>Guardar bloqueo</Button>
              </form>
              <div className="agenda-list">
                {bloqueos.map((item) => (
                  <div key={item.id} className="agenda-row">
                    <span>{item.tipo_bloqueo}</span>
                    <span>{new Date(item.fecha_inicio).toLocaleString()}</span>
                    <span>{item.groomer_id ? `Groomer ${item.groomer_id}` : "Todos"}</span>
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => handleEliminarBloqueo(item.id)}
                    >
                      Eliminar
                    </button>
                  </div>
                ))}
                {!bloqueos.length && <div className="admin-empty">Sin bloqueos registrados.</div>}
              </div>
            </section>
          )}

          {section === "slots" && <CalendarGrid />}

          {section === "reprogramacion" && (
            <section className="agenda-card">
              <h3>Reprogramacion</h3>
              <p className="section-note">
                Mueve citas con arrastrar y soltar. Esta vista se activara cuando
                conectemos el calendario interactivo.
              </p>
              <ul className="info-list">
                <li>Calendario maestro con columnas por groomer.</li>
                <li>Control de capacidad para evitar solapamientos.</li>
                <li>Historial de cambios por usuario.</li>
              </ul>
            </section>
          )}

          {section === "cobranza" && (
            <section className="agenda-card">
              <h3>Cobranza</h3>
              <p className="section-note">
                Registra pagos por efectivo, QR o transferencia una vez confirmada la cita.
              </p>
              <ul className="info-list">
                <li>Punto de venta para servicios y productos.</li>
                <li>Promociones y descuentos por fidelidad.</li>
                <li>Emision automatica de recibos y cierre de caja.</li>
              </ul>
              <PanelCobros
                pendientes={cobrosPendientes}
                onPagar={async (citaId, payload) => {
                  setError("");
                  try {
                    await apiPagarCita(citaId, payload);
                    setSuccess("Pago registrado.");
                    const data = await apiListCobrosPendientes();
                    setCobrosPendientes(data.pendientes || []);
                  } catch (err) {
                    setError("No se pudo registrar el pago.");
                  }
                }}
              />
            </section>
          )}
        </div>

        {success && <Alert message={success} success />}
        <Alert message={error} />
      </div>
    </div>
  );
}
