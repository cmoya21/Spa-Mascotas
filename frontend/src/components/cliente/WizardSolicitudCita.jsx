import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiGetFechasDisponibles, apiGetSlotsDisponibles, apiListServicios } from "../../api/agendaApi.js";
import { apiListGroomersActivos } from "../../api/adminApi.js";
import { apiGetMisMascotas, apiSolicitarCitaCliente } from "../../api/clienteApi.js";
import { calcularDuracion } from "../../utils/calcularDuracion.js";
import DesgloseDuracion from "../common/DesgloseDuracion.jsx";
import Button from "../shared/Button";

const FASES = ["Mascota", "Servicio", "Agenda", "Confirmar"];
const FRANJAS = [
  { key: "manana", label: "🌅 Mañana (9-12)", rango: [9, 12] },
  { key: "tarde", label: "☀️ Tarde (12-17)", rango: [12, 17] },
  { key: "cualquiera", label: "🕐 Cualquier hora", rango: [0, 24] },
];

const today = new Date();
const hoyIso = today.toISOString().slice(0, 10);
const maxIso = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

const formatFechaBonita = (fechaTexto) =>
  new Intl.DateTimeFormat("es-BO", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${fechaTexto}T00:00:00`));

const franjaLabel = (franja) => FRANJAS.find((item) => item.key === franja)?.label || "🕐 Cualquier hora";

const isSlotInFranja = (hora, franja) => {
  const [hour] = hora.split(":").map(Number);
  const def = FRANJAS.find((item) => item.key === franja) || FRANJAS[2];
  return hour >= def.rango[0] && hour < def.rango[1];
};

const normalizeError = (err) => {
  const data = err?.response?.data;
  const details = data?.details?.errores || data?.details || data?.errores || data?.message;
  if (Array.isArray(details)) return details.join(". ");
  if (typeof details === "string") return details;
  if (details && typeof details === "object") return Object.values(details).flat().join(". ");
  return "No se pudo completar la solicitud.";
};

const emptyAvailability = () => ({ manana: false, tarde: false, cualquiera: false });

export default function WizardSolicitudCita({ mascotas: mascotasProp = [], onCreated, onRequestRegistrarMascota }) {
  const navigate = useNavigate();
  const [paso, setPaso] = useState(1);
  const [mascotas, setMascotas] = useState(mascotasProp || []);
  const [servicios, setServicios] = useState([]);
  const [groomers, setGroomers] = useState([]);
  const [mascotaSel, setMascotaSel] = useState(null);
  const [servicioSel, setServicioSel] = useState(null);
  const [groomerSel, setGroomerSel] = useState(null);
  const [fechaSel, setFechaSel] = useState("");
  const [franjaSel, setFranjaSel] = useState("cualquiera");
  const [notas, setNotas] = useState("");
  const [duracionAjustada, setDuracionAjustada] = useState(null);
  const [fechasDisponibles, setFechasDisponibles] = useState([]);
  const [franjasDisponibles, setFranjasDisponibles] = useState(emptyAvailability());
  const [cargandoFechas, setCargandoFechas] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  useEffect(() => {
    setMascotas(mascotasProp || []);
  }, [mascotasProp]);

  useEffect(() => {
    apiGetMisMascotas()
      .then((data) => setMascotas(data.mascotas || []))
      .catch(() => setError("No se pudieron cargar tus mascotas."));

    apiListServicios()
      .then((data) => setServicios(data.servicios || []))
      .catch(() => setError("No se pudieron cargar los servicios."));

    apiListGroomersActivos()
      .then((data) => setGroomers(data.groomers || []))
      .catch(() => setError("No se pudieron cargar los groomers activos."));
  }, []);

  useEffect(() => {
    if (!mascotaSel || !servicioSel) {
      setFechasDisponibles([]);
      setDuracionAjustada(null);
      setFechaSel("");
      return;
    }

    const duracion = calcularDuracion(
      servicioSel.duracion_base_minutos,
      mascotaSel.peso_kg,
      mascotaSel.temperamento,
      servicioSel.factor_tamano_raza
    ).duracionFinal;
    setDuracionAjustada(duracion);

    setCargandoFechas(true);
    apiGetFechasDisponibles({
      servicio_id: servicioSel.id,
      mascota_id: mascotaSel.id,
      groomer_id: groomerSel?.id || undefined,
    })
      .then((data) => {
        setFechasDisponibles(data.fechas_disponibles || []);
        setDuracionAjustada(data.duracion_ajustada || duracion);
      })
      .catch((err) => setError(normalizeError(err)))
      .finally(() => setCargandoFechas(false));
  }, [mascotaSel, servicioSel, groomerSel]);

  useEffect(() => {
    if (!fechaSel || !duracionAjustada) {
      setFranjasDisponibles(emptyAvailability());
      return;
    }

    const candidates = groomerSel ? [groomerSel] : groomers;
    if (!candidates.length) {
      setFranjasDisponibles(emptyAvailability());
      return;
    }

    let cancelled = false;
    const load = async () => {
      const results = await Promise.all(
        candidates.map(async (groomer) => {
          const data = await apiGetSlotsDisponibles({
            groomer_id: groomer.id,
            fecha: fechaSel,
            duracion_min: duracionAjustada,
          });
          return data.slots || [];
        })
      );
      if (cancelled) return;
      const allSlots = results.flat();
      setFranjasDisponibles({
        manana: allSlots.some((slot) => slot.disponible && isSlotInFranja(slot.hora_inicio, "manana")),
        tarde: allSlots.some((slot) => slot.disponible && isSlotInFranja(slot.hora_inicio, "tarde")),
        cualquiera: allSlots.some((slot) => slot.disponible),
      });
    };

    load().catch(() => {
      if (!cancelled) setFranjasDisponibles(emptyAvailability());
    });
    return () => {
      cancelled = true;
    };
  }, [fechaSel, duracionAjustada, groomerSel, groomers]);

  const mascotaList = mascotas || [];
  const mascotasCount = mascotaList.length;
  const servicioDuracion = useMemo(() => duracionAjustada || servicioSel?.duracion_base_minutos || null, [duracionAjustada, servicioSel]);

  const currentGroomerLabel = groomerSel ? `${groomerSel.nombre}${groomerSel.especialidad ? ` · ${groomerSel.especialidad}` : ""}` : "Sin preferencia";
  const fechaLabel = fechaSel ? formatFechaBonita(fechaSel) : "Sin fecha seleccionada";

  const selectMascota = (mascota) => {
    setMascotaSel(mascota);
    setPaso((current) => Math.max(current, 2));
    setError("");
  };

  const selectServicio = (servicio) => {
    setServicioSel(servicio);
    setPaso((current) => Math.max(current, 3));
    setError("");
  };

  const avanzar = () => {
    if (paso === 1 && !mascotaSel) return setError("Selecciona una mascota.");
    if (paso === 2 && !servicioSel) return setError("Selecciona un servicio.");
    if (paso === 3 && (!fechaSel || !franjasDisponibles[franjaSel])) return setError("Selecciona una fecha y franja disponibles.");
    setError("");
    setPaso((current) => Math.min(current + 1, 4));
  };

  const retroceder = () => setPaso((current) => Math.max(current - 1, 1));

  const guardar = async () => {
    setError("");
    if (!mascotaSel || !servicioSel || !fechaSel) {
      setError("Completa mascota, servicio y fecha.");
      return;
    }
    if (!franjasDisponibles[franjaSel]) {
      setError("No hay disponibilidad en esa franja para la fecha seleccionada.");
      return;
    }

    setEnviando(true);
    try {
      const response = await apiSolicitarCitaCliente({
        mascota_id: mascotaSel.id,
        servicio_id: servicioSel.id,
        groomer_id: groomerSel?.id || undefined,
        fecha_preferida: fechaSel,
        franja: franjaSel,
        notas,
      });
      setToast(response.mensaje || "¡Solicitud enviada! Te notificaremos pronto.");
      onCreated?.();
      setTimeout(() => navigate("/cliente/vista", { replace: true }), 900);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setEnviando(false);
    }
  };

  const renderPaso = () => {
    if (paso === 1) {
      if (!mascotaList.length) {
        return (
          <div style={{ display: "grid", gap: 12 }}>
            <div className="admin-empty">No tienes mascotas registradas.</div>
            <Button type="button" onClick={() => onRequestRegistrarMascota?.()}>
              Registrar mi primera mascota
            </Button>
          </div>
        );
      }

      return (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gap: 8 }}>
            <h3 style={{ margin: 0 }}>Selecciona tu mascota</h3>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.68)" }}>Usaremos su peso y temperamento para calcular la duración ajustada.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            {mascotaList.map((mascota) => {
              const selected = String(mascotaSel?.id) === String(mascota.id);
              return (
                <button
                  key={mascota.id}
                  type="button"
                  onClick={() => selectMascota(mascota)}
                  style={{
                    textAlign: "left",
                    borderRadius: 20,
                    padding: 14,
                    border: selected ? "1px solid #61A36A" : "1px solid rgba(255,255,255,0.08)",
                    background: selected ? "rgba(97,163,106,0.16)" : "rgba(255,255,255,0.04)",
                    color: "inherit",
                    display: "grid",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <div style={{ width: 52, height: 52, borderRadius: 18, overflow: "hidden", background: "rgba(255,255,255,0.08)", display: "grid", placeItems: "center", flexShrink: 0 }}>
                      {mascota.foto_url ? (
                        <img src={mascota.foto_url} alt={mascota.nombre} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      ) : (
                        <span style={{ fontSize: 22 }}>🐾</span>
                      )}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700 }}>{mascota.nombre}</div>
                      <div style={{ color: "rgba(255,255,255,0.72)" }}>{mascota.raza || mascota.especie || "Sin raza"}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", color: "rgba(255,255,255,0.8)" }}>
                    {mascota.tamano ? <span className="pill">{mascota.tamano}</span> : null}
                    {mascota.temperamento ? <span className="pill">{mascota.temperamento}</span> : null}
                    {mascota.alergias_conocidas ? <span className="pill">⚠ Alergias</span> : null}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    if (paso === 2) {
      return (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "grid", gap: 8 }}>
            <h3 style={{ margin: 0 }}>Selecciona el servicio</h3>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.68)" }}>La duración se ajusta según la mascota seleccionada.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 12 }}>
            {servicios.map((servicio) => {
              const selected = String(servicioSel?.id) === String(servicio.id);
              return (
                <button
                  key={servicio.id}
                  type="button"
                  onClick={() => selectServicio(servicio)}
                  style={{
                    textAlign: "left",
                    borderRadius: 20,
                    padding: 14,
                    border: selected ? "1px solid #61A36A" : "1px solid rgba(255,255,255,0.08)",
                    background: selected ? "rgba(97,163,106,0.16)" : "rgba(255,255,255,0.04)",
                    color: "inherit",
                    display: "grid",
                    gap: 8,
                  }}
                >
                  <strong>{servicio.nombre}</strong>
                  <div style={{ color: "rgba(255,255,255,0.72)" }}>{servicio.duracion_base_minutos} min base</div>
                  <div style={{ color: "rgba(255,255,255,0.72)" }}>Bs {Number(servicio.precio_base || 0).toFixed(2)}</div>
                </button>
              );
            })}
          </div>
          {servicioSel && mascotaSel ? <DesgloseDuracion servicio={servicioSel} mascota={mascotaSel} /> : null}
        </div>
      );
    }

    if (paso === 3) {
      const fechaInvalida = fechaSel && !fechasDisponibles.includes(fechaSel);
      return (
        <div style={{ display: "grid", gap: 14 }}>
          <div style={{ display: "grid", gap: 8 }}>
            <h3 style={{ margin: 0 }}>Fecha, franja y groomer</h3>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.68)" }}>El sistema solo te deja avanzar con días que tengan cupo suficiente para la duración ajustada.</p>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            <label className="input-field">
              <span>Fecha preferida</span>
              <div className="input-wrapper" style={{ position: "relative" }}>
                <input
                  type="date"
                  min={hoyIso}
                  max={maxIso}
                  value={fechaSel}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (value && fechasDisponibles.length && !fechasDisponibles.includes(value)) {
                      setFechaSel(value);
                      setError("Esa fecha no tiene disponibilidad suficiente.");
                      return;
                    }
                    setError("");
                    setFechaSel(value);
                  }}
                />
                {cargandoFechas ? <span className="pill" style={{ position: "absolute", right: 10, top: 10 }}>Cargando...</span> : null}
              </div>
            </label>
            {fechasDisponibles.length ? null : (
              <div className="alert alert-error">No hay disponibilidad en los próximos 30 días. Contacta a recepción.</div>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
              {Array.from({ length: 30 }, (_, index) => {
                const current = new Date(today.getTime() + index * 24 * 60 * 60 * 1000);
                const value = current.toISOString().slice(0, 10);
                const available = fechasDisponibles.includes(value);
                return (
                  <button
                    key={value}
                    type="button"
                    disabled={!available}
                    onClick={() => setFechaSel(value)}
                    title={available ? "Disponible" : "Sin disponibilidad"}
                    style={{
                      borderRadius: 16,
                      padding: 12,
                      border: value === fechaSel ? "1px solid #61A36A" : "1px solid rgba(255,255,255,0.08)",
                      background: available ? (value === fechaSel ? "rgba(97,163,106,0.18)" : "rgba(255,255,255,0.04)") : "rgba(255,255,255,0.02)",
                      color: "inherit",
                      opacity: available ? 1 : 0.4,
                    }}
                  >
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.68)" }}>{current.toLocaleDateString("es-BO", { weekday: "short" })}</div>
                    <strong>{current.getDate()}</strong>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ display: "grid", gap: 8 }}>
            <span style={{ fontWeight: 700 }}>Franja</span>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
              {FRANJAS.map((franja) => {
                const disponible = franja.key === "cualquiera" ? franjasDisponibles.cualquiera : franjasDisponibles[franja.key];
                const selected = franjaSel === franja.key;
                return (
                  <button
                    key={franja.key}
                    type="button"
                    onClick={() => disponible && setFranjaSel(franja.key)}
                    disabled={!disponible}
                    title={disponible ? franja.label : "Sin disponibilidad en esta franja para la fecha seleccionada"}
                    style={{
                      borderRadius: 16,
                      padding: 12,
                      border: selected ? "1px solid #61A36A" : "1px solid rgba(255,255,255,0.08)",
                      background: disponible ? (selected ? "rgba(97,163,106,0.18)" : "rgba(255,255,255,0.04)") : "rgba(255,255,255,0.02)",
                      color: "inherit",
                      opacity: disponible ? 1 : 0.45,
                    }}
                  >
                    {franja.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ display: "grid", gap: 8 }}>
            <label className="input-field">
              <span>Preferencia de groomer (opcional)</span>
              <div className="input-wrapper">
                <select
                  value={groomerSel?.id || ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    setGroomerSel(value ? groomers.find((item) => String(item.id) === String(value)) || null : null);
                  }}
                >
                  <option value="">Sin preferencia</option>
                  {groomers.map((groomer) => (
                    <option key={groomer.id} value={groomer.id}>
                      {groomer.nombre} {groomer.especialidad ? `· ${groomer.especialidad}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </label>
          </div>

          <div className="cliente-summary" style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)" }}>
            <div><strong>Duración ajustada:</strong> {servicioDuracion || "--"} min</div>
            <div><strong>Fecha:</strong> {fechaLabel}</div>
            <div><strong>Franja:</strong> {franjaLabel(franjaSel)}</div>
            <div><strong>Groomer preferido:</strong> {currentGroomerLabel}</div>
          </div>
        </div>
      );
    }

    return (
      <div style={{ display: "grid", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Confirmar solicitud</h3>
        <div className="cliente-summary" style={{ padding: 14, borderRadius: 16, background: "rgba(255,255,255,0.04)", display: "grid", gap: 10 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ width: 40, height: 40, borderRadius: 14, overflow: "hidden", background: "rgba(255,255,255,0.08)", display: "grid", placeItems: "center" }}>
              {mascotaSel?.foto_url ? <img src={mascotaSel.foto_url} alt={mascotaSel.nombre} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : "🐾"}
            </span>
            <div>
              <div><strong>{mascotaSel?.nombre}</strong> — {mascotaSel?.raza || mascotaSel?.especie || "Sin raza"}</div>
              <div>{mascotaSel?.peso_kg ? `${mascotaSel.peso_kg} kg` : "Peso no registrado"}</div>
            </div>
          </div>
          <div><strong>Servicio:</strong> {servicioSel?.nombre}</div>
          <div><strong>Duración estimada:</strong> {servicioDuracion} min</div>
          <div><strong>Fecha:</strong> {fechaLabel}</div>
          <div><strong>Franja:</strong> {franjaLabel(franjaSel)}</div>
          <div><strong>Groomer preferido:</strong> {currentGroomerLabel}</div>
        </div>

        <div className="input-field">
          <span>Notas</span>
          <div className="input-wrapper">
            <textarea value={notas} onChange={(event) => setNotas(event.target.value)} rows={3} style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }} />
          </div>
        </div>

        <div style={{ padding: 14, borderRadius: 16, background: "rgba(97,163,106,0.10)", color: "rgba(255,255,255,0.88)" }}>
          📋 Tu solicitud quedará en estado En revisión. Recibirás una confirmación por WhatsApp/email en cuanto recepción apruebe la cita.
        </div>
      </div>
    );
  };

  return (
    <section className="cliente-card" style={{ display: "grid", gap: 16, position: "relative" }}>
      {toast ? (
        <div style={{ position: "absolute", top: 12, right: 12, zIndex: 2, padding: "10px 14px", borderRadius: 14, background: "#1D9E75", color: "white", boxShadow: "0 14px 36px rgba(0,0,0,0.22)" }}>
          {toast}
        </div>
      ) : null}

      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Solicitar cita</h3>
            <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.7)" }}>El wizard conserva tu selección mientras avanzas entre pasos.</p>
          </div>
          <span className="pill">Paso {paso} de 4</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}>
          {FASES.map((label, index) => {
            const step = index + 1;
            const active = paso === step;
            const completed = paso > step;
            return (
              <div key={label} style={{ display: "grid", gap: 6, justifyItems: "center" }}>
                <div style={{ width: 34, height: 34, borderRadius: "999px", display: "grid", placeItems: "center", background: completed || active ? "#1D9E75" : "rgba(255,255,255,0.14)", color: "white", fontWeight: 700 }}>
                  {completed ? "✓" : step}
                </div>
                <span style={{ fontSize: 12, color: active || completed ? "#D7F3E0" : "rgba(255,255,255,0.58)" }}>{label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {renderPaso()}

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 10 }}>
          {paso > 1 ? (
            <button type="button" className="ghost-button" onClick={retroceder}>
              Atrás
            </button>
          ) : null}
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {paso < 4 ? (
            <Button type="button" onClick={avanzar} disabled={cargandoFechas && paso === 3}>
              Siguiente
            </Button>
          ) : (
            <Button type="button" onClick={guardar} disabled={enviando}>
              {enviando ? "Enviando..." : "Enviar solicitud"}
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
