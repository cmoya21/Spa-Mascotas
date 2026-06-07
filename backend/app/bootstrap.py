from __future__ import annotations

from sqlalchemy import inspect

from .extensions import db
from .models import CategoriaProducto, Producto, VarianteProducto


_CATALOGO_BASE = [
    {
        "categoria": {"nombre": "Alimentos", "descripcion": "Comida seca, húmeda y snacks"},
        "productos": [
            {
                "nombre": "Alimento Premium Adulto 1kg",
                "descripcion": "Croquetas premium con proteína de pollo",
                "sku": "ALI-PREM-1KG",
                "precio_base": 85.0,
                "stock": 15,
                "stock_minimo": 3,
                "variantes": [
                    {"atributo": "Peso", "valor": "2kg", "precio_extra": 60.0, "stock": 10, "sku_variante": "ALI-PREM-2KG"},
                    {"atributo": "Peso", "valor": "5kg", "precio_extra": 180.0, "stock": 5, "sku_variante": "ALI-PREM-5KG"},
                ],
            },
        ],
    },
    {
        "categoria": {"nombre": "Accesorios", "descripcion": "Collares, correas, ropa y accesorios"},
        "productos": [
            {
                "nombre": "Collar Ajustable Mediano",
                "descripcion": "Collar de nylon ajustable para razas medianas",
                "sku": "ACC-COLL-MED",
                "precio_base": 25.0,
                "stock": 30,
                "stock_minimo": 10,
            },
        ],
    },
    {
        "categoria": {"nombre": "Higiene", "descripcion": "Shampoos, cepillos, cortaúñas y desodorantes"},
        "productos": [
            {
                "nombre": "Shampoo Hipoalergénico 500ml",
                "descripcion": "Shampoo suave sin fragancia para pieles sensibles",
                "sku": "SHP-HIPOAL-500",
                "precio_base": 35.0,
                "stock": 20,
                "stock_minimo": 5,
            },
        ],
    },
    {
        "categoria": {"nombre": "Juguetes", "descripcion": "Pelotas, cuerdas y juguetes interactivos"},
        "productos": [
            {
                "nombre": "Pelota Interactiva",
                "descripcion": "Pelota de goma resistente con sonido",
                "sku": "JUG-PELOTA-01",
                "precio_base": 18.0,
                "stock": 25,
                "stock_minimo": 8,
            },
        ],
    },
    {
        "categoria": {"nombre": "Salud", "descripcion": "Antiparasitarios, vitaminas y medicamentos OTC"},
        "productos": [
            {
                "nombre": "Antiparasitario Pipeta",
                "descripcion": "Pipeta antiparasitaria para perros hasta 25kg",
                "sku": "SAL-ANTI-PIP",
                "precio_base": 45.0,
                "stock": 12,
                "stock_minimo": 4,
            },
        ],
    },
]


_def_catalogo_seeded = False


def _db_ready() -> bool:
    try:
        inspector = inspect(db.engine)
        return inspector.has_table("categorias_producto") and inspector.has_table("productos")
    except Exception:
        return False


def seed_catalogo_basico():
    global _def_catalogo_seeded
    if _def_catalogo_seeded or not _db_ready():
        return

    if CategoriaProducto.query.count() > 0 or Producto.query.count() > 0:
        _def_catalogo_seeded = True
        return

    categorias_por_nombre = {}
    for item in _CATALOGO_BASE:
        categoria = CategoriaProducto.query.filter_by(nombre=item["categoria"]["nombre"]).first()
        if not categoria:
            categoria = CategoriaProducto(**item["categoria"])
            db.session.add(categoria)
            db.session.flush()
        categorias_por_nombre[categoria.nombre] = categoria

    for item in _CATALOGO_BASE:
        categoria = categorias_por_nombre[item["categoria"]["nombre"]]
        for producto_data in item["productos"]:
            producto = Producto.query.filter_by(sku=producto_data["sku"]).first()
            if not producto:
                producto = Producto(
                    nombre=producto_data["nombre"],
                    descripcion=producto_data.get("descripcion"),
                    sku=producto_data["sku"],
                    precio_base=producto_data["precio_base"],
                    stock=producto_data["stock"],
                    stock_minimo=producto_data["stock_minimo"],
                    activo=True,
                    categoria_id=categoria.id,
                )
                db.session.add(producto)
                db.session.flush()
            else:
                producto.categoria_id = categoria.id
            for variante_data in producto_data.get("variantes", []):
                variante = VarianteProducto.query.filter_by(sku_variante=variante_data["sku_variante"]).first()
                if not variante:
                    db.session.add(
                        VarianteProducto(
                            producto_id=producto.id,
                            atributo=variante_data["atributo"],
                            valor=variante_data["valor"],
                            precio_extra=variante_data["precio_extra"],
                            stock=variante_data["stock"],
                            sku_variante=variante_data["sku_variante"],
                        )
                    )
    db.session.commit()
    _def_catalogo_seeded = True
