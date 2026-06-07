import { useEffect, useMemo, useState } from "react";

import ModalPreviewPedido from "./ModalPreviewPedido.jsx";
import {
  apiActualizarItemCarrito,
  apiEliminarItemCarrito,
  apiGenerarPedidoWhatsApp,
  apiGetCarritoMe,
  apiVaciarCarrito,
} from "../../api/tiendaApi";
import { apiValidarCupon } from "../../api/promocionesApi";

const money = (value) => `Bs. ${Number(value || 0).toFixed(2)}`;

export default function CarritoDrawer({ abierto, onCerrar, onCarritoActualizado, onToast, refreshToken = 0 }) {
  const [carrito, setCarrito] = useState(null);
  const [generando, setGenerando] = useState(false);
  const [preview, setPreview] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [cupon, setCupon] = useState("");
  const [descuentoAplicado, setDescuentoAplicado] = useState(null);
  const [validandoCupon, setValidandoCupon] = useState(false);

  const items = carrito?.items || [];
  const subtotal = useMemo(() => Number(carrito?.subtotal || 0), [carrito]);
  const totalConDescuento = useMemo(() => {
    if (!descuentoAplicado) return subtotal;
    return Math.max(0, Number(descuentoAplicado.total_con_descuento || subtotal));
  }, [descuentoAplicado, subtotal]);

  const sincronizar = async () => {
    if (!abierto) return;
    setCargando(true);
    try {
      const data = await apiGetCarritoMe();
      setCarrito(data);
      if (descuentoAplicado?.subtotal_original !== undefined && Number(descuentoAplicado.subtotal_original) !== Number(data.subtotal || 0)) {
        setDescuentoAplicado(null);
        setCupon("");
      }
      onCarritoActualizado?.(data.total_items || 0);
    } catch {
      setCarrito(null);
      onCarritoActualizado?.(0);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    if (abierto) {
      sincronizar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, refreshToken]);

  const actualizarCantidad = async (item, nuevaCantidad) => {
    try {
      if (nuevaCantidad <= 0) {
        await apiEliminarItemCarrito(item.id);
      } else {
        await apiActualizarItemCarrito(item.id, { cantidad: nuevaCantidad });
      }
      await sincronizar();
    } catch (error) {
      onToast?.(error?.response?.data?.message || "No se pudo actualizar el carrito.");
    }
  };

  const vaciarCarrito = async () => {
    try {
      await apiVaciarCarrito();
      setCarrito((prev) => (prev ? { ...prev, items: [], total_items: 0, subtotal: 0 } : prev));
      setDescuentoAplicado(null);
      setCupon("");
      onCarritoActualizado?.(0);
      onToast?.("Carrito vaciado");
    } catch (error) {
      onToast?.(error?.response?.data?.message || "No se pudo vaciar el carrito.");
    }
  };

  const generarWhatsApp = async () => {
    setGenerando(true);
    try {
      const data = await apiGenerarPedidoWhatsApp(
        descuentoAplicado?.promocion_id ? { promocion_id: descuentoAplicado.promocion_id } : {}
      );
      setPreview(data);
    } catch (error) {
      onToast?.(error?.response?.data?.message || "No se pudo generar el pedido.");
    } finally {
      setGenerando(false);
    }
  };

  const generarTelegram = async () => {
    setGenerando(true);
    try {
      const data = await apiGenerarPedidoWhatsApp(
        descuentoAplicado?.promocion_id ? { promocion_id: descuentoAplicado.promocion_id } : {}
      );
      if (data.link_telegram) {
        window.open(data.link_telegram, "_blank", "noopener,noreferrer");
        onToast?.("¡Pedido enviado! Continúa en Telegram.");
      } else {
        onToast?.("Telegram no está configurado.");
      }
    } catch (error) {
      onToast?.(error?.response?.data?.message || "No se pudo generar el pedido.");
    } finally {
      setGenerando(false);
    }
  };

  const handleConfirmarPreview = () => {
    setPreview(null);
    setCarrito((prev) => (prev ? { ...prev, items: [], total_items: 0, subtotal: 0 } : prev));
    setDescuentoAplicado(null);
    setCupon("");
    onToast?.("¡Pedido enviado! Continúa en WhatsApp.");
  };

  const aplicarCupon = async () => {
    if (!cupon.trim()) {
      onToast?.("Escribe un código de cupón.");
      return;
    }
    setValidandoCupon(true);
    try {
      const data = await apiValidarCupon({ codigo_cupon: cupon.trim(), subtotal });
      setDescuentoAplicado(data);
      onToast?.(`Cupón ${cupon.trim()} aplicado`);
    } catch (error) {
      setDescuentoAplicado(null);
      const message = error?.response?.status === 404 || error?.response?.status === 422
        ? (error?.response?.data?.message || "Código inválido o vencido")
        : (error?.response?.data?.message || "No se pudo validar el cupón");
      onToast?.(message);
    } finally {
      setValidandoCupon(false);
    }
  };

  if (!abierto) return null;

  return (
    <div className="carrito-drawer-overlay">
      <aside className="carrito-drawer">
        <div className="carrito-drawer-header">
          <div>
            <p className="calendar-kicker">Carrito de compras</p>
            <h3>Tu pedido</h3>
          </div>
          <button type="button" className="ghost-button" onClick={onCerrar}>
            Cerrar
          </button>
        </div>

        {cargando ? <div className="admin-empty">Cargando carrito...</div> : null}

        {!items.length && !cargando ? (
          <div className="empty-cart">
            <div className="empty-cart-emoji">🛒</div>
            <h4>Tu carrito está vacío</h4>
            <p>Agrega productos desde el catálogo para continuar con tu pedido.</p>
            <button type="button" className="primary-button" onClick={onCerrar}>
              Ver productos
            </button>
          </div>
        ) : null}

        {items.length ? (
          <div className="carrito-items">
            {items.map((item) => (
              <article key={item.id} className="carrito-item">
                <div className="carrito-item-image">
                  {item.imagen_url ? <img src={item.imagen_url} alt={item.nombre} /> : <span>🧴</span>}
                </div>
                <div className="carrito-item-body">
                  <div className="carrito-item-head">
                    <div>
                      <strong>{item.nombre}</strong>
                      {item.variante_label ? <p>{item.variante_label}</p> : null}
                    </div>
                    <button type="button" className="ghost-button danger" onClick={() => actualizarCantidad(item, 0)}>
                      🗑
                    </button>
                  </div>
                  <div className="carrito-item-meta">
                    <span>{money(item.precio_unitario)} x {item.cantidad}</span>
                    <strong>{money(item.subtotal)}</strong>
                  </div>
                  <div className="carrito-item-actions">
                    <button type="button" className="ghost-button" onClick={() => actualizarCantidad(item, item.cantidad - 1)}>
                      −
                    </button>
                    <span className="carrito-qty">{item.cantidad}</span>
                    <button type="button" className="ghost-button" onClick={() => actualizarCantidad(item, item.cantidad + 1)}>
                      +
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {items.length ? (
          <>
            <div className="carrito-summary">
              <span>Subtotal</span>
              <strong>{money(subtotal)}</strong>
            </div>

            <div className="cupon-box">
              <label className="cupon-label">Código de descuento (opcional)</label>
              <div className="cupon-row">
                <input
                  type="text"
                  value={cupon}
                  onChange={(event) => setCupon(event.target.value)}
                  placeholder="PROMO20"
                />
                <button type="button" className="ghost-button" onClick={aplicarCupon} disabled={validandoCupon}>
                  {validandoCupon ? "Validando..." : "Aplicar"}
                </button>
              </div>
              {descuentoAplicado ? (
                <div className="cupon-aplicado">
                  <div>✓ Cupón "{cupon.trim()}" aplicado</div>
                  <div>Descuento: -{money(descuentoAplicado.descuento_calculado)}</div>
                </div>
              ) : null}
            </div>

            {descuentoAplicado ? (
              <div className="carrito-summary stack">
                <div><span>Subtotal</span><strong>{money(subtotal)}</strong></div>
                <div><span>Descuento ({cupon.trim()})</span><strong>-{money(descuentoAplicado.descuento_calculado)}</strong></div>
                <div><span>TOTAL</span><strong>{money(totalConDescuento)}</strong></div>
              </div>
            ) : null}

            {!descuentoAplicado ? (
              <div className="carrito-summary">
                <span>TOTAL</span>
                <strong>{money(subtotal)}</strong>
              </div>
            ) : null}

            <button type="button" className="ghost-button danger subtle" onClick={vaciarCarrito}>
              🗑 Vaciar carrito
            </button>

            <div className="carrito-send-block">
              <h4>¿Cómo quieres enviar tu pedido?</h4>
              <button type="button" className="primary-button whatsapp-button" onClick={generarWhatsApp} disabled={generando}>
                {generando ? "Generando..." : "📱 Enviar por WhatsApp"}
              </button>
              {preview?.link_telegram || preview?.mensaje_preview ? (
                <button type="button" className="ghost-button telegram-button" onClick={generarTelegram} disabled={generando}>
                  ✈ Enviar por Telegram
                </button>
              ) : (
                <button type="button" className="ghost-button telegram-button" onClick={generarTelegram} disabled={generando}>
                  ✈ Enviar por Telegram
                </button>
              )}
            </div>
          </>
        ) : null}
      </aside>

      <ModalPreviewPedido pedido={preview} onConfirmar={handleConfirmarPreview} onCancelar={() => setPreview(null)} />
    </div>
  );
}
