import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiCrearFicha, apiGetAgendaPersonal, apiGetAgendaSemanaPersonal, apiGetAgendaStats } from "../api/groomerApi.js";
import { useAuthContext } from "../context/AuthContext.jsx";

const WEEKDAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

function statusLabel(estadoFicha) {
  if (estadoFicha === "en_curso") return "🔄 En curso";
  if (estadoFicha === "cerrada") return "✓ Completada";
  return "Por iniciar";
}

function statusClass(estadoFicha) {
  if (estadoFicha === "en_curso") return "pill pill-warning";
  if (estadoFicha === "cerrada") return "pill pill-success";
  return "pill";
}

function shiftDate(fecha, days) {
  const next = new Date(`${fecha}T00:00:00`);
  next.setDate(next.getDate() + days);
  return next.toISOString().slice(0, 10);
}

function checklistProgress(ficha) {
  if (!ficha || !ficha.items_total) return null;
  const completos = Math.max(ficha.items_total - ficha.items_pendientes, 0);
  const porcentaje = Math.round((completos / ficha.items_total) * 100);
  return { completos, porcentaje };
}

export default function AgendaPersonal() {
  const navigate = useNavigate();
  const { usuario } = useAuthContext();
  const [modo, setModo] = useState("dia");
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [citas, setCitas] = useState([]);
  const [semana, setSemana] = useState(null);
  const [stats, setStats] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [accionCitaId, setAccionCitaId] = useState(null);

  useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      setError("");
      try {
        const agendaPromise = modo === "dia" ? apiGetAgendaPersonal(fecha) : apiGetAgendaSemanaPersonal({ fecha });
        const semanaPromise = apiGetAgendaSemanaPersonal({ fecha });
        const [agendaData, statsData, semanaData] = await Promise.all([agendaPromise, apiGetAgendaStats(), semanaPromise]);
        setCitas(modo === "dia" ? (Array.isArray(agendaData) ? agendaData : agendaData?.citas || []) : []);
        setSemana(semanaData || (modo === "semana" ? agendaData : null));
        setStats(statsData || null);
      } catch (err) {
        setError("No se pudo cargar la agenda personal.");
      } finally {
        setCargando(false);
      }
    };

    cargar();
  }, [fecha, modo]);

  const diasSemana = useMemo(() => {
    if (!semana?.dias) return [];
    return Object.entries(semana.dias).sort(([a], [b]) => a.localeCompare(b));
  }, [semana]);

  const citaDiaActual = semana?.dias?.[fecha] || null;

  const todasCompletadas = citas.length > 0 && citas.every((item) => item.ficha?.estado === "cerrada");

  const handleCrearFicha = async (cita) => {
    setError("");
    setAccionCitaId(cita.id);
    try {
      const data = await apiCrearFicha({ cita_id: cita.id });
      const fichaId = data?.ficha?.id;
      if (fichaId) {
        navigate(`/fichas/${fichaId}`);
      } else {
        navigate(`/groomer/ficha/${cita.id}`);
      }
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo iniciar el servicio.");
    } finally {
      setAccionCitaId(null);
    }
  };

  const renderTarjeta = (cita) => {
    const progreso = checklistProgress(cita.ficha);
    const puedeIniciar = cita.ficha?.estado === "sin_iniciar" && ["agendada", "confirmada"].includes(cita.estado);

    return (
      <article key={cita.id} className="groomer-card agenda-groomer-card">
        <div className="agenda-groomer-card__top">
          <div>
            <div className="agenda-hour-range">{cita.hora_inicio || "--:--"} — {cita.hora_fin || "--:--"}</div>
            <div className={statusClass(cita.ficha?.estado)}>{statusLabel(cita.ficha?.estado)}</div>
          </div>
          {cita.cliente_notificado ? <div className="pill pill-success">Cliente notificado ✓</div> : null}
        </div>

        <div className="agenda-groomer-card__main">
          <div>🐕 {cita.mascota?.nombre || "Mascota"} · {cita.mascota?.raza || "Sin raza"} · {cita.mascota?.peso_kg ?? "-"}kg</div>
          <div>✂️ {cita.servicio?.nombre || "Servicio"} · {cita.duracion_estimada || cita.servicio?.duracion_base_minutos || 0} min</div>
          {cita.mascota?.tiene_alergias ? <div className="alert alert-error">⚠ ALERGIA: {cita.mascota.alergias_conocidas}</div> : null}

          <div className="agenda-checklist-block">
            <div className="agenda-checklist-head">
              <span>Checklist: {Math.max((cita.ficha?.items_total || 0) - (cita.ficha?.items_pendientes || 0), 0)}/{cita.ficha?.items_total || 0} ✓</span>
              {cita.ficha?.estado === "sin_iniciar" ? <span className="agenda-muted">Servicio no iniciado</span> : null}
            </div>
            {progreso ? (
              <>
                <div className="agenda-progress-bar">
                  <div style={{ width: `${progreso.porcentaje}%` }} />
                </div>
                <div className="agenda-muted">{progreso.completos}/{cita.ficha.items_total} completados</div>
              </>
            ) : (
              <div className="agenda-muted">Sin checklist asociado.</div>
            )}
          </div>
        </div>

        <div className="agenda-groomer-card__actions">
          <button
            type="button"
            className="link-button"
            onClick={() => navigate(cita.ficha?.id ? `/fichas/${cita.ficha.id}` : `/fichas/nueva?cita_id=${cita.id}&fecha=${fecha}`)}
          >
            Ver ficha →
          </button>
          {puedeIniciar ? (
            <button
              type="button"
              className="ghost-button"
              disabled={accionCitaId === cita.id}
              onClick={() => handleCrearFicha(cita)}
            >
              {accionCitaId === cita.id ? "Iniciando..." : "Iniciar servicio"}
            </button>
          ) : null}
        </div>
      </article>
    );
  };

  return (
    <div className="agenda-personal-page">
      <div className="agenda-personal-shell">
        <header className="agenda-personal-header">
          <div>
            <p className="agenda-personal-kicker">Agenda personal del groomer</p>
            <h1>Buenos días, {usuario?.nombre_completo || usuario?.email || "groomer"}</h1>
            <p className="agenda-personal-subtitle">Solo ves tus propias citas, con checklist, estado y notificaciones del cliente.</p>
          </div>
          {stats ? (
            <div className="agenda-stats-row">
              <div className="agenda-stat-card"><span>Hoy</span><strong>{stats.citas_hoy}</strong></div>
              <div className="agenda-stat-card"><span>Completadas</span><strong>{stats.completadas_hoy}</strong></div>
              <div className="agenda-stat-card"><span>Semana</span><strong>{stats.citas_semana}</strong></div>
            </div>
          ) : null}
        </header>

        <section className="agenda-personal-toolbar">
          <div className="agenda-mode-toggle">
            <button type="button" className={modo === "dia" ? "ghost-button active" : "ghost-button"} onClick={() => setModo("dia")}>
              📅 Día
            </button>
            <button type="button" className={modo === "semana" ? "ghost-button active" : "ghost-button"} onClick={() => setModo("semana")}>
              📆 Semana
            </button>
          </div>
          <div className="agenda-date-nav">
            <button type="button" className="ghost-button" onClick={() => setFecha((current) => shiftDate(current, modo === "dia" ? -1 : -7))}>
              ← Anterior
            </button>
            <button type="button" className="ghost-button" onClick={() => setFecha(new Date().toISOString().split("T")[0])}>
              Hoy
            </button>
            <input type="date" value={fecha} onChange={(event) => setFecha(event.target.value)} className="agenda-date-input" />
            <button type="button" className="ghost-button" onClick={() => setFecha((current) => shiftDate(current, modo === "dia" ? 1 : 7))}>
              Siguiente →
            </button>
          </div>
        </section>

        {error ? <div className="alert alert-error">{error}</div> : null}
        {todasCompletadas ? <div className="alert alert-success">✅ ¡Todas las citas del día completadas!</div> : null}
        {cargando ? <div className="admin-empty">Cargando agenda...</div> : null}

        {!cargando && modo === "dia" ? (
          <section className="agenda-day-list">
            {citas.length ? citas.map(renderTarjeta) : (
              <div className="admin-empty">
                🎉 No tienes citas para este día. ¡Descansa!
                {citaDiaActual && !citaDiaActual.trabaja ? <div style={{ marginTop: 8 }}>📅 No tienes jornada este día.</div> : null}
              </div>
            )}
          </section>
        ) : null}

        {!cargando && modo === "semana" ? (
          <>
            <section className="agenda-week-grid">
              {diasSemana.map(([dia, info]) => {
                const conteo = info.citas.length;
                const capacidad = info.capacidad || 0;
                const porcentaje = capacidad ? Math.min(Math.round((conteo / capacidad) * 100), 100) : 0;
                const dayIndex = new Date(`${dia}T00:00:00`).getDay();
                const label = WEEKDAY_LABELS[dayIndex === 0 ? 6 : dayIndex - 1];
                return (
                  <article key={dia} className="agenda-week-day" onClick={() => {
                    setModo("dia");
                    setFecha(dia);
                  }}>
                    <div className="agenda-week-day__head">
                      <strong>{label}</strong>
                      <span className="pill">{conteo}/{capacidad || "-"}</span>
                    </div>
                    <div className="agenda-muted">{info.fecha_label}</div>
                    <div className="agenda-progress-bar agenda-progress-bar--small">
                      <div style={{ width: `${porcentaje}%` }} />
                    </div>
                    <div className="agenda-week-list">
                      {info.citas.slice(0, 3).map((cita) => (
                        <div key={cita.id} className="agenda-week-item">
                          <span>{cita.hora_inicio}</span>
                          <span>{cita.mascota?.nombre || "Mascota"} · {cita.servicio?.nombre || "Servicio"}</span>
                        </div>
                      ))}
                      {!info.citas.length ? <div className="agenda-muted">Sin citas</div> : null}
                    </div>
                  </article>
                );
              })}
            </section>

            {semana?.resumen ? (
              <div className="agenda-week-summary">
                <span>Total: {semana.resumen.total_citas}</span>
                <span>Completadas: {semana.resumen.completadas}</span>
                <span>En curso: {semana.resumen.en_curso}</span>
                <span>Pendientes: {semana.resumen.pendientes}</span>
              </div>
            ) : null}

            {!diasSemana.length ? <div className="admin-empty">No tienes citas en la semana seleccionada.</div> : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
