export default function ChecklistPanel({ items, onToggle, disabled = false }) {
  const total = items.length;
  const completed = items.filter((item) => item.completado).length;
  const progress = total ? Math.round((completed / total) * 100) : 0;

  return (
    <section className="groomer-card" style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h3 style={{ margin: 0 }}>Checklist obligatorio</h3>
          <p style={{ margin: "6px 0 0", color: "rgba(255,255,255,0.68)" }}>
            {completed} / {total} ítems completados.
          </p>
        </div>
        <div className="pill">{progress}%</div>
      </div>

      <div style={{ height: 10, borderRadius: 999, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
        <div style={{ width: `${progress}%`, height: "100%", background: "linear-gradient(90deg, #5aa7ff, #5ad7a0)" }} />
      </div>

      <div style={{ display: "grid", gap: 10 }}>
        {items.length ? items.map((item) => (
          <article key={item.id} style={{ borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <label style={{ display: "flex", gap: 12, alignItems: "start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={item.completado}
                disabled={disabled || (item.requiere_obs && !item.completado && !(item.observacion || "").trim())}
                onChange={(event) => onToggle?.(item, event.target.checked)}
                style={{ marginTop: 3 }}
              />
              <div style={{ display: "grid", gap: 8, width: "100%" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <strong>{item.orden ? `${item.orden}. ${item.nombre}` : item.nombre}</strong>
                  {item.requiere_obs ? <span className="pill">Requiere obs</span> : null}
                </div>
                {item.requiere_obs ? (
                  <textarea
                    value={item.observacion || ""}
                    disabled={disabled}
                    onChange={(event) => onToggle?.(item, item.completado, event.target.value)}
                    rows={3}
                    placeholder="Observación obligatoria"
                    style={{ width: "100%", resize: "vertical", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)", color: "inherit", padding: 10 }}
                  />
                ) : null}
                {item.completado_en ? <small style={{ color: "rgba(255,255,255,0.65)" }}>✓ {new Date(item.completado_en).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small> : null}
              </div>
            </label>
          </article>
        )) : <div className="admin-empty">No hay ítems de checklist para este servicio.</div>}
      </div>
    </section>
  );
}
