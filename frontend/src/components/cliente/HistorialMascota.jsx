import { useEffect, useState } from "react";

import { apiGetHistorialMascota, apiResponderEncuestaCita } from "../../api/clienteApi.js";
import Button from "../shared/Button";

const EMPTY_SURVEY = { calificacion: "5", nps: "8", comentario: "" };

export default function HistorialMascota({ mascotaId, refreshToken }) {
  const [historial, setHistorial] = useState([]);
  const [mascota, setMascota] = useState(null);
  const [error, setError] = useState("");
  const [surveyState, setSurveyState] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!mascotaId) {
      setHistorial([]);
      setMascota(null);
      return;
    }
    let active = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await apiGetHistorialMascota(mascotaId);
        if (!active) return;
        setMascota(data.mascota || null);
        setHistorial(data.historial || []);
      } catch (err) {
        if (active) {
          setError("No se pudo cargar el historial de la mascota.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [mascotaId, refreshToken]);

  const updateSurvey = (citaId, key, value) => {
    setSurveyState((current) => ({
      ...current,
      [citaId]: { ...(current[citaId] || EMPTY_SURVEY), [key]: value },
    }));
  };

  const submitSurvey = async (citaId) => {
    const survey = surveyState[citaId] || EMPTY_SURVEY;
    await apiResponderEncuestaCita(citaId, {
      calificacion: Number(survey.calificacion),
      nps: Number(survey.nps),
      comentario: survey.comentario,
    });
    setSurveyState((current) => ({ ...current, [citaId]: EMPTY_SURVEY }));
    const data = await apiGetHistorialMascota(mascotaId);
    setMascota(data.mascota || null);
    setHistorial(data.historial || []);
  };

  if (!mascotaId) {
    return <div className="admin-empty">Selecciona una mascota para ver su historial.</div>;
  }

  return (
    <section className="cliente-card" style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>Historial de {mascota?.nombre || "la mascota"}</h3>
          <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.7)" }}>
            Citas, vacunas y novedades.
          </p>
        </div>
        {loading ? <span className="pill">Cargando...</span> : null}
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <div style={{ display: "grid", gap: 12 }}>
        {!historial.length ? <div className="admin-empty">Sin registros aún.</div> : null}
        {historial.map((item) => (
          <article
            key={`${item.tipo}-${item.id}`}
            style={{
              borderRadius: 18,
              padding: 16,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 8 }}>
              <strong>{item.titulo}</strong>
              <span>{item.fecha ? new Date(item.fecha).toLocaleString() : "Sin fecha"}</span>
            </div>
            <div style={{ color: "rgba(255,255,255,0.75)", marginBottom: 8 }}>
              {item.tipo === "cita" ? `Estado: ${item.estado || "-"}` : item.tipo === "vacuna" ? "Vacuna registrada" : "Notificación"}
            </div>
            {item.detalle ? <div style={{ marginBottom: 10 }}>{item.detalle}</div> : null}

            {item.tipo === "cita" && item.estado === "completada" && !item.tiene_encuesta ? (
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10 }}>
                  <label className="input-field">
                    <span>Calificación</span>
                    <div className="input-wrapper">
                      <input
                        type="number"
                        min="1"
                        max="5"
                        value={(surveyState[item.id] || EMPTY_SURVEY).calificacion}
                        onChange={(event) => updateSurvey(item.id, "calificacion", event.target.value)}
                      />
                    </div>
                  </label>
                  <label className="input-field">
                    <span>NPS</span>
                    <div className="input-wrapper">
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={(surveyState[item.id] || EMPTY_SURVEY).nps}
                        onChange={(event) => updateSurvey(item.id, "nps", event.target.value)}
                      />
                    </div>
                  </label>
                </div>
                <label className="input-field">
                  <span>Comentario</span>
                  <div className="input-wrapper">
                    <textarea
                      rows={3}
                      value={(surveyState[item.id] || EMPTY_SURVEY).comentario}
                      onChange={(event) => updateSurvey(item.id, "comentario", event.target.value)}
                      style={{ width: "100%", resize: "vertical", border: "none", background: "transparent", outline: "none" }}
                    />
                  </div>
                </label>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <Button type="button" onClick={() => submitSurvey(item.id)}>
                    Enviar encuesta
                  </Button>
                </div>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
