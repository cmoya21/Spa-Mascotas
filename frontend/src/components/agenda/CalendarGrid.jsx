import { Fragment, useEffect, useMemo, useState } from "react";

import {
  apiActualizarEstadoCita,
  apiCancelarCita,
  apiConfirmarCita,
  apiCrearBloqueo,
  apiCrearCita,
  apiGetAgendaDia,
  apiGetAgendaSemana,
  apiListServicios,
  apiReprogramarCita,
  apiValidarCita,
} from "../../api/agendaApi.js";
import { apiListGroomersActivos } from "../../api/adminApi.js";
import { apiListMascotas } from "../../api/mascotasApi.js";
import DesgloseDuracion from "../common/DesgloseDuracion";
import IndicadorCapacidad from "./IndicadorCapacidad.jsx";
import SelectorSlot from "./SelectorSlot.jsx";
import { calcularDuracion } from "../../utils/calcularDuracion.js";

const HORA_INICIO = 9;
const HORA_FIN = 18;
const INTERVALO_MINUTOS = 30;
const DEFAULT_BLOCK_END = 60;

const timeSlots = (() => {
  const slots = [];
  for (let hora = HORA_INICIO; hora < HORA_FIN; hora += 1) {
    slots.push(`${String(hora).padStart(2, "0")}:00`);
    slots.push(`${String(hora).padStart(2, "0")}:30`);
  }
  return slots;
})();

const stateLabels = {
  pendiente: "Pendiente",
  agendada: "Agendada",
  confirmada: "Confirmada",
  en_progreso: "En progreso",
  completada: "Completada",
  rechazada: "Rechazada",
  cancelada: "Cancelada",
  no_asistio: "No asistio",
};

const stateStyles = {
  pendiente: "linear-gradient(135deg, #f59e0b, #fbbf24)",
  agendada: "linear-gradient(135deg, #0f766e, #14b8a6)",
  confirmada: "linear-gradient(135deg, #2563eb, #60a5fa)",
  en_progreso: "linear-gradient(135deg, #7c3aed, #a78bfa)",
  completada: "linear-gradient(135deg, #16a34a, #4ade80)",
  rechazada: "linear-gradient(135deg, #dc2626, #f87171)",
  cancelada: "linear-gradient(135deg, #6b7280, #9ca3af)",
  no_asistio: "linear-gradient(135deg, #475569, #94a3b8)",
};

const todayIso = () => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const toLocalDate = (value) => new Date(`${value}T00:00:00`);

const toDateTimeLocal = (value) => (value ? value.slice(0, 16) : "");

const formatDateLabel = (value) =>
  toLocalDate(value).toLocaleDateString([], {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });

const addDays = (date, days) => {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
};

const getWeekDates = (value) => {
  const base = toLocalDate(value);
  const monday = addDays(base, -base.getDay() + (base.getDay() === 0 ? -6 : 1));
  return Array.from({ length: 7 }, (_, index) => {
    const date = addDays(monday, index);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  });
};

const timeToMinutes = (time) => {
  const [hours, minutes] = String(time || "00:00").split(":").map(Number);
  return (hours * 60) + (minutes || 0);
};

const overlaps = (startA, endA, startB, endB) => {
  const leftA = timeToMinutes(startA);
  const rightA = timeToMinutes(endA);
  const leftB = timeToMinutes(startB);
  const rightB = timeToMinutes(endB);
  return leftA < rightB && leftB < rightA;
};

const formatMinutes = (minutes) => {
  const total = Math.max(0, Number(minutes) || 0);
  const hours = Math.floor(total / 60);
  const remainder = total % 60;
  if (!hours) return `${remainder} min`;
  if (!remainder) return `${hours} h`;
  return `${hours} h ${remainder} min`;
};

const slotRangeLabel = (time) => {
  const end = timeToMinutes(time) + INTERVALO_MINUTOS;
  const hours = String(Math.floor(end / 60)).padStart(2, "0");
  const minutes = String(end % 60).padStart(2, "0");
  return `${time} - ${hours}:${minutes}`;
};

const normalizeSnapshot = (groomer, dateKey) => {
  const day = groomer?.dias?.[dateKey] || {};
  const total = Number(groomer?.capacidad_simultanea || 1);
  const used = Number(day.citas_usadas ?? day.citas?.length ?? 0);
  const remaining = Number(day.capacidad_restante ?? Math.max(total - used, 0));
  return {
    citas_usadas: used,
    capacidad_restante: remaining,
    capacidad_total: total,
    citas: day.citas || [],
    bloqueos: day.bloqueos || [],
  };
};

