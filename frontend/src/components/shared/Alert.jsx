export default function Alert({ message, success = false }) {
  if (!message) return null;
  return (
    <div className={`alert${success ? " alert-success" : ""}`}>
      <span>!</span>
      <span>{message}</span>
    </div>
  );
}
