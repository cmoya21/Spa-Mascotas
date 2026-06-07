import { useEffect, useMemo, useState } from "react";

import Alert from "../components/shared/Alert";
import InputField from "../components/shared/InputField";
import {
  apiCrearBloqueoDisponibilidad,
  apiEliminarBloqueoDisponibilidad,
  apiGetGroomersDisponibilidad,
  apiGetHorarioGeneral,
  apiListBloqueosDisponibilidad,
  apiUpdateGroomerDisponibilidad,
  apiUpdateHorarioGeneral
} from "../api/disponibilidadApi";

const diasSemana = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];

const createDay = (dia_semana, activo = true) => ({
  dia_semana,
  hora_inicio: "09:00",
  hora_fin: "18:00",
  buffer_minutos: 15,
  activo,
  intervalo_descanso: { inicio: "13:00", fin: "14:00" }
});

const buildWeek = (active = true) => Array.from({ length: 7 }, (_, index) => createDay(index, active));

const normalizeWeek = (days, defaultActive = true) =>
  buildWeek(defaultActive).map((item) => {
    const source = (days || []).find((day) => Number(day.dia_semana) === item.dia_semana) || {};
    return {
      ...item,
      ...source,
      dia_semana: item.dia_semana,
      intervalo_descanso: source.intervalo_descanso || item.intervalo_descanso,
      activo: source.activo ?? item.activo
    };
  });

const parseTime = (value) => {
  if (!value || typeof value !== "string") return null;
  const [hours, minutes] = value.split(":").map((part) => Number(part));
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  return hours * 60 + minutes;
};

const resolveError = (err, fallback) => {
  const response = err?.response;
  const message = response?.data?.message;
  const details = response?.data?.details;
  if (details) {
    const firstKey = Object.keys(details)[0];
    if (firstKey && details[firstKey]?.length) {
      return `${message || fallback}: ${details[firstKey][0]}`;
    }
  }
  return message || fallback;
};

const validateWeek = (days, scope) => {
  for (const day of days) {
    if (!day.activo) continue;
    const start = parseTime(day.hora_inicio);
    const end = parseTime(day.hora_fin);
    if (start === null || end === null || start >= end) {
      return `El horario de ${diasSemana[day.dia_semana]} en ${scope} no es valido.`;
    }
  }
  return "";
};