const extractErrorMessage = (error, fallback) => {
  const data = error?.response?.data || {};
  const details = data?.details || {};
  const errores = details?.errores || data?.errores || data?.message;
  if (Array.isArray(errores) && errores.length) {
    return errores.join(". ");
  }
  if (typeof errores === "string" && errores.trim()) {
    return errores;
  }
  return fallback;
};

const isCellStartOfEvent = (time, event) => String(event?.hora_inicio) === String(time);

const getCellState = (snapshot, time) => {
  const slotStart = timeToMinutes(time);
  const slotEnd = slotStart + INTERVALO_MINUTOS;

  const bloqueo = snapshot.bloqueos.find((item) =>
    overlaps(item.hora_inicio, item.hora_fin, time, slotRangeEnd(time))
  );
  if (bloqueo && isCellStartOfEvent(time, bloqueo)) {
    return { kind: "block-start", item: bloqueo };
  }
  if (bloqueo) {
    return { kind: "blocked", item: bloqueo };
  }

  const cita = snapshot.citas.find((item) =>
    overlaps(item.hora_inicio, item.hora_fin, time, slotRangeEnd(time))
  );
  if (cita && isCellStartOfEvent(time, cita)) {
    return { kind: "cita-start", item: cita };
  }
  if (cita) {
    return { kind: "occupied", item: cita };
  }

  if (snapshot.capacidad_restante <= 0) {
    return { kind: "full" };
  }

  const withinDay = slotStart >= HORA_INICIO * 60 && slotEnd <= HORA_FIN * 60;
  if (!withinDay) {
    return { kind: "off-hours" };
  }

  return { kind: "free" };
};

const slotRangeEnd = (time) => {
  const total = timeToMinutes(time) + INTERVALO_MINUTOS;
  const hours = String(Math.floor(total / 60)).padStart(2, "0");
  const minutes = String(total % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
};

const SummaryBadge = ({ label, value, tone = "default" }) => (
  <div
    style={{
      borderRadius: 16,
      padding: "12px 14px",
      border: "1px solid rgba(255,255,255,0.08)",
      background: tone === "accent" ? "rgba(20, 184, 166, 0.12)" : "rgba(255,255,255,0.04)",
      minWidth: 160,
    }}
  >
    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)" }}>{label}</div>
    <div style={{ fontWeight: 700, marginTop: 4 }}>{value}</div>
  </div>
);

const DetailRow = ({ label, value }) => (
  <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 14, marginBottom: 8 }}>
    <strong style={{ color: "rgba(255,255,255,0.7)" }}>{label}</strong>
    <span style={{ textAlign: "right" }}>{value || "-"}</span>
  </div>
);

