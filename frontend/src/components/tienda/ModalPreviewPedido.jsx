const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

export default function ModalPreviewPedido({ pedido, onConfirmar, onCancelar }) {
  if (!pedido) return null;

  const handleConfirmar = () => {
    if (pedido.link_whatsapp) {
      window.open(pedido.link_whatsapp, "_blank", "noopener,noreferrer");
    }
    onConfirmar?.();
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 70 }}>
      <div className="pedido-preview-modal">
        <div className="modal-header">
          <div>
            <p className="calendar-kicker">Vista previa de tu pedido</p>
            <h3 style={{ margin: 0 }}>Revisa el mensaje antes de abrir WhatsApp</h3>
          </div>
          <button type="button" className="ghost-button" onClick={onCancelar}>
            Cerrar
          </button>
        </div>

        <div className="pedido-preview-box">
          <pre>{pedido.mensaje_preview}</pre>
        </div>

        <div className="pedido-preview-summary">
          <strong>Subtotal</strong>
          <strong>{money(pedido.subtotal)}</strong>
        </div>

        {pedido.total !== undefined ? (
          <div className="pedido-preview-summary">
            <strong>Total</strong>
            <strong>{money(pedido.total)}</strong>
          </div>
        ) : null}

        <div className="pedido-preview-actions">
          <button type="button" className="ghost-button" onClick={onCancelar}>
            ← Modificar carrito
          </button>
          <button type="button" className="primary-button" onClick={handleConfirmar}>
            ✓ Abrir WhatsApp y confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
