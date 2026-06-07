export default function InventoryAlertBadge({ count }) {
  if (!count) {
    return null;
  }

  return (
    <span
      style={{
        background: "#f6c343",
        color: "#2b2b2b",
        borderRadius: 999,
        padding: "2px 10px",
        fontSize: 12,
        fontWeight: 600
      }}
    >
      {count} alertas
    </span>
  );
}
