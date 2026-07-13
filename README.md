# ☕ Cafetería Adulam — Mi Refugio

Sistema de pedidos tipo PWA para cafetería, pensado para que los clientes ordenen desde su asiento y el staff gestione todo desde un panel de administración en tiempo real.

** Demo en vivo:** [adulam.pythonanywhere.com](https://adulam.pythonanywhere.com/)

> Nombre interno del proyecto: `Cafetería Adulam`. Nombre de cara al cliente en las plantillas: **"Mi Refugio"**.

---

##  Características

- **Pedido desde el asiento** — el cliente ingresa su nombre y número de asiento, arma su pedido desde el menú y lo envía sin necesidad de mesero.
- **Menú con precios duales** — productos con precio único o con precio diferenciado grande/chico.
- **Personalización de productos** — sabor, tipo de leche, nivel de hielo, azúcar y café configurables por producto.
- **Estado de pedido en tiempo real** — el cliente ve si su pedido está *pendiente*, *en preparación* o *entregado*, con polling automático.
- **Panel de administración**:
  - Gestión de pedidos activos con notificación sonora de nuevos pedidos.
  - CRUD de productos y opciones (sabores, leches) con activación/desactivación por falta de stock.
  - **Arqueo de caja** diario: ventas, número de pedidos, promedio, producto más vendido, historial filtrable por días de evento.
  - Edición/cancelación de pedidos con separación de roles (cliente vs. admin); pedidos en preparación quedan bloqueados.
  - Mapa interactivo de asientos (vista normal y vista de mesas interiores).
  - Activar/desactivar la app completa con mensaje personalizado para los usuarios.
- **PWA instalable** — service worker, manifest e iconos para instalación en el celular; funciona con pantalla de "app inactiva" cuando el negocio está cerrado.
- **Guía de asientos visual** en el login, con tooltips y zonas especiales (mostrador, mesas laterales, zona multimedia, mesas interiores).

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python 3 / Flask |
| Base de datos | SQLite (`cafe.db`) |
| Plantillas | Jinja2 |
| Frontend | HTML + CSS + JavaScript vanilla |
| PWA | Service Worker + Web App Manifest |
| Hosting | PythonAnywhere (plan gratuito) |

---

## Estructura del proyecto

```
.
├── app.py                     # Backend Flask: rutas, lógica de negocio, migraciones de DB
├── generador_qr.py            # Utilidad para generar el código QR de acceso
├── requirements.txt
├── cafe.db                    # Base de datos SQLite (se crea/migra automáticamente)
├── templates/
│   ├── login.html             # Pantalla de acceso + guía de asientos
│   ├── panel.html             # Menú y armado de pedido del cliente
│   ├── pedido_exitoso.html    # Seguimiento de estado del pedido
│   ├── admin.html             # Panel de administración (pedidos, productos, opciones, arqueo, asientos, config)
│   └── reactivar.html         # Reactivación de emergencia de la app
└── static/
    ├── style.css
    ├── manifest.json
    └── sw.js                  # Service worker (cache de assets estáticos, network-first para rutas Flask)
```

---

## Instalación local

### Requisitos
- Python 3.10+ (desarrollado con Python 3.14)
- pip

### Pasos

```bash
git clone https://github.com/<tu-usuario>/<tu-repo>.git
cd <tu-repo>

python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac

pip install -r requirements.txt

python app.py
```

La app quedará disponible en `http://localhost:5000`. La base de datos (`cafe.db`) y su esquema se crean y migran automáticamente al iniciar (`init_db()` y `migrate_db()`).

---

## Acceso de administrador

El login de administrador usa las mismas casillas de "nombre" y "asiento" que un cliente normal.


La sesión de administrador persiste por 7 días una vez iniciada.

También existe una ruta `/reactivar` con una clave de emergencia (`CLAVE_REACTIVAR` en `app.py`) para reactivar la app y recuperar sesión de admin sin pasar por el login normal.

---

##  Notas de diseño

- El sistema usa `precio_grande` / `precio_chico` para productos con tamaños; si `precio_chico` es `NULL`, el producto tiene precio único.
- Categorías del menú: `Caliente`, `Frío`, `Frappé`, `Smoothie`, `Snack`, `Otro`.
- El arqueo diario descuenta cancelaciones hechas por el administrador, pero no las hechas por el cliente.
- Los pedidos en estado `preparando` no pueden ser editados ni cancelados por nadie.

---

## Licencia

Proyecto de uso privado para Cafetería Adulam.
