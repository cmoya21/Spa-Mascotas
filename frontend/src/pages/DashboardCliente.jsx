import { useEffect, useMemo, useState } from "react";

import { useAuthContext } from "../context/AuthContext.jsx";
import {
  apiActualizarMiMascota,
  apiCrearMiMascota,
  apiEliminarMiMascota,
  apiGetMisCitas,
  apiGetMisMascotas,
  apiGetMisNotificaciones,
  apiRegistrarVacunaMascota,
} from "../api/clienteApi.js";
import Button from "../components/shared/Button";
import FormMascota from "../components/cliente/FormMascota.jsx";
import FormCancelacion from "../components/cliente/FormCancelacion.jsx";
import HistorialMascota from "../components/cliente/HistorialMascota.jsx";
import BeneficiosFrecuente from "../components/cliente/BeneficiosFrecuente.jsx";
import RecomendacionesPersonalizadas from "../components/tienda/RecomendacionesPersonalizadas.jsx";
import CampanaNotificaciones from "../components/shared/CampanaNotificaciones.jsx";
import WizardSolicitudCita from "../components/cliente/WizardSolicitudCita.jsx";

const initialVaccineForm = {
  nombre_vacuna: "",
  aplicada_en: "",
  proxima_aplicacion: "",
  lote: "",
  observaciones: "",
};