export default function PanelDisponibilidad() {
  const [activeTab, setActiveTab] = useState("general");
  const [loading, setLoading] = useState(true);
  const [savingGeneral, setSavingGeneral] = useState(false);
  const [savingGroomer, setSavingGroomer] = useState(false);
  const [savingBloqueo, setSavingBloqueo] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [generalDays, setGeneralDays] = useState(buildWeek(true));
  const [groomers, setGroomers] = useState([]);
  const [selectedGroomerId, setSelectedGroomerId] = useState("");
  const [groomerDays, setGroomerDays] = useState(buildWeek(true));
  const [bloqueos, setBloqueos] = useState([]);
  const [bloqueosRange, setBloqueosRange] = useState({ fecha_inicio: "", fecha_fin: "" });
  const [bloqueoForm, setBloqueoForm] = useState({
    groomer_id: "",
    fecha_inicio: "",
    fecha_fin: "",
    tipo_bloqueo: "mantenimiento",
    descripcion: "",
    forzar: false
  });

  const groomerOptions = useMemo(
    () =>
      groomers.map((groomer) => ({
        ...groomer,
        nombre_completo: `${groomer.nombre || ""} ${groomer.apellido || ""}`.trim() || `Groomer ${groomer.id}`
      })),
    [groomers]
  );

  const selectedGroomer = groomerOptions.find((item) => String(item.id) === String(selectedGroomerId));

  const loadGeneral = async () => {
    const data = await apiGetHorarioGeneral();
    setGeneralDays(normalizeWeek(data.dias || [], true));
  };

  const loadGroomers = async () => {
    const data = await apiGetGroomersDisponibilidad();
    const items = data.groomers || [];
    setGroomers(items);
    if (!selectedGroomerId && items.length) {
      setSelectedGroomerId(String(items[0].id));
    }
  };

  const loadBloqueos = async (params) => {
    const data = await apiListBloqueosDisponibilidad(params);
    setBloqueos(data.bloqueos || []);
  };

  useEffect(() => {
    let mounted = true;

    const boot = async () => {
      setLoading(true);
      const results = await Promise.allSettled([loadGeneral(), loadGroomers(), loadBloqueos()]);
      if (!mounted) return;

      const firstError = results.find((result) => result.status === "rejected");
      if (firstError) {
        setError(resolveError(firstError.reason, "No se pudo cargar la disponibilidad."));
      }
      setLoading(false);
    };

    boot();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const item = groomers.find((groomer) => String(groomer.id) === String(selectedGroomerId));
    setGroomerDays(normalizeWeek(item?.disponibilidad || [], true));
  }, [selectedGroomerId, groomers]);

  const updateGeneralDay = (index, field, value) => {
    setGeneralDays((prev) =>
      prev.map((day, dayIndex) =>
        dayIndex === index
          ? {
              ...day,
              [field]: value
            }
          : day
      )
    );
  };

  const updateGroomerDay = (index, field, value) => {
    setGroomerDays((prev) =>
      prev.map((day, dayIndex) =>
        dayIndex === index
          ? {
              ...day,
              [field]: value
            }
          : day
      )
    );
  };

  const handleSaveGeneral = async () => {
    setError("");
    setSuccess("");
    const validation = validateWeek(generalDays, "el horario general");
    if (validation) {
      setError(validation);
      return;
    }

    setSavingGeneral(true);
    try {
      const data = await apiUpdateHorarioGeneral({ dias: generalDays });
      setGeneralDays(normalizeWeek(data.dias || [], true));
      setSuccess("Horario general guardado correctamente.");
    } catch (err) {
      setError(resolveError(err, "No se pudo guardar el horario general."));
    } finally {
      setSavingGeneral(false);
    }
  };

  const handleSaveGroomer = async () => {
    setError("");
    setSuccess("");
    if (!selectedGroomerId) {
      setError("Selecciona un groomer primero.");
      return;
    }

    const validation = validateWeek(groomerDays, "la disponibilidad del groomer");
    if (validation) {
      setError(validation);
      return;
    }

    setSavingGroomer(true);
    try {
      await apiUpdateGroomerDisponibilidad(selectedGroomerId, { dias: groomerDays });
      const data = await apiGetGroomersDisponibilidad();
      const items = data.groomers || [];
      setGroomers(items);
      setSelectedGroomerId((current) => current || (items[0] ? String(items[0].id) : ""));
      setSuccess("Disponibilidad del groomer guardada correctamente.");
    } catch (err) {
      setError(resolveError(err, "No se pudo guardar la disponibilidad del groomer."));
    } finally {
      setSavingGroomer(false);
    }
  };

  const handleFilterBloqueos = async () => {
    setError("");
    try {
      const params = bloqueosRange.fecha_inicio && bloqueosRange.fecha_fin ? bloqueosRange : undefined;
      await loadBloqueos(params);
    } catch (err) {
      setError(resolveError(err, "No se pudieron cargar los bloqueos."));
    }
  };

  const handleCreateBloqueo = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!bloqueoForm.fecha_inicio || !bloqueoForm.fecha_fin || !bloqueoForm.tipo_bloqueo) {
      setError("Completa las fechas y el tipo de bloqueo.");
      return;
    }

    setSavingBloqueo(true);
    try {
      await apiCrearBloqueoDisponibilidad(
        {
          groomer_id: bloqueoForm.groomer_id || null,
          fecha_inicio: bloqueoForm.fecha_inicio,
          fecha_fin: bloqueoForm.fecha_fin,
          tipo_bloqueo: bloqueoForm.tipo_bloqueo,
          descripcion: bloqueoForm.descripcion || null
        },
        bloqueoForm.forzar
      );
      setBloqueoForm((prev) => ({
        ...prev,
        fecha_inicio: "",
        fecha_fin: "",
        descripcion: "",
        forzar: false
      }));
      await loadBloqueos();
      setSuccess(bloqueoForm.forzar ? "Bloqueo guardado con fuerza." : "Bloqueo guardado correctamente.");
    } catch (err) {
      if (err?.response?.status === 409 && !bloqueoForm.forzar) {
        setError("Conflicto detectado con citas o bloqueos existentes. Activa 'Forzar' si necesitas continuar.");
      } else {
        setError(resolveError(err, "No se pudo guardar el bloqueo."));
      }
    } finally {
      setSavingBloqueo(false);
    }
  };

  const handleDeleteBloqueo = async (bloqueoId) => {
    setError("");
    try {
      await apiEliminarBloqueoDisponibilidad(bloqueoId);
      await loadBloqueos(
        bloqueosRange.fecha_inicio && bloqueosRange.fecha_fin ? bloqueosRange : undefined
      );
      setSuccess("Bloqueo eliminado correctamente.");
    } catch (err) {
      setError(resolveError(err, "No se pudo eliminar el bloqueo."));
    }
  };

  return (
    <div className="page-shell agenda-layout">
      <div className="page-content">
        <header className="agenda-header">
          <div>
            <h2>Módulo 2.1 - Gestión de disponibilidad</h2>
            <p>Admin y Recepción pueden editar horarios, disponibilidad por groomer y bloqueos.</p>
          </div>
          <div className="admin-metrics">
            <div>
              <span>Groomers</span>
              <strong>{groomers.length}</strong>
            </div>
            <div>
              <span>Bloqueos</span>
              <strong>{bloqueos.length}</strong>
            </div>
          </div>
        </header>

        <Alert message={error || success} success={!!success} />

        {loading ? (
          <section className="agenda-card">
            <p>Cargando disponibilidad...</p>
          </section>
        ) : (
          <div className="agenda-grid">
            {activeTab === "general" && (
              <section className="agenda-card agenda-wide">
                <h3>Horario general del spa</h3>
                <p className="section-note">Define los días laborables y sus horas de atención.</p>
                <div className="schedule-grid">
                  {generalDays.map((day, index) => (
                    <div key={`general-${day.dia_semana}`} className="schedule-row">
                      <span>{diasSemana[day.dia_semana]}</span>
                      <input
                        type="time"
                        value={day.hora_inicio}
                        onChange={(event) => updateGeneralDay(index, "hora_inicio", event.target.value)}
                      />
                      <input
                        type="time"
                        value={day.hora_fin}
                        onChange={(event) => updateGeneralDay(index, "hora_fin", event.target.value)}
                      />
                      <label className="toggle-inline">
                        <input
                          type="checkbox"
                          checked={day.activo}
                          onChange={(event) => updateGeneralDay(index, "activo", event.target.checked)}
                        />
                        Activo
                      </label>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  className="primary-button"
                  onClick={handleSaveGeneral}
                  disabled={savingGeneral}
                >
                  {savingGeneral ? "Guardando..." : "Guardar horario general"}
                </button>
              </section>
            )}

            {activeTab === "groomer" && (
              <section className="agenda-card agenda-wide">
                <h3>Disponibilidad por groomer</h3>
                <div className="input-field">
                  <label>Selecciona groomer</label>
                  <div className="input-wrapper">
                    <select
                      className="select-field"
                      value={selectedGroomerId}
                      onChange={(event) => setSelectedGroomerId(event.target.value)}
                    >
                      <option value="">Selecciona un groomer</option>
                      {groomerOptions.map((groomer) => (
                        <option key={groomer.id} value={groomer.id}>
                          {groomer.nombre_completo}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {selectedGroomer && (
                  <p className="section-note">
                    Editando {selectedGroomer.nombre_completo}. Capacidad diaria: {selectedGroomer.capacidad_diaria}.
                  </p>
                )}

                <div className="schedule-grid">
                  {groomerDays.map((day, index) => (
                    <div key={`groomer-${day.dia_semana}`} className="schedule-row">
                      <span>{diasSemana[day.dia_semana]}</span>
                      <input
                        type="time"
                        value={day.hora_inicio}
                        onChange={(event) => updateGroomerDay(index, "hora_inicio", event.target.value)}
                      />
                      <input
                        type="time"
                        value={day.hora_fin}
                        onChange={(event) => updateGroomerDay(index, "hora_fin", event.target.value)}
                      />
                      <input
                        type="number"
                        min="0"
                        value={day.buffer_minutos}
                        onChange={(event) => updateGroomerDay(index, "buffer_minutos", event.target.value)}
                      />
                      <input
                        type="time"
                        value={day.intervalo_descanso?.inicio || ""}
                        onChange={(event) =>
                          updateGroomerDay(index, "intervalo_descanso", {
                            ...day.intervalo_descanso,
                            inicio: event.target.value
                          })
                        }
                      />
                      <input
                        type="time"
                        value={day.intervalo_descanso?.fin || ""}
                        onChange={(event) =>
                          updateGroomerDay(index, "intervalo_descanso", {
                            ...day.intervalo_descanso,
                            fin: event.target.value
                          })
                        }
                      />
                      <label className="toggle-inline">
                        <input
                          type="checkbox"
                          checked={day.activo}
                          onChange={(event) => updateGroomerDay(index, "activo", event.target.checked)}
                        />
                        Activo
                      </label>
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  className="primary-button"
                  onClick={handleSaveGroomer}
                  disabled={savingGroomer}
                >
                  {savingGroomer ? "Guardando..." : "Guardar disponibilidad"}
                </button>
              </section>
            )}

            {activeTab === "bloqueos" && (
              <section className="agenda-card agenda-wide">
                <h3>Bloqueos de calendario</h3>
                <div className="agenda-filters">
                  <InputField
                    label="Desde (YYYY-MM-DD)"
                    value={bloqueosRange.fecha_inicio}
                    onChange={(value) => setBloqueosRange((prev) => ({ ...prev, fecha_inicio: value }))}
                  />
                  <InputField
                    label="Hasta (YYYY-MM-DD)"
                    value={bloqueosRange.fecha_fin}
                    onChange={(value) => setBloqueosRange((prev) => ({ ...prev, fecha_fin: value }))}
                  />
                  <button type="button" className="ghost-button" onClick={handleFilterBloqueos}>
                    Filtrar bloqueos
                  </button>
                </div>

                <form onSubmit={handleCreateBloqueo} className="form-group">
                  <div className="input-field">
                    <label>Groomer (opcional)</label>
                    <div className="input-wrapper">
                      <select
                        className="select-field"
                        value={bloqueoForm.groomer_id}
                        onChange={(event) =>
                          setBloqueoForm((prev) => ({ ...prev, groomer_id: event.target.value }))
                        }
                      >
                        <option value="">Global (todos)</option>
                        {groomerOptions.map((groomer) => (
                          <option key={groomer.id} value={groomer.id}>
                            {groomer.nombre_completo}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <InputField
                    label="Fecha inicio"
                    type="datetime-local"
                    value={bloqueoForm.fecha_inicio}
                    onChange={(value) => setBloqueoForm((prev) => ({ ...prev, fecha_inicio: value }))}
                  />
                  <InputField
                    label="Fecha fin"
                    type="datetime-local"
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

                  <label className="toggle-inline" style={{ marginTop: 8 }}>
                    <input
                      type="checkbox"
                      checked={bloqueoForm.forzar}
                      onChange={(event) => setBloqueoForm((prev) => ({ ...prev, forzar: event.target.checked }))}
                    />
                    Forzar aunque exista conflicto
                  </label>

                  <button type="submit" className="primary-button" disabled={savingBloqueo}>
                    {savingBloqueo ? "Guardando..." : "Guardar bloqueo"}
                  </button>
                </form>

                <div className="agenda-list">
                  {bloqueos.map((item) => (
                    <div key={item.id} className="agenda-row">
                      <span>{item.tipo_bloqueo}</span>
                      <span>{new Date(item.fecha_inicio).toLocaleString()}</span>
                      <span>{item.groomer_id ? `Groomer ${item.groomer_id}` : "Global"}</span>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleDeleteBloqueo(item.id)}
                      >
                        Eliminar
                      </button>
                    </div>
                  ))}
                  {!bloqueos.length && <div className="admin-empty">Sin bloqueos registrados.</div>}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
