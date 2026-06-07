import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useNavigate, useParams } from "react-router-dom";

import Button from "../components/shared/Button";
import InputField from "../components/shared/InputField";
import ChecklistPanel from "../components/grooming/ChecklistPanel.jsx";
import PanelSalidaInsumos from "../components/groomer/PanelSalidaInsumos.jsx";
import {
  apiCerrarFicha,
  apiCrearFicha,
  apiDeleteFichaPhoto,
  apiGetAgendaSemanaPersonal,
  apiGetFicha,
  apiGetFichaByCita,
  apiListFichas,
  apiUpdateChecklistItem,
  apiUpdateFichaBase,
  apiUploadFichaPhoto,
} from "../api/groomerApi.js";
import ModalCierre from "../components/groomer/ModalCierre.jsx";
import usePuedeCerrar from "../hooks/usePuedeCerrar";

const EMPTY_START = {
  estado_inicial: "",
  temperatura_ingreso: "",
  peso_momento_servicio: "",
  raza_tamano_momento: "",
  notas_internas: "",
};

const EMPTY_CLOSE = {
  estado_final: "",
  observaciones_final: "",
  duracion_real: "",
};

function flattenAgenda(agenda) {
  return Object.values(agenda || {}).flatMap((item) => (Array.isArray(item) ? item : item?.citas || []));
}

