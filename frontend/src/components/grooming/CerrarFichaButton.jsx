import Button from "../shared/Button";

export default function CerrarFichaButton({ checklistItems, onClick, disabled }) {
  const pendientes = (checklistItems || []).filter((item) => !item.completado).length;
  const bloqueado = disabled || pendientes > 0 || (checklistItems || []).length === 0;
  const helperText = pendientes > 0
    ? `Completa ${pendientes} item(s) del checklist para habilitar el cierre.`
    : "Completa el checklist para habilitar el cierre.";

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <Button onClick={onClick} disabled={bloqueado}>
        Cerrar servicio
      </Button>
      {bloqueado && (
        <small style={{ color: "#6b6b6b" }}>
          {helperText}
        </small>
      )}
    </div>
  );
}