function CitaChip({ cita, onSelect, onDragStart, onDragEnd }) {
  return (
    <button
      type="button"
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onSelect}
      style={{
        display: "block",
        width: "100%",
        border: "none",
        borderRadius: 14,
        padding: "10px 12px",
        textAlign: "left",
        color: "white",
        background: stateStyles[cita.estado] || stateStyles.agendada,
        boxShadow: "0 10px 24px rgba(0,0,0,0.18)",
        cursor: "grab",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
        <strong>{cita.hora_inicio}</strong>
        <span style={{ fontSize: 11, opacity: 0.9 }}>{stateLabels[cita.estado] || cita.estado}</span>
      </div>
      <div style={{ marginTop: 4, fontSize: 13, fontWeight: 600 }}>{cita.mascota || "Mascota"}</div>
      <div style={{ marginTop: 2, fontSize: 12, opacity: 0.9 }}>{cita.servicio || "Servicio"}</div>
    </button>
  );
}

export default function CalendarGrid() {
  const [mode, setMode] = useState("week");
  const [fecha, setFecha] = useState(todayIso());
  const [calendarData, setCalendarData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [catalogsLoaded, setCatalogsLoaded] = useState(false);
  const [servicios, setServicios] = useState([]);
  const [mascotas, setMascotas] = useState([]);
  const [groomersActivos, setGroomersActivos] = useState([]);
  const [selectedCita, setSelectedCita] = useState(null);
  const [editor, setEditor] = useState(null);
  const [bloqueoEditor, setBloqueoEditor] = useState(null);
  const [cancelEditor, setCancelEditor] = useState(null);
  const [rejectedEditor, setRejectedEditor] = useState(null);
  const [draggedCita, setDraggedCita] = useState(null);
  const [dropPreview, setDropPreview] = useState(null);

  useEffect(() => {
    let active = true;
    const loadCatalogs = async () => {
      try {
        const [serviciosData, mascotasData, groomersData] = await Promise.all([
          apiListServicios(),
          apiListMascotas(),
          apiListGroomersActivos(),
        ]);
        if (!active) return;
        setServicios(serviciosData.servicios || []);
        setMascotas(mascotasData.mascotas || []);
        setGroomersActivos(groomersData.groomers || []);
        setCatalogsLoaded(true);
      } catch (loadError) {
        if (active) {
          setError("No se pudieron cargar catalogos para la agenda.");
        }
      }
    };

    loadCatalogs();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const loadCalendar = async () => {
      setLoading(true);
      setError("");
      try {
        const data = mode === "week"
          ? await apiGetAgendaSemana(fecha)
          : await apiGetAgendaDia({ fecha });
        if (!active) return;
        setCalendarData(Array.isArray(data) ? data : []);
      } catch (loadError) {
        if (active) {
          setCalendarData([]);
          setError("No se pudo cargar el calendario.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadCalendar();
    return () => {
      active = false;
    };
  }, [fecha, mode]);

  useEffect(() => {
    const timer = setInterval(() => {
      setSuccess((prev) => prev);
      setError((prev) => prev);
      const refresh = async () => {
        try {
          const data = mode === "week"
            ? await apiGetAgendaSemana(fecha)
            : await apiGetAgendaDia({ fecha });
          setCalendarData(Array.isArray(data) ? data : []);
        } catch {
          // keep the current view if background refresh fails
        }
      };
      refresh();
    }, 60000);

    return () => clearInterval(timer);
  }, [fecha, mode]);

  const weekDates = useMemo(() => getWeekDates(fecha), [fecha]);
  const summaryDates = mode === "week" ? weekDates : [fecha];

  const currentGroomers = calendarData || [];
  const totalCitas = currentGroomers.reduce(
    (acc, groomer) => acc + summaryDates.reduce((sum, dayKey) => sum + ((groomer.dias?.[dayKey]?.citas?.length) || 0), 0),
    0,
  );
  const totalBloqueos = currentGroomers.reduce(
    (acc, groomer) => acc + summaryDates.reduce((sum, dayKey) => sum + ((groomer.dias?.[dayKey]?.bloqueos?.length) || 0), 0),
    0,
  );

  const selectedServicio = servicios.find((item) => String(item.id) === String(editor?.servicio_id));
  const selectedMascota = mascotas.find((item) => String(item.id) === String(editor?.mascota_id));
  const selectedDuration = selectedServicio && selectedMascota
    ? calcularDuracion(
        selectedServicio.duracion_base_minutos,
        selectedMascota.peso_kg,
        selectedMascota.temperamento,
        selectedServicio.factor_tamano_raza,
      ).duracionFinal
    : (selectedServicio?.duracion_base_minutos || 0);

  const openCreateEditor = ({ groomerId, dateKey, time }) => {
    const groomerFallback = groomerId || groomersActivos[0]?.id || "";
    const mascotaFallback = mascotas[0]?.id || "";
    const servicioFallback = servicios[0]?.id || "";
    setSelectedCita(null);
    setBloqueoEditor(null);
    setCancelEditor(null);
    setRejectedEditor(null);
    setEditor({
      mode: "create",
      cita: null,
      groomer_id: String(groomerFallback),
      mascota_id: String(mascotaFallback),
      servicio_id: String(servicioFallback),
      fecha: dateKey,
      fecha_hora_inicio: `${dateKey}T${time}:00`,
      fecha_hora_fin: "",
      duracion_estimada: "",
    });
  };

  const openReprogramEditor = (cita, groomerId, dateKey, time) => {
    setSelectedCita(null);
    setBloqueoEditor(null);
    setCancelEditor(null);
    setRejectedEditor(null);
    setEditor({
      mode: "reprogram",
      cita,
      groomer_id: String(groomerId || cita.groomer_id || ""),
      mascota_id: String(cita.mascota_id || ""),
      servicio_id: String(cita.servicio_id || ""),
      fecha: dateKey,
      fecha_hora_inicio: `${dateKey}T${time}:00`,
      fecha_hora_fin: cita.fecha_hora_fin || "",
      duracion_estimada: cita.duracion_estimada || "",
    });
  };

  const closeEditor = () => {
    setEditor(null);
  };

  const applySlotSelection = ({ hora_inicio, hora_fin, duracion_ajustada }) => {
    setEditor((prev) => ({
      ...prev,
      fecha_hora_inicio: hora_inicio,
      fecha_hora_fin: hora_fin,
      duracion_estimada: duracion_ajustada,
    }));
  };

  const submitEditor = async () => {
    if (!editor) return;
    setError("");
    setSuccess("");

    if (!editor.groomer_id || !editor.servicio_id || !editor.mascota_id || !editor.fecha_hora_inicio) {
      setError("Completa groomer, mascota, servicio y horario antes de continuar.");
      return;
    }

    try {
      if (editor.mode === "create") {
        const validacion = await apiValidarCita({
          groomer_id: Number(editor.groomer_id),
          servicio_id: Number(editor.servicio_id),
          mascota_id: Number(editor.mascota_id),
          fecha_hora_inicio: editor.fecha_hora_inicio,
        });
        if (!validacion.valido) {
          setError((validacion.errores || ["La cita no es valida."]).join(". "));
          return;
        }

        await apiCrearCita({
          mascota_id: Number(editor.mascota_id),
          groomer_id: Number(editor.groomer_id),
          servicio_id: Number(editor.servicio_id),
          fecha_hora_inicio: editor.fecha_hora_inicio,
          fecha_hora_fin: validacion.fecha_hora_fin,
          duracion_estimada: validacion.duracion_ajustada_min,
          notas: editor.notas,
        });
        setSuccess("Cita creada.");
      } else {
        await apiReprogramarCita(editor.cita.id, {
          groomer_id: Number(editor.groomer_id),
          fecha_hora_inicio: editor.fecha_hora_inicio,
        });
        setSuccess("Cita reprogramada.");
      }

      closeEditor();
      const data = mode === "week"
        ? await apiGetAgendaSemana(fecha)
        : await apiGetAgendaDia({ fecha });
      setCalendarData(Array.isArray(data) ? data : []);
    } catch (submitError) {
      setError(extractErrorMessage(submitError, editor.mode === "create" ? "No se pudo crear la cita." : "No se pudo reprogramar la cita."));
    }
  };

  const submitBlock = async () => {
    if (!bloqueoEditor) return;
    setError("");
    setSuccess("");
    try {
      await apiCrearBloqueo(
        {
          groomer_id: bloqueoEditor.groomer_id ? Number(bloqueoEditor.groomer_id) : null,
          fecha_inicio: bloqueoEditor.fecha_inicio,
          fecha_fin: bloqueoEditor.fecha_fin,
          tipo_bloqueo: bloqueoEditor.tipo_bloqueo,
          descripcion: bloqueoEditor.descripcion,
        },
        Boolean(bloqueoEditor.forzar),
      );
      setSuccess("Bloqueo creado.");
      setBloqueoEditor(null);
      const data = mode === "week"
        ? await apiGetAgendaSemana(fecha)
        : await apiGetAgendaDia({ fecha });
      setCalendarData(Array.isArray(data) ? data : []);
    } catch (submitError) {
      setError(extractErrorMessage(submitError, "No se pudo crear el bloqueo."));
    }
  };

  const confirmSelectedCita = async (cita) => {
    try {
      await apiConfirmarCita(cita.id);
      setSuccess("Cita confirmada.");
      setSelectedCita((prev) => (prev ? { ...prev, estado: "confirmada" } : prev));
      const data = mode === "week"
        ? await apiGetAgendaSemana(fecha)
        : await apiGetAgendaDia({ fecha });
      setCalendarData(Array.isArray(data) ? data : []);
    } catch (confirmError) {
      setError(extractErrorMessage(confirmError, "No se pudo confirmar la cita."));
    }
  };

  const rejectSelectedCita = async () => {
    if (!rejectedEditor?.cita) return;
    try {
      await apiActualizarEstadoCita(rejectedEditor.cita.id, {
        estado: "rechazada",
        motivo_rechazo: rejectedEditor.motivo,
      });
      setSuccess("Cita rechazada.");
      setRejectedEditor(null);
      setSelectedCita(null);
      const data = mode === "week"
        ? await apiGetAgendaSemana(fecha)
        : await apiGetAgendaDia({ fecha });
      setCalendarData(Array.isArray(data) ? data : []);
    } catch (rejectError) {
      setError(extractErrorMessage(rejectError, "No se pudo rechazar la cita."));
    }
  };

  const cancelSelectedCita = async () => {
    if (!cancelEditor?.cita) return;
    try {
      await apiCancelarCita(cancelEditor.cita.id, { motivo_cancelacion: cancelEditor.motivo });
      setSuccess("Cita cancelada.");
      setCancelEditor(null);
      setSelectedCita(null);
      const data = mode === "week"
        ? await apiGetAgendaSemana(fecha)
        : await apiGetAgendaDia({ fecha });
      setCalendarData(Array.isArray(data) ? data : []);
    } catch (cancelError) {
      setError(extractErrorMessage(cancelError, "No se pudo cancelar la cita."));
    }
  };

  const openReprogramFromDrop = (cita, groomerId, dateKey, time) => {
    setDraggedCita(null);
    setDropPreview(null);
    openReprogramEditor(cita, groomerId, dateKey, time);
  };

  const weekView = () => (
    <div style={{ display: "grid", gap: 16 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `220px repeat(${weekDates.length}, minmax(160px, 1fr))`,
          gap: 10,
        }}
      >
        <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
          <strong>Groomer</strong>
        </div>
        {weekDates.map((dayKey) => (
          <div key={dayKey} style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <strong>{formatDateLabel(dayKey)}</strong>
          </div>
        ))}

        {currentGroomers.map((groomer) => (
          <Fragment key={groomer.groomer_id}>
            <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <strong>{groomer.groomer_nombre}</strong>
              <div style={{ marginTop: 4, color: "rgba(255,255,255,0.7)", fontSize: 12 }}>
                {groomer.capacidad_simultanea} simultaneas
              </div>
            </div>
            {weekDates.map((dayKey) => {
              const snapshot = normalizeSnapshot(groomer, dayKey);
              const occupancy = snapshot.capacidad_total
                ? Math.min(100, Math.round((snapshot.citas_usadas / snapshot.capacidad_total) * 100))
                : 0;
              return (
                <button
                  key={`${groomer.groomer_id}-${dayKey}`}
                  type="button"
                  onClick={() => {
                    setMode("day");
                    setFecha(dayKey);
                  }}
                  style={{
                    borderRadius: 16,
                    padding: 14,
                    textAlign: "left",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(255,255,255,0.03)",
                    color: "inherit",
                    cursor: "pointer",
                    minHeight: 120,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                    <strong>{snapshot.citas_usadas} citas</strong>
                    <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)" }}>{snapshot.bloqueos.length} bloqueos</span>
                  </div>
                  <div style={{ marginTop: 8, height: 10, borderRadius: 999, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                    <div style={{ width: `${occupancy}%`, height: "100%", background: "linear-gradient(135deg, #14b8a6, #38bdf8)" }} />
                  </div>
                  <div style={{ marginTop: 8, fontSize: 12, color: "rgba(255,255,255,0.72)" }}>
                    {snapshot.capacidad_restante} cupos libres
                  </div>
                </button>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );

  const daySnapshotFor = (groomer) => normalizeSnapshot(groomer, fecha);

  const dayView = () => (
    <div style={{ overflowX: "auto" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `88px repeat(${currentGroomers.length || 1}, minmax(220px, 1fr))`,
          gap: 10,
          minWidth: 340 + (currentGroomers.length * 220),
        }}
      >
        <div style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>Hora</div>
        {currentGroomers.map((groomer) => {
          const snapshot = daySnapshotFor(groomer);
          return (
            <div key={groomer.groomer_id} style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <strong>{groomer.groomer_nombre}</strong>
              <div style={{ marginTop: 4, color: "rgba(255,255,255,0.7)", fontSize: 12 }}>
                {snapshot.capacidad_restante} libres / {snapshot.capacidad_total} total
              </div>
            </div>
          );
        })}

        {timeSlots.map((time) => (
          <Fragment key={time}>
            <div style={{ padding: "12px 4px", color: "rgba(255,255,255,0.72)", fontSize: 12 }}>
              {time}
            </div>
            {currentGroomers.map((groomer) => {
              const snapshot = daySnapshotFor(groomer);
              const cell = getCellState(snapshot, time);
              const targetKey = `${groomer.groomer_id}-${fecha}-${time}`;

              const cellStyle = {
                minHeight: 74,
                borderRadius: 16,
                padding: 10,
                border: "1px solid rgba(255,255,255,0.08)",
                display: "flex",
                alignItems: "stretch",
                justifyContent: "stretch",
                color: "inherit",
                background:
                  cell.kind === "blocked" || cell.kind === "block-start"
                    ? "repeating-linear-gradient(135deg, rgba(107,114,128,0.40), rgba(107,114,128,0.40) 8px, rgba(148,163,184,0.20) 8px, rgba(148,163,184,0.20) 16px)"
                    : cell.kind === "occupied" || cell.kind === "cita-start"
                      ? "rgba(15, 23, 42, 0.9)"
                      : cell.kind === "full"
                        ? "rgba(249, 115, 22, 0.16)"
                        : cell.kind === "off-hours"
                          ? "rgba(148, 163, 184, 0.08)"
                          : "rgba(20, 184, 166, 0.12)",
                cursor: cell.kind === "free" ? "pointer" : "default",
                boxShadow: dropPreview?.key === targetKey ? "0 0 0 2px rgba(20,184,166,0.9) inset" : "none",
              };

              const handleDrop = (event) => {
                event.preventDefault();
                if (!draggedCita || cell.kind !== "free") return;
                openReprogramFromDrop(draggedCita, groomer.groomer_id, fecha, time);
              };

              const handleClick = () => {
                if (cell.kind === "free") {
                  openCreateEditor({ groomerId: groomer.groomer_id, dateKey: fecha, time });
                  return;
                }
                if (cell.item && (cell.kind === "cita-start" || cell.kind === "occupied")) {
                  setSelectedCita({ ...cell.item, groomer_id: groomer.groomer_id, fecha });
                }
              };

              return (
                <div
                  key={targetKey}
                  onDragOver={(event) => {
                    if (draggedCita && cell.kind === "free") {
                      event.preventDefault();
                      setDropPreview({ key: targetKey });
                    }
                  }}
                  onDragLeave={() => setDropPreview((prev) => (prev?.key === targetKey ? null : prev))}
                  onDrop={handleDrop}
                  style={cellStyle}
                >
                  {cell.kind === "cita-start" ? (
                    <CitaChip
                      cita={cell.item}
                      onSelect={handleClick}
                      onDragStart={() => setDraggedCita(cell.item)}
                      onDragEnd={() => {
                        setDraggedCita(null);
                        setDropPreview(null);
                      }}
                    />
                  ) : cell.kind === "occupied" ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", fontSize: 12, color: "rgba(255,255,255,0.72)" }}>
                      Ocupado
                    </div>
                  ) : cell.kind === "block-start" ? (
                    <div style={{ width: "100%", color: "rgba(255,255,255,0.9)", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                      <strong>{cell.item.tipo}</strong>
                      <span style={{ fontSize: 12 }}>{cell.item.hora_inicio} - {cell.item.hora_fin}</span>
                    </div>
                  ) : cell.kind === "blocked" ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", fontSize: 12, color: "rgba(255,255,255,0.72)" }}>
                      Bloqueado
                    </div>
                  ) : cell.kind === "full" ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", fontSize: 12, color: "rgba(251,146,60,0.95)" }}>
                      Capacidad llena
                    </div>
                  ) : cell.kind === "off-hours" ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "100%", fontSize: 12, color: "rgba(255,255,255,0.45)" }}>
                      Fuera de horario
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleClick}
                      style={{
                        width: "100%",
                        border: "none",
                        borderRadius: 14,
                        background: "transparent",
                        color: "inherit",
                        textAlign: "left",
                        padding: 0,
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 700 }}>Disponible</div>
                      <div style={{ fontSize: 11, color: "rgba(255,255,255,0.72)", marginTop: 4 }}>Crear o soltar cita</div>
                    </button>
                  )}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );

  const detailDrawer = () => {
    if (!selectedCita) return null;
    return (
      <aside
        style={{
          position: "fixed",
          right: 20,
          top: 100,
          width: 360,
          maxWidth: "calc(100vw - 40px)",
          zIndex: 30,
          borderRadius: 20,
          border: "1px solid rgba(255,255,255,0.12)",
          background: "rgba(8, 15, 24, 0.96)",
          boxShadow: "0 24px 60px rgba(0,0,0,0.4)",
          padding: 18,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
          <div>
            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.08, color: "rgba(255,255,255,0.55)" }}>Detalle de cita</div>
            <h4 style={{ margin: "6px 0 0" }}>{selectedCita.mascota || "Mascota"}</h4>
          </div>
          <button type="button" className="link-button" onClick={() => setSelectedCita(null)}>Cerrar</button>
        </div>

        <div style={{ marginTop: 14 }}>
          <DetailRow label="Horario" value={`${selectedCita.hora_inicio} - ${selectedCita.hora_fin}`} />
          <DetailRow label="Servicio" value={selectedCita.servicio} />
          <DetailRow label="Cliente" value={selectedCita.cliente} />
          <DetailRow label="Estado" value={stateLabels[selectedCita.estado] || selectedCita.estado} />
          <DetailRow label="Groomer" value={selectedCita.groomer_nombre || selectedCita.groomer?.nombre || selectedCita.groomer_id} />
        </div>

        <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
          <button type="button" className="primary-button" onClick={() => confirmSelectedCita(selectedCita)}>
            Confirmar
          </button>
          <button type="button" className="secondary-button" onClick={() => setRejectedEditor({ cita: selectedCita, motivo: "" })}>
            Rechazar
          </button>
          <button type="button" className="secondary-button" onClick={() => setCancelEditor({ cita: selectedCita, motivo: "" })}>
            Cancelar
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => openReprogramEditor(selectedCita, selectedCita.groomer_id, selectedCita.fecha || fecha, selectedCita.hora_inicio)}
          >
            Reprogramar
          </button>
        </div>
      </aside>
    );
  };

  return (
    <section className="agenda-card agenda-wide">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "start" }}>
        <div>
          <p className="calendar-kicker">Calendario maestro</p>
          <h3 style={{ marginBottom: 8 }}>Agenda y reservas</h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <SummaryBadge label="Citas visibles" value={totalCitas} tone="accent" />
            <SummaryBadge label="Bloqueos visibles" value={totalBloqueos} />
            <SummaryBadge label="Groomers activos" value={currentGroomers.length} />
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <button type="button" className={mode === "week" ? "primary-button" : "secondary-button"} onClick={() => setMode("week")}>Semana</button>
          <button type="button" className={mode === "day" ? "primary-button" : "secondary-button"} onClick={() => setMode("day")}>Día</button>
          <input type="date" value={fecha} onChange={(event) => setFecha(event.target.value)} />
          <button type="button" className="secondary-button" onClick={() => openCreateEditor({ groomerId: currentGroomers[0]?.groomer_id || groomersActivos[0]?.id, dateKey: fecha, time: "09:00" })}>
            Nueva cita
          </button>
          <button type="button" className="secondary-button" onClick={() => setBloqueoEditor({
            groomer_id: String(currentGroomers[0]?.groomer_id || ""),
            fecha_inicio: `${fecha}T09:00`,
            fecha_fin: `${fecha}T10:00`,
            tipo_bloqueo: "operativo",
            descripcion: "",
            forzar: false,
          })}>
            Nuevo bloqueo
          </button>
        </div>
      </div>

      {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}
      {success ? <div className="alert alert-success" style={{ marginTop: 16 }}>{success}</div> : null}
      {loading ? <div className="admin-empty" style={{ marginTop: 18 }}>Cargando calendario...</div> : null}
      {!loading && catalogsLoaded && currentGroomers.length === 0 ? (
        <div className="admin-empty" style={{ marginTop: 18 }}>No hay datos para la fecha seleccionada.</div>
      ) : null}

      {!loading && currentGroomers.length > 0 ? (
        <div style={{ marginTop: 20 }}>
          {mode === "week" ? weekView() : dayView()}
        </div>
      ) : null}

      {editor ? (
        <div className="modal-backdrop" style={{ zIndex: 40 }}>
          <div className="modal-card" style={{ width: "min(1080px, calc(100vw - 24px))", maxHeight: "92vh", overflowY: "auto" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">{editor.mode === "create" ? "Nueva cita" : "Reprogramar cita"}</p>
                <h4 style={{ margin: 0 }}>{editor.fecha_hora_inicio.slice(0, 10)} {editor.fecha_hora_inicio.slice(11, 16)}</h4>
              </div>
              <button type="button" className="ghost-button" onClick={closeEditor}>Cerrar</button>
            </div>

            <div className="calendar-form-grid" style={{ display: "grid", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                <label>
                  Groomer
                  <select value={editor.groomer_id} onChange={(event) => setEditor((prev) => ({ ...prev, groomer_id: event.target.value }))}>
                    <option value="">Selecciona</option>
                    {groomersActivos.map((groomer) => (
                      <option key={groomer.id} value={groomer.id}>{groomer.nombre} {groomer.apellido || ""}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Mascota
                  <select value={editor.mascota_id} onChange={(event) => setEditor((prev) => ({ ...prev, mascota_id: event.target.value }))}>
                    <option value="">Selecciona</option>
                    {mascotas.map((mascota) => (
                      <option key={mascota.id} value={mascota.id}>{mascota.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Servicio
                  <select value={editor.servicio_id} onChange={(event) => setEditor((prev) => ({ ...prev, servicio_id: event.target.value }))}>
                    <option value="">Selecciona</option>
                    {servicios.map((servicio) => (
                      <option key={servicio.id} value={servicio.id}>{servicio.nombre}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Fecha
                  <input type="date" value={editor.fecha} onChange={(event) => setEditor((prev) => ({ ...prev, fecha: event.target.value, fecha_hora_inicio: `${event.target.value}T${prev.fecha_hora_inicio.slice(11, 16)}:00` }))} />
                </label>
              </div>

              <div>
                <DesgloseDuracion servicio={selectedServicio} mascota={selectedMascota} />
              </div>

              {editor.groomer_id && editor.fecha && selectedDuration ? (
                <IndicadorCapacidad
                  groomer_id={Number(editor.groomer_id)}
                  fecha={editor.fecha}
                  duracion_min={selectedDuration}
                />
              ) : null}

              {editor.groomer_id && editor.fecha && editor.servicio_id && editor.mascota_id ? (
                <SelectorSlot
                  groomer_id={Number(editor.groomer_id)}
                  fecha={editor.fecha}
                  duracion_min={selectedDuration}
                  servicio_id={Number(editor.servicio_id)}
                  mascota_id={Number(editor.mascota_id)}
                  onSlotSelect={applySlotSelection}
                />
              ) : (
                <div className="admin-empty">Selecciona groomer, mascota y servicio para ver los slots disponibles.</div>
              )}

              <div style={{ padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)" }}>
                <strong>Horario seleccionado</strong>
                <div style={{ marginTop: 6, color: "rgba(255,255,255,0.75)" }}>
                  {editor.fecha_hora_inicio ? editor.fecha_hora_inicio.replace("T", " ").slice(0, 16) : "Sin horario"}
                </div>
                <div style={{ marginTop: 4, color: "rgba(255,255,255,0.6)", fontSize: 12 }}>
                  {editor.fecha_hora_fin ? `Fin estimado: ${editor.fecha_hora_fin.replace("T", " ").slice(0, 16)}` : "Selecciona un slot para completar la cita."}
                </div>
              </div>
            </div>

            <div className="calendar-actions" style={{ marginTop: 18, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button type="button" className="primary-button" onClick={submitEditor}>
                {editor.mode === "create" ? "Crear cita" : "Confirmar reprogramación"}
              </button>
              <button type="button" className="secondary-button" onClick={closeEditor}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {bloqueoEditor ? (
        <div className="modal-backdrop" style={{ zIndex: 41 }}>
          <div className="modal-card" style={{ width: "min(720px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Nuevo bloqueo</p>
                <h4 style={{ margin: 0 }}>Reservar un tramo de agenda</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setBloqueoEditor(null)}>Cerrar</button>
            </div>
            <div style={{ display: "grid", gap: 12 }}>
              <label>
                Groomer (opcional)
                <select value={bloqueoEditor.groomer_id} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, groomer_id: event.target.value }))}>
                  <option value="">Global (todos)</option>
                  {groomersActivos.map((groomer) => (
                    <option key={groomer.id} value={groomer.id}>{groomer.nombre} {groomer.apellido || ""}</option>
                  ))}
                </select>
              </label>
              <label>
                Inicio
                <input type="datetime-local" value={toDateTimeLocal(bloqueoEditor.fecha_inicio)} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, fecha_inicio: event.target.value }))} />
              </label>
              <label>
                Fin
                <input type="datetime-local" value={toDateTimeLocal(bloqueoEditor.fecha_fin)} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, fecha_fin: event.target.value }))} />
              </label>
              <label>
                Tipo
                <input value={bloqueoEditor.tipo_bloqueo} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, tipo_bloqueo: event.target.value }))} />
              </label>
              <label>
                Descripcion
                <textarea value={bloqueoEditor.descripcion} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, descripcion: event.target.value }))} rows={3} />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={Boolean(bloqueoEditor.forzar)} onChange={(event) => setBloqueoEditor((prev) => ({ ...prev, forzar: event.target.checked }))} />
                Forzar aunque existan conflictos
              </label>
            </div>
            <div className="calendar-actions" style={{ marginTop: 18, display: "flex", gap: 12 }}>
              <button type="button" className="primary-button" onClick={submitBlock}>Guardar bloqueo</button>
              <button type="button" className="secondary-button" onClick={() => setBloqueoEditor(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      ) : null}

      {cancelEditor ? (
        <div className="modal-backdrop" style={{ zIndex: 42 }}>
          <div className="modal-card" style={{ width: "min(620px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Cancelar cita</p>
                <h4 style={{ margin: 0 }}>{cancelEditor.cita?.mascota || "Mascota"}</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setCancelEditor(null)}>Cerrar</button>
            </div>
            <label>
              Motivo
              <textarea rows={4} value={cancelEditor.motivo} onChange={(event) => setCancelEditor((prev) => ({ ...prev, motivo: event.target.value }))} />
            </label>
            <div className="calendar-actions" style={{ marginTop: 18, display: "flex", gap: 12 }}>
              <button type="button" className="primary-button" onClick={cancelSelectedCita}>Confirmar cancelación</button>
              <button type="button" className="secondary-button" onClick={() => setCancelEditor(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      ) : null}

      {rejectedEditor ? (
        <div className="modal-backdrop" style={{ zIndex: 43 }}>
          <div className="modal-card" style={{ width: "min(620px, calc(100vw - 24px))" }}>
            <div className="modal-header">
              <div>
                <p className="calendar-kicker">Rechazar solicitud</p>
                <h4 style={{ margin: 0 }}>{rejectedEditor.cita?.mascota || "Mascota"}</h4>
              </div>
              <button type="button" className="ghost-button" onClick={() => setRejectedEditor(null)}>Cerrar</button>
            </div>
            <label>
              Motivo del rechazo
              <textarea rows={4} value={rejectedEditor.motivo} onChange={(event) => setRejectedEditor((prev) => ({ ...prev, motivo: event.target.value }))} />
            </label>
            <div className="calendar-actions" style={{ marginTop: 18, display: "flex", gap: 12 }}>
              <button type="button" className="primary-button" onClick={rejectSelectedCita}>Confirmar rechazo</button>
              <button type="button" className="secondary-button" onClick={() => setRejectedEditor(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      ) : null}

      {detailDrawer()}
    </section>
  );
}