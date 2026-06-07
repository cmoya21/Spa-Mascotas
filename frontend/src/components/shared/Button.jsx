export default function Button({ children, onClick, disabled, loading }) {
  return (
    <button className="primary-button" onClick={onClick} disabled={disabled || loading}>
      {loading ? (
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="spinner" /> Iniciando sesión...
        </span>
      ) : (
        children
      )}
    </button>
  );
}