export default function FichaTecnica() {
  const { citaId, fichaId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [agenda, setAgenda] = useState([]);
  const [ficha, setFicha] = useState(null);
  const [fichas, setFichas] = useState([]);
  const [startForm, setStartForm] = useState(EMPTY_START);
  const [baseForm, setBaseForm] = useState(EMPTY_START);
  const [closeForm, setCloseForm] = useState(EMPTY_CLOSE);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fotoPreviews, setFotoPreviews] = useState({ antes: null, despues: null });
  const [citaBase, setCitaBase] = useState(null);
  const fechaQuery = useMemo(() => new URLSearchParams(location.search).get("fecha"), [location.search]);
  const citaQueryId = useMemo(() => new URLSearchParams(location.search).get("cita_id"), [location.search]);
  const citaReferencia = fichaId || citaId || citaQueryId;

  const cita = useMemo(() => {
    return agenda.find((item) => String(item.id) === String(citaReferencia)) || ficha?.cita || citaBase || null;
  }, [agenda, citaReferencia, ficha, citaBase]);

  const loadContext = async () => {
    setLoading(true);
    setError("");
    try {
      if (fichaId) {
        const detail = await apiGetFicha(fichaId);
        const fichaDetalle = detail.ficha || null;
        setFicha(fichaDetalle);
        setAgenda(fichaDetalle?.cita ? [fichaDetalle.cita] : []);
        setFichas(fichaDetalle ? [fichaDetalle] : []);
        setCitaBase(fichaDetalle?.cita || null);
        setBaseForm({
          estado_inicial: fichaDetalle?.estado_inicial || "",
          temperatura_ingreso: fichaDetalle?.temperatura_ingreso || "",
          peso_momento_servicio: fichaDetalle?.peso_momento_servicio || "",
          raza_tamano_momento: fichaDetalle?.raza_tamano_momento || "",
          notas_internas: fichaDetalle?.notas_internas || "",
        });
      } else {
        let fichaEncontrada = null;
        if (citaReferencia) {
          try {
            const detail = await apiGetFichaByCita(citaReferencia);
            fichaEncontrada = detail.ficha || null;
          } catch (err) {
            if (err?.response?.status !== 404) throw err;
          }
        }

        if (!fichaEncontrada) {
          const fechaBase = fechaQuery || new Date().toISOString().slice(0, 10);
          const [agendaData, fichasData] = await Promise.all([
            apiGetAgendaSemanaPersonal({ fecha: fechaBase }),
            apiListFichas(citaReferencia),
          ]);
          const agendaFlat = flattenAgenda(agendaData.dias || agendaData.agenda || {});
          setAgenda(agendaFlat);
          const listaFichas = fichasData.fichas || [];
          setFichas(listaFichas);
          const citaEncontrada = agendaFlat.find((item) => String(item.id) === String(citaReferencia)) || null;
          setCitaBase(citaEncontrada);
          const fichaExistente = listaFichas.find((item) => String(item.cita_id) === String(citaReferencia));
          if (fichaExistente) {
            const detail = await apiGetFicha(fichaExistente.id);
            fichaEncontrada = detail.ficha || null;
          }
        }

        if (fichaEncontrada) {
          setFicha(fichaEncontrada);
          setAgenda(fichaEncontrada?.cita ? [fichaEncontrada.cita] : agenda);
          setCitaBase(fichaEncontrada?.cita || citaBase || null);
          setBaseForm({
            estado_inicial: fichaEncontrada?.estado_inicial || "",
            temperatura_ingreso: fichaEncontrada?.temperatura_ingreso || "",
            peso_momento_servicio: fichaEncontrada?.peso_momento_servicio || "",
            raza_tamano_momento: fichaEncontrada?.raza_tamano_momento || "",
            notas_internas: fichaEncontrada?.notas_internas || "",
          });
        } else {
          setFicha(null);
          setBaseForm(EMPTY_START);
        }
      }
    } catch (err) {
      setError("No se pudo cargar la ficha operativa.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContext();
  }, [citaId, fichaId, citaQueryId, fechaQuery]);

  useEffect(() => {
    if (!ficha) return;
    setBaseForm({
      estado_inicial: ficha.estado_inicial || "",
      temperatura_ingreso: ficha.temperatura_ingreso || "",
      peso_momento_servicio: ficha.peso_momento_servicio || "",
      raza_tamano_momento: ficha.raza_tamano_momento || "",
      notas_internas: ficha.notas_internas || "",
    });
  }, [ficha]);

  

  const refreshFicha = async () => {
    if (!ficha?.id) return;
    const detail = await apiGetFicha(ficha.id);
    setFicha(detail.ficha || null);
  };

  const estadoCierre = usePuedeCerrar(ficha?.id);

  const handleStartService = async () => {
    if (!cita) return;
    setError("");
    try {
      const data = await apiCrearFicha({
        cita_id: cita.id,
        ...startForm,
      });
      setFicha(data.ficha || null);
      await loadContext();
    } catch (err) {
      const message = err?.response?.data?.message || "No se pudo iniciar el servicio.";
      setError(message);
    }
  };

  const handleSaveBase = async () => {
    if (!ficha?.id) return;
    setError("");
    try {
      const data = await apiUpdateFichaBase(ficha.id, baseForm);
      if (data?.ficha) {
        setFicha(data.ficha);
      }
      await loadContext();
    } catch (err) {
      setError(err?.response?.data?.message || "No se pudo guardar el estado inicial.");
    }
  };

  const handleToggleChecklist = async (item, checked, observation) => {
    if (!ficha?.id) return;
    setError("");
    try {
      const payload = {
        completado: checked,
        observacion: observation !== undefined ? observation : item.observacion,
      };
      const data = await apiUpdateChecklistItem(ficha.id, item.item_id, payload);
      await refreshFicha();
      if (data.checklist_completo) {
        setFicha((current) => (current ? { ...current, checklist_completo: true } : current));
      }
    } catch (err) {
      const message = err?.response?.data?.message || "No se pudo actualizar el checklist.";
      setError(message);
    }
  };

  const handleUploadPhoto = async (event, tipo) => {
    if (!ficha?.id) return;
    const archivo = event.target.files?.[0];
    if (!archivo) return;
    const ext = archivo.name.split(".").pop()?.toLowerCase();
    if (!ext || !["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setError("Solo se permiten imágenes JPG, PNG o WEBP.");
      event.target.value = "";
      return;
    }
    setUploading(true);
    setError("");
    const previewUrl = URL.createObjectURL(archivo);
    setFotoPreviews((current) => ({ ...current, [tipo]: previewUrl }));
    try {
      const formData = new FormData();
      formData.append("archivo", archivo);
      formData.append("tipo", tipo);
      await apiUploadFichaPhoto(ficha.id, formData);
      await refreshFicha();
    } catch (err) {
      const message = err?.response?.data?.message || "No se pudo cargar la foto.";
      setError(message);
    } finally {
      setUploading(false);
      setFotoPreviews((current) => ({ ...current, [tipo]: null }));
      URL.revokeObjectURL(previewUrl);
      event.target.value = "";
    }
  };

  const handleDropPhoto = async (event, tipo) => {
    event.preventDefault();
    const archivo = event.dataTransfer.files?.[0];
    if (!archivo) return;
    const fakeEvent = { target: { files: [archivo], value: "" } };
    await handleUploadPhoto(fakeEvent, tipo);
  };

  const handleDeletePhoto = async (fotoId) => {
    if (!ficha?.id) return;
    setError("");
    try {
      await apiDeleteFichaPhoto(ficha.id, fotoId);
      await refreshFicha();
    } catch (err) {
      setError("No se pudo eliminar la foto.");
    }
  };

  const closeTooltip = !ficha
    ? "Inicia el servicio primero"
    : ficha.fecha_cierre
      ? "La ficha ya está cerrada"
      : !ficha.checklist_completo
        ? "Completa el checklist para poder cerrar"
        : (ficha.fotos?.antes || []).length < 1
          ? "Sube al menos 1 foto del estado inicial"
          : (ficha.fotos?.despues || []).length < 1
            ? "Sube al menos 1 foto del resultado final"
            : "Cerrar servicio";

  const closeMissingReasons = [];
  if (ficha && !ficha.checklist_completo) closeMissingReasons.push("Checklist incompleto");
  if (ficha && (ficha.fotos?.antes || []).length < 1) closeMissingReasons.push("Falta foto antes");
  if (ficha && (ficha.fotos?.despues || []).length < 1) closeMissingReasons.push("Falta foto después");

  const handleCloseService = async () => {
    if (!ficha?.id) return;
    setError("");
    try {
      await apiCerrarFicha(ficha.id, {
        estado_final: closeForm.estado_final,
        observaciones_final: closeForm.observaciones_final,
        duracion_real: closeForm.duracion_real ? Number(closeForm.duracion_real) : undefined,
      });
      navigate("/groomers/agenda");
    } catch (err) {
      const message = err?.response?.data?.message || "No se pudo cerrar la ficha.";
      setError(message);
    }
  };

  const checklistItems = ficha?.checklist || [];
  const fotosAntes = ficha?.fotos?.antes || [];
  const fotosDespues = ficha?.fotos?.despues || [];

  useEffect(() => {
    if (!ficha?.cita?.servicio?.duracion_base_minutos || closeForm.duracion_real) return;
    setCloseForm((current) => ({
      ...current,
      duracion_real: String(ficha.cita.servicio.duracion_base_minutos),
    }));
  }, [ficha?.cita?.servicio?.duracion_base_minutos]);

  return (
    <div style={{ minHeight: "100vh", padding: 24, background: "linear-gradient(180deg, #0c1016 0%, #111827 100%)", color: "#f4f7fb" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", display: "grid", gap: 18 }}>
        <header style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <p style={{ margin: 0, color: "rgba(255,255,255,0.65)", textTransform: "uppercase", letterSpacing: 1.2, fontSize: 12 }}>Vista operativa del groomer</p>
            <h1 style={{ margin: "8px 0 0" }}>{cita ? `${cita.mascota?.nombre || "Mascota"} · ${cita.servicio?.nombre || "Servicio"}` : "Ficha técnica"}</h1>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <a className="ghost-button" href="/groomers/agenda">Volver a agenda</a>
            <button type="button" className="ghost-button" onClick={loadContext}>Actualizar</button>
          </div>
        </header>

        {error ? <div className="alert alert-error">{error}</div> : null}
        {loading ? <div className="admin-empty">Cargando información de la ficha...</div> : null}

        {cita?.mascota ? (
          <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 220px) 1fr", gap: 18, alignItems: "start" }}>
              <div style={{ borderRadius: 22, overflow: "hidden", background: "rgba(255,255,255,0.05)", minHeight: 180 }}>
                {cita.mascota.foto_url ? (
                  <img src={cita.mascota.foto_url} alt={cita.mascota.nombre} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <div style={{ minHeight: 180, display: "grid", placeItems: "center", color: "rgba(255,255,255,0.65)" }}>Sin foto</div>
                )}
              </div>
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <h2 style={{ margin: 0 }}>{cita.mascota.nombre}</h2>
                    <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.72)" }}>
                      {cita.mascota.raza || "Sin raza"} · {cita.mascota.peso_kg || "-"} kg · {cita.mascota.temperamento || "sin temperamento"} · {cita.mascota.edad_anios ?? "-"} años
                    </p>
                  </div>
                  <span className="pill">{ficha?.checklist_completo ? "Checklist completo" : "Checklist pendiente"}</span>
                </div>
                {cita.mascota.alergias_conocidas ? <div className="alert alert-error" style={{ fontWeight: 700 }}>🚨 ALERTA DE ALERGIA: {cita.mascota.alergias_conocidas}</div> : null}
                {cita.mascota.restricciones_medicas ? <div className="alert" style={{ background: "rgba(255, 165, 0, 0.16)", color: "#ffd59c", fontWeight: 700 }}>⚠ Restricciones médicas: {cita.mascota.restricciones_medicas}</div> : null}
                <div style={{ display: "grid", gap: 6, color: "rgba(255,255,255,0.8)" }}>
                  {cita.mascota.observaciones ? <div>Observaciones: {cita.mascota.observaciones}</div> : null}
                  <div>Hora de inicio: {cita.fecha_hora_inicio ? new Date(cita.fecha_hora_inicio).toLocaleString() : "-"}</div>
                  <div>Estado de cita: {cita.estado}</div>
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {!ficha && cita ? (
          <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
            <h3 style={{ margin: 0 }}>Estado inicial</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
              <InputField label="Estado inicial" value={startForm.estado_inicial} onChange={(value) => setStartForm((current) => ({ ...current, estado_inicial: value }))} />
              <InputField label="Temperatura ingreso" type="number" value={startForm.temperatura_ingreso} onChange={(value) => setStartForm((current) => ({ ...current, temperatura_ingreso: value }))} />
              <InputField label="Peso momento servicio" type="number" value={startForm.peso_momento_servicio} onChange={(value) => setStartForm((current) => ({ ...current, peso_momento_servicio: value }))} />
              <InputField label="Raza/tamaño al ingreso" value={startForm.raza_tamano_momento} onChange={(value) => setStartForm((current) => ({ ...current, raza_tamano_momento: value }))} />
            </div>
            <label className="input-field">
              <span>Notas internas</span>
              <div className="input-wrapper">
                <textarea
                  rows={4}
                  value={startForm.notas_internas}
                  onChange={(event) => setStartForm((current) => ({ ...current, notas_internas: event.target.value }))}
                  style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
                />
              </div>
            </label>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Button type="button" onClick={handleStartService}>Iniciar servicio</Button>
            </div>
          </section>
        ) : null}

        {ficha ? (
          <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
            <h3 style={{ margin: 0 }}>Estado inicial</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
              <InputField label="Estado inicial" value={baseForm.estado_inicial} onChange={(value) => setBaseForm((current) => ({ ...current, estado_inicial: value }))} disabled={Boolean(ficha.fecha_cierre)} />
              <InputField label="Temperatura ingreso" type="number" value={baseForm.temperatura_ingreso} onChange={(value) => setBaseForm((current) => ({ ...current, temperatura_ingreso: value }))} disabled={Boolean(ficha.fecha_cierre)} />
              <InputField label="Peso momento servicio" type="number" value={baseForm.peso_momento_servicio} onChange={(value) => setBaseForm((current) => ({ ...current, peso_momento_servicio: value }))} disabled={Boolean(ficha.fecha_cierre)} />
              <InputField label="Raza/tamaño al ingreso" value={baseForm.raza_tamano_momento} onChange={(value) => setBaseForm((current) => ({ ...current, raza_tamano_momento: value }))} disabled={Boolean(ficha.fecha_cierre)} />
            </div>
            <label className="input-field">
              <span>Notas internas del groomer</span>
              <div className="input-wrapper">
                <textarea
                  rows={4}
                  value={baseForm.notas_internas}
                  disabled={Boolean(ficha.fecha_cierre)}
                  onChange={(event) => setBaseForm((current) => ({ ...current, notas_internas: event.target.value }))}
                  style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
                />
              </div>
            </label>
            {!ficha.fecha_cierre ? (
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Button type="button" onClick={handleSaveBase}>Guardar estado inicial</Button>
              </div>
            ) : null}
          </section>
        ) : null}

        {ficha ? (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 0.9fr)", gap: 18 }}>
            <div style={{ display: "grid", gap: 18 }}>
              <ChecklistPanel items={checklistItems} onToggle={handleToggleChecklist} disabled={Boolean(ficha.fecha_cierre)} />

              <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <h3 style={{ margin: 0 }}>Fotos</h3>
                    <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>
                      Antes: {fotosAntes.length} foto(s) | Después: {fotosDespues.length} foto(s)
                    </p>
                  </div>
                  {uploading ? <span className="pill">Subiendo...</span> : null}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                  <label
                    className="groomer-card"
                    style={{ padding: 14, display: "grid", gap: 10, cursor: "pointer" }}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => handleDropPhoto(event, "antes")}
                  >
                    <strong>Fotos Antes</strong>
                    <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleUploadPhoto(event, "antes")} />
                    <div style={{ minHeight: 120, borderRadius: 16, border: "1px dashed rgba(255,255,255,0.16)", padding: 10, display: "grid", gap: 8, placeItems: "center", textAlign: "center" }}>
                      {fotoPreviews.antes ? <img src={fotoPreviews.antes} alt="Vista previa antes" style={{ width: "100%", maxHeight: 160, objectFit: "cover", borderRadius: 14 }} /> : <span>Arrastra o clic para subir fotos antes</span>}
                    </div>
                    <div style={{ display: "grid", gap: 8 }}>
                      {fotosAntes.map((foto) => (
                        <div key={foto.id} style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                          <a href={foto.url} target="_blank" rel="noreferrer">Foto {foto.id}</a>
                          <button type="button" className="ghost-button" onClick={() => handleDeletePhoto(foto.id)}>×</button>
                        </div>
                      ))}
                    </div>
                  </label>
                  <label
                    className="groomer-card"
                    style={{ padding: 14, display: "grid", gap: 10, cursor: "pointer" }}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => handleDropPhoto(event, "despues")}
                  >
                    <strong>Fotos Después</strong>
                    <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleUploadPhoto(event, "despues")} />
                    <div style={{ minHeight: 120, borderRadius: 16, border: "1px dashed rgba(255,255,255,0.16)", padding: 10, display: "grid", gap: 8, placeItems: "center", textAlign: "center" }}>
                      {fotoPreviews.despues ? <img src={fotoPreviews.despues} alt="Vista previa después" style={{ width: "100%", maxHeight: 160, objectFit: "cover", borderRadius: 14 }} /> : <span>Arrastra o clic para subir fotos después</span>}
                    </div>
                    <div style={{ display: "grid", gap: 8 }}>
                      {fotosDespues.map((foto) => (
                        <div key={foto.id} style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                          <a href={foto.url} target="_blank" rel="noreferrer">Foto {foto.id}</a>
                          <button type="button" className="ghost-button" onClick={() => handleDeletePhoto(foto.id)}>×</button>
                        </div>
                      ))}
                    </div>
                  </label>
                </div>
              </section>

              <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <h3 style={{ margin: 0 }}>Insumos</h3>
                    <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>
                      Guarda la salida para que el stock se descuente al cerrar.
                    </p>
                  </div>
                </div>
                <PanelSalidaInsumos
                  fichaId={ficha.id}
                  servicioId={ficha?.cita?.servicio?.id}
                  fichaEstado={ficha?.cita?.estado_ficha}
                  readOnly={Boolean(ficha.fecha_cierre)}
                  onInsumosSaved={refreshFicha}
                />
              </section>
            </div>

            <aside style={{ display: "grid", gap: 18 }}>
              <section className="groomer-card" style={{ display: "grid", gap: 10 }}>
                <h3 style={{ margin: 0 }}>Datos de la ficha</h3>
                <div>Estado inicial: {ficha.estado_inicial || "-"}</div>
                <div>Temperatura ingreso: {ficha.temperatura_ingreso || "-"}</div>
                <div>Peso momento servicio: {ficha.peso_momento_servicio || "-"}</div>
                <div>Raza/tamaño momento: {ficha.raza_tamano_momento || "-"}</div>
                <div>Fecha cierre: {ficha.fecha_cierre || "Pendiente"}</div>
              </section>

              <section className="groomer-card" style={{ display: "grid", gap: 10 }}>
                <h3 style={{ margin: 0 }}>Cierre</h3>
                <Button
                  type="button"
                  onClick={() => setShowCloseModal(true)}
                  disabled={!estadoCierre?.puede_cerrar || estadoCierre?.loading}
                  title={estadoCierre?.loading ? "Verificando..." : closeTooltip}
                >
                  Cerrar servicio
                </Button>
                {!estadoCierre?.puede_cerrar && !estadoCierre?.loading ? (
                  <small style={{ color: "rgba(255,255,255,0.65)" }}>{closeTooltip}</small>
                ) : null}
                {estadoCierre?.razones_bloqueo && estadoCierre.razones_bloqueo.length ? (
                  <small style={{ color: "rgba(255,255,255,0.55)" }}>{estadoCierre.razones_bloqueo.join(" · ")}</small>
                ) : null}
              </section>
            </aside>
          </div>
        ) : null}
      </div>
      {showCloseModal && ficha ? (
        <ModalCierre
          ficha={ficha}
          onCerrado={() => {
            setShowCloseModal(false);
            navigate("/groomers/agenda");
          }}
          onCancelar={() => setShowCloseModal(false)}
        />
      ) : null}
    </div>
  );
}
