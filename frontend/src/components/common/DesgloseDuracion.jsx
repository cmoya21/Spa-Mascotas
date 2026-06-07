import { calcularDuracion } from "../../utils/calcularDuracion";

export default function DesgloseDuracion({ servicio, mascota }) {
  if (!servicio || !mascota) return null;

  const r = calcularDuracion(
    servicio.duracion_base_minutos,
    mascota.peso_kg,
    mascota.temperamento,
    servicio.factor_tamano_raza
  );

  const hayAjuste = r.duracionFinal !== r.duracionBase;

  return (
    <div
      style={{
        background: "var(--color-background-secondary)",
        borderLeft: `3px solid ${hayAjuste ? "#EF9F27" : "#1D9E75"}`,
        borderRadius: "0 6px 6px 0",
        padding: "10px 14px",
        marginTop: "8px",
        fontSize: "13px"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-secondary)", marginBottom: "4px" }}>
        <span>Duración base del servicio</span>
        <span><b>{r.duracionBase} min</b></span>
      </div>
      {r.minutosPorTamano > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-secondary)", marginBottom: "4px" }}>
          <span>+ Ajuste por tamaño ({r.categoriaLabel})</span>
          <span><b>+{r.minutosPorTamano} min</b></span>
        </div>
      )}
      {r.extraTemperamento > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-secondary)", marginBottom: "4px" }}>
          <span>+ Ajuste por temperamento ({r.temperamento})</span>
          <span><b>+{r.extraTemperamento} min</b></span>
        </div>
      )}
      <div style={{ borderTop: "0.5px solid var(--color-border-tertiary)", marginTop: "6px", paddingTop: "6px", display: "flex", justifyContent: "space-between" }}>
        <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>⏱ Duración total estimada</span>
        <span style={{ fontWeight: 500, color: hayAjuste ? "#BA7517" : "#1D9E75" }}>{r.duracionFinal} min</span>
      </div>
      {hayAjuste && (
        <p style={{ fontSize: "11px", color: "#BA7517", margin: "6px 0 0" }}>
          ⚠ El tiempo se ajustó por las características de {mascota.nombre}. Se buscará un slot de {r.duracionFinal} min.
        </p>
      )}
    </div>
  );
}
