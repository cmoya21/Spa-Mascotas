from .auth import auth_bp
from .admin import admin_bp
from .agenda import agenda_bp
from .mascotas import mascotas_bp
from .grooming import grooming_bp
from .notificaciones import notificaciones_bp
from .insumos import insumos_bp, productos_insumos_bp
from .inventario import inventario_bp
from .pagos import pagos_bp
from .citas import citas_bp
from .clientes import clientes_bp
from .pedidos import pedidos_bp
from .alertas import alertas_bp
from .cobros import cobros_bp
from .disponibilidad import disponibilidad_bp
from .servicios import servicios_bp
from .groomers import groomers_bp, fichas_bp
from .reportes import reportes_bp
from .promociones import promociones_bp
from .encuestas import encuestas_bp
from .tienda import tienda_bp
from .usuarios import usuarios_bp

__all__ = [
	"auth_bp",
	"admin_bp",
	"agenda_bp",
	"mascotas_bp",
	"grooming_bp",
	"notificaciones_bp",
	"insumos_bp",
	"productos_insumos_bp",
	"inventario_bp",
	"pagos_bp",
	"citas_bp",
	"clientes_bp",
	"pedidos_bp",
	"alertas_bp",
	"cobros_bp",
	"disponibilidad_bp",
	"servicios_bp",
	"groomers_bp",
	"fichas_bp",
	"reportes_bp",
	"promociones_bp",
	"encuestas_bp",
	"tienda_bp",
	"usuarios_bp",
]