export default function DashboardCliente() {
  const { usuario } = useAuthContext();
  const [mascotas, setMascotas] = useState([]);
  const [citas, setCitas] = useState([]);
  const [notificaciones, setNotificaciones] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [editingMascota, setEditingMascota] = useState(null);
  const [showMascotaForm, setShowMascotaForm] = useState(false);
  const [selectedMascotaId, setSelectedMascotaId] = useState("");
  const [citaParaCancelar, setCitaParaCancelar] = useState(null);
  const [toast, setToast] = useState("");
  const [vaccineMascota, setVaccineMascota] = useState(null);
  const [vaccineForm, setVaccineForm] = useState(initialVaccineForm);
  const [vaccineError, setVaccineError] = useState("");

  const loadData = async () => {
    setBusy(true);
    setError("");
    try {
      const [mascotasData, citasData, notificacionesData] = await Promise.all([
        apiGetMisMascotas(),
        apiGetMisCitas({ proximas: true }),
        apiGetMisNotificaciones(),
      ]);
      const mascotasList = mascotasData.mascotas || [];
      setMascotas(mascotasList);
      setCitas(citasData.citas || []);
      setNotificaciones(notificacionesData.notificaciones || []);
      setSelectedMascotaId((current) => {
        if (current && mascotasList.some((item) => String(item.id) === String(current))) {
          return current;
        }
        return mascotasList[0] ? String(mascotasList[0].id) : "";
      });
    } catch (err) {
      setError("No se pudieron cargar tus datos.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const selectedMascota = useMemo(
    () => mascotas.find((item) => String(item.id) === String(selectedMascotaId)) || null,
    [mascotas, selectedMascotaId]
  );

  const proximasCitas = citas.filter((item) => ["pendiente", "agendada", "confirmada", "en_progreso"].includes(item.estado));
  const citasCompletadas = citas.filter((item) => item.estado === "completada");
  const notificacionesVisibles = notificaciones.slice(0, 6);

  const handleCrearOActualizarMascota = async (payload) => {
    if (editingMascota?.id) {
      await apiActualizarMiMascota(editingMascota.id, payload);
    } else {
      await apiCrearMiMascota(payload);
    }
    setEditingMascota(null);
    setShowMascotaForm(false);
    await loadData();
  };

  const handleEliminarMascota = async (mascotaId) => {
    if (!window.confirm("¿Desvincular esta mascota de tu cuenta?")) return;
    await apiEliminarMiMascota(mascotaId);
    await loadData();
  };

  const handleRegistrarVacuna = async () => {
    if (!vaccineMascota) return;
    setVaccineError("");
    if (!vaccineForm.nombre_vacuna.trim()) {
      setVaccineError("Escribe el nombre de la vacuna.");
      return;
    }
    await apiRegistrarVacunaMascota(vaccineMascota.id, {
      ...vaccineForm,
      aplicada_en: vaccineForm.aplicada_en || undefined,
      proxima_aplicacion: vaccineForm.proxima_aplicacion || undefined,
    });
    setVaccineMascota(null);
    setVaccineForm(initialVaccineForm);
    await loadData();
  };

  const dashboardStats = [
    { label: "Mascotas", value: mascotas.length },
    { label: "Citas próximas", value: proximasCitas.length },
    { label: "Mensajes", value: notificacionesVisibles.length },
  ];

  const estadoBadge = (estado) => {
    const base = { borderRadius: 999, padding: "4px 10px", fontSize: 12, fontWeight: 700 };
    if (estado === "agendada") return <span style={{ ...base, background: "rgba(245, 158, 11, 0.16)", color: "#fbbf24", border: "1px dashed #fbbf24" }}>En revisión</span>;
    if (estado === "confirmada") return <span style={{ ...base, background: "rgba(34, 197, 94, 0.16)", color: "#4ade80" }}>Confirmada ✓</span>;
    if (estado === "en_progreso") return <span style={{ ...base, background: "rgba(59, 130, 246, 0.16)", color: "#60a5fa" }}>En curso</span>;
    if (estado === "completada") return <span style={{ ...base, background: "rgba(148, 163, 184, 0.16)", color: "#cbd5e1" }}>Completada</span>;
    if (estado === "cancelada") return <span style={{ ...base, background: "rgba(239, 68, 68, 0.16)", color: "#fca5a5", textDecoration: "line-through" }}>Cancelada</span>;
    return <span style={{ ...base, background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.8)" }}>{estado}</span>;
  };

  return (
    <div style={{ minHeight: "100vh", padding: 24, background: "linear-gradient(180deg, #0d1117 0%, #111827 100%)", color: "#f4f7fb" }}>
      <div style={{ maxWidth: 1320, margin: "0 auto", display: "grid", gap: 20 }}>
        <header style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.68)", letterSpacing: 1.2, textTransform: "uppercase", fontSize: 12 }}>
              Autogestión del cliente
            </p>
            <h1 style={{ margin: "6px 0 8px", fontSize: 38 }}>Hola, {usuario?.nombre_completo || usuario?.email || "cliente"}</h1>
            <p style={{ margin: 0, maxWidth: 760, color: "rgba(255,255,255,0.72)" }}>
              Gestiona varias mascotas, solicita citas, revisa tu historial y controla notificaciones desde un solo lugar.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <a className="ghost-button" href="/tienda">Ir a tienda</a>
            <button type="button" className="ghost-button" onClick={() => setShowMascotaForm(true)}>
              Nueva mascota
            </button>
            <CampanaNotificaciones />
          </div>
        </header>

        {toast ? <div className="alert alert-success">{toast}</div> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}

        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
          {dashboardStats.map((item) => (
            <article key={item.label} style={{ borderRadius: 20, padding: 18, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ color: "rgba(255,255,255,0.65)", marginBottom: 6 }}>{item.label}</div>
              <div style={{ fontSize: 32, fontWeight: 700 }}>{busy ? "..." : item.value}</div>
            </article>
          ))}
        </section>

        <BeneficiosFrecuente />

        <section style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)", gap: 18, alignItems: "start" }}>
          <div style={{ display: "grid", gap: 18 }}>
            <div style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 14 }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: 22 }}>Tus mascotas</h2>
                  <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>Puedes manejar más de una mascota por cuenta.</p>
                </div>
                <Button type="button" onClick={() => setShowMascotaForm(true)}>Agregar</Button>
              </div>

              <div style={{ display: "grid", gap: 12 }}>
                {mascotas.map((mascota) => {
                  const isSelected = String(selectedMascotaId) === String(mascota.id);
                  return (
                    <article
                      key={mascota.id}
                      style={{
                        borderRadius: 20,
                        padding: 16,
                        background: isSelected ? "rgba(216, 173, 79, 0.12)" : "rgba(255,255,255,0.04)",
                        border: isSelected ? "1px solid rgba(216,173,79,0.55)" : "1px solid rgba(255,255,255,0.07)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                        <div>
                          <strong style={{ fontSize: 18 }}>{mascota.nombre}</strong>
                          <div style={{ color: "rgba(255,255,255,0.7)" }}>
                            {mascota.especie}{mascota.raza ? ` · ${mascota.raza}` : ""}{mascota.tamano ? ` · ${mascota.tamano}` : ""}
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {mascota.es_principal ? <span className="pill">Principal</span> : null}
                          {mascota.alergias_conocidas ? <span className="pill">Alergias</span> : null}
                        </div>
                      </div>

                      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                        <div style={{ color: "rgba(255,255,255,0.72)" }}>
                          {mascota.peso_kg ? `${mascota.peso_kg} kg · ` : ""}
                          {mascota.temperamento || "sin temperamento"}
                        </div>
                        {mascota.alergias_conocidas ? <div>Alergias: {mascota.alergias_conocidas}</div> : null}
                        {mascota.restricciones_medicas ? <div>Restricciones: {mascota.restricciones_medicas}</div> : null}
                      </div>

                      <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button type="button" className="ghost-button" onClick={() => { setSelectedMascotaId(String(mascota.id)); }}>
                          Ver historial
                        </button>
                        <button type="button" className="ghost-button" onClick={() => { setEditingMascota(mascota); setShowMascotaForm(true); }}>
                          Editar
                        </button>
                        <button type="button" className="ghost-button" onClick={() => setVaccineMascota(mascota)}>
                          Registrar vacuna
                        </button>
                        <button type="button" className="ghost-button" onClick={() => handleEliminarMascota(mascota.id)}>
                          Desvincular
                        </button>
                      </div>

                      {mascota.vacunas?.length ? (
                        <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
                          <strong style={{ fontSize: 14 }}>Vacunas recientes</strong>
                          {mascota.vacunas.map((vacuna) => (
                            <div key={vacuna.id} style={{ color: "rgba(255,255,255,0.72)" }}>
                              {vacuna.nombre_vacuna} · {vacuna.aplicada_en || "sin fecha"}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  );
                })}
                {!mascotas.length ? <div className="admin-empty">Aún no registras mascotas.</div> : null}
              </div>
            </div>

            <WizardSolicitudCita
              mascotas={mascotas}
              onCreated={loadData}
              onRequestRegistrarMascota={() => {
                setEditingMascota(null);
                setShowMascotaForm(true);
              }}
            />
          </div>

          <div style={{ display: "grid", gap: 18 }}>
            <section style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h2 style={{ margin: "0 0 14px" }}>Próximas citas</h2>
              <div style={{ display: "grid", gap: 10 }}>
                {proximasCitas.length ? proximasCitas.map((cita) => (
                  <article key={cita.id} style={{ borderRadius: 18, padding: 14, background: "rgba(255,255,255,0.04)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <strong>{cita.mascota_nombre}</strong>
                      {estadoBadge(cita.estado)}
                    </div>
                    <div style={{ marginTop: 6, color: "rgba(255,255,255,0.75)" }}>{cita.servicio_nombre}</div>
                    <div style={{ marginTop: 6 }}>{cita.fecha_hora_inicio ? new Date(cita.fecha_hora_inicio).toLocaleString() : "Sin fecha"}</div>
                    <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {cita.estado === "agendada" ? (
                        <button type="button" className="ghost-button" onClick={() => setCitaParaCancelar(cita)}>
                          Cancelar
                        </button>
                      ) : cita.estado === "confirmada" ? (
                        <span style={{ color: "rgba(255,255,255,0.7)" }}>Para cancelar esta cita, contacta a recepción.</span>
                      ) : null}
                    </div>
                  </article>
                )) : <div className="admin-empty">No tienes citas próximas.</div>}
              </div>
            </section>

            <section style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h2 style={{ margin: "0 0 14px" }}>Recomendaciones para tu mascota</h2>
              <RecomendacionesPersonalizadas onAgregar={(producto) => { /* no-op, user can go to tienda */ }} />
            </section>

            <section style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h2 style={{ margin: "0 0 14px" }}>Notificaciones</h2>
              <div style={{ display: "grid", gap: 10 }}>
                {notificacionesVisibles.length ? notificacionesVisibles.map((item) => (
                  <article key={item.id} style={{ borderRadius: 16, padding: 12, background: "rgba(255,255,255,0.04)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <strong>{item.tipo_evento}</strong>
                      <span className="pill">{item.estado}</span>
                    </div>
                    <div style={{ marginTop: 6, color: "rgba(255,255,255,0.75)" }}>{item.mensaje}</div>
                  </article>
                )) : <div className="admin-empty">Sin notificaciones.</div>}
              </div>
            </section>

            <section style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <h2 style={{ margin: "0 0 14px" }}>Últimas encuestas</h2>
              <div style={{ display: "grid", gap: 10 }}>
                {citasCompletadas.length ? citasCompletadas.map((cita) => (
                  <article key={cita.id} style={{ borderRadius: 16, padding: 12, background: "rgba(255,255,255,0.04)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <strong>{cita.mascota_nombre}</strong>
                      <span>{cita.estado}</span>
                    </div>
                    <div style={{ marginTop: 6, color: "rgba(255,255,255,0.75)" }}>{cita.servicio_nombre}</div>
                    <div style={{ marginTop: 6 }}>{cita.tiene_encuesta ? "Encuesta respondida" : "Pendiente de encuesta"}</div>
                  </article>
                )) : <div className="admin-empty">Sin citas completadas.</div>}
              </div>
            </section>
          </div>
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 18 }}>
          <HistorialMascota mascotaId={selectedMascotaId} refreshToken={selectedMascotaId} />
          <section style={{ borderRadius: 24, padding: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <h2 style={{ marginTop: 0 }}>Tu mascota seleccionada</h2>
            {selectedMascota ? (
              <div style={{ display: "grid", gap: 10 }}>
                <div><strong>Nombre:</strong> {selectedMascota.nombre}</div>
                <div><strong>Especie:</strong> {selectedMascota.especie}</div>
                <div><strong>Raza:</strong> {selectedMascota.raza || "-"}</div>
                <div><strong>Alergias:</strong> {selectedMascota.alergias_conocidas || "-"}</div>
                <div><strong>Restricciones:</strong> {selectedMascota.restricciones_medicas || "-"}</div>
              </div>
            ) : (
              <div className="admin-empty">Selecciona una mascota para ver el detalle.</div>
            )}
          </section>
        </section>
      </div>

      {showMascotaForm ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(5, 8, 12, 0.66)", display: "grid", placeItems: "center", padding: 16, zIndex: 50 }}>
          <div style={{ width: "min(960px, 100%)", borderRadius: 24, padding: 20, background: "#0f1722", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0 }}>{editingMascota ? "Editar mascota" : "Registrar mascota"}</h3>
                <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>Los cambios se guardan en tu perfil.</p>
              </div>
              <button type="button" className="ghost-button" onClick={() => { setEditingMascota(null); setShowMascotaForm(false); }}>
                Cerrar
              </button>
            </div>
            <FormMascota
              initialValue={editingMascota}
              onSubmit={handleCrearOActualizarMascota}
              onCancel={() => { setEditingMascota(null); setShowMascotaForm(false); }}
            />
          </div>
        </div>
      ) : null}

      {vaccineMascota ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(5, 8, 12, 0.66)", display: "grid", placeItems: "center", padding: 16, zIndex: 50 }}>
          <div style={{ width: "min(640px, 100%)", borderRadius: 24, padding: 20, background: "#0f1722", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0 }}>Registrar vacuna</h3>
                <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>{vaccineMascota.nombre}</p>
              </div>
              <button type="button" className="ghost-button" onClick={() => setVaccineMascota(null)}>Cerrar</button>
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              <label className="input-field">
                <span>Nombre vacuna</span>
                <div className="input-wrapper">
                  <input value={vaccineForm.nombre_vacuna} onChange={(event) => setVaccineForm((current) => ({ ...current, nombre_vacuna: event.target.value }))} />
                </div>
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
                <label className="input-field">
                  <span>Aplicada en</span>
                  <div className="input-wrapper">
                    <input type="date" value={vaccineForm.aplicada_en} onChange={(event) => setVaccineForm((current) => ({ ...current, aplicada_en: event.target.value }))} />
                  </div>
                </label>
                <label className="input-field">
                  <span>Próxima aplicación</span>
                  <div className="input-wrapper">
                    <input type="date" value={vaccineForm.proxima_aplicacion} onChange={(event) => setVaccineForm((current) => ({ ...current, proxima_aplicacion: event.target.value }))} />
                  </div>
                </label>
              </div>
              <label className="input-field">
                <span>Lote</span>
                <div className="input-wrapper">
                  <input value={vaccineForm.lote} onChange={(event) => setVaccineForm((current) => ({ ...current, lote: event.target.value }))} />
                </div>
              </label>
              <label className="input-field">
                <span>Observaciones</span>
                <div className="input-wrapper">
                  <textarea rows={3} value={vaccineForm.observaciones} onChange={(event) => setVaccineForm((current) => ({ ...current, observaciones: event.target.value }))} style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }} />
                </div>
              </label>
              {vaccineError ? <div className="alert alert-error">{vaccineError}</div> : null}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button type="button" className="ghost-button" onClick={() => setVaccineMascota(null)}>Cancelar</button>
                <Button type="button" onClick={handleRegistrarVacuna}>Guardar vacuna</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {citaParaCancelar ? (
        <FormCancelacion
          cita={citaParaCancelar}
          onCancelada={async () => {
            setCitaParaCancelar(null);
            setToast("Cita cancelada. El horario ha quedado libre.");
            await loadData();
          }}
          onCerrar={() => setCitaParaCancelar(null)}
        />
      ) : null}
    </div>
  );
}
