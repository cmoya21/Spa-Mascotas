def mensaje_solicitud_revision(mascota_nombre, servicio_nombre, fecha, hora):
    return (
        f"Hola! Tu solicitud de cita para {mascota_nombre} "
        f"({servicio_nombre}) el {fecha} a las {hora} "
        f"está siendo revisada por recepción. "
        f"Te confirmaremos pronto. 🐾"
    )


def mensaje_cita_confirmada(mascota_nombre, servicio_nombre, fecha, hora, direccion=""):
    return (
        f"✅ ¡Cita confirmada! {mascota_nombre} tiene su cita de "
        f"{servicio_nombre} el {fecha} a las {hora}. "
        f"{('Dirección: ' + direccion) if direccion else ''} "
        f"¡Te esperamos! 🐾"
    )


def mensaje_recordatorio_24h(mascota_nombre, servicio_nombre, hora, direccion=""):
    return (
        f"⏰ Recordatorio: mañana a las {hora} tienes cita para "
        f"{mascota_nombre} ({servicio_nombre}). "
        f"{('Dirección: ' + direccion) if direccion else ''} "
        f"¡No olvides traer su carnet de vacunas! 🐾"
    )


def mensaje_recordatorio_2h(mascota_nombre, servicio_nombre, hora):
    return (
        f"🔔 En 2 horas ({hora}) tienes cita para {mascota_nombre} "
        f"({servicio_nombre}). ¡Nos vemos pronto! 🐾"
    )


def mensaje_listo_recoger(mascota_nombre, servicio_nombre):
    return (
        f"🎉 ¡{mascota_nombre} está lista para ser recogida! "
        f"El servicio de {servicio_nombre} finalizó exitosamente. "
        f"Puedes pasar a recogerla cuando gustes. ¡Quedó hermosa/o! 🐾"
    )


def mensaje_bajo_stock(producto_nombre, stock_actual, stock_minimo):
    return (
        f"⚠️ ALERTA: El producto \"{producto_nombre}\" está por debajo "
        f"del mínimo. Stock actual: {stock_actual} / Mínimo: {stock_minimo}. "
        f"Se recomienda reabastecer a la brevedad."
    )


def mensaje_pago_registrado(mascota_nombre, servicio_nombre, total, metodo, numero_factura):
    return (
        f"✅ Pago registrado. {mascota_nombre} - {servicio_nombre}. "
        f"Total: Bs.{total:.2f} ({metodo}). "
        f"Factura: {numero_factura}. "
        f"¡Gracias por confiar en nosotros! 🐾"
    )
