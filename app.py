import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
import re
import sqlite3
from datetime import datetime, date, timedelta

def get_db_connection():
    conn = sqlite3.connect("cafe.db")
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)

# La clave secreta se toma de una variable de entorno.
# En PythonAnywhere se configura en el archivo WSGI o en un .env (ver guía).
app.secret_key = os.environ.get("SECRET_KEY", "cafe_adulam_secret_key")

# La sesion de admin dura 7 dias sin necesidad de volver a iniciar sesion
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

ADMIN_NAME = "admin"
ADMIN_SEAT = "admin"

# Clave de emergencia para reactivar la app desde /reactivar sin sesion activa
CLAVE_REACTIVAR = os.environ.get("CLAVE_REACTIVAR", "adulam2026")

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')


# --- MIGRACION DB -----------------------------------------------------------

def migrate_db():
    conn = sqlite3.connect("cafe.db")

    cols_pedidos = [r[1] for r in conn.execute("PRAGMA table_info(pedidos)").fetchall()]
    if "detalles" not in cols_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN detalles TEXT")
    if "total" not in cols_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN total REAL DEFAULT 0")
    # Estado del pedido: pendiente / preparando / completado
    if "estado" not in cols_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN estado TEXT DEFAULT 'pendiente'")

    # Columna para ocultar registros del historial sin borrarlos
    tablas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "arqueo" in tablas:
        cols_arqueo = [r[1] for r in conn.execute("PRAGMA table_info(arqueo)").fetchall()]
        if "oculto" not in cols_arqueo:
            conn.execute("ALTER TABLE arqueo ADD COLUMN oculto INTEGER DEFAULT 0")

    tablas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "productos" in tablas:
        cols_prod = [r[1] for r in conn.execute("PRAGMA table_info(productos)").fetchall()]
        if "tiene_hielo" not in cols_prod:
            conn.execute("ALTER TABLE productos ADD COLUMN tiene_hielo INTEGER DEFAULT 1")
        if "tiene_azucar" not in cols_prod:
            conn.execute("ALTER TABLE productos ADD COLUMN tiene_azucar INTEGER DEFAULT 1")
        if "tiene_cafe" not in cols_prod:
            conn.execute("ALTER TABLE productos ADD COLUMN tiene_cafe INTEGER DEFAULT 0")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT DEFAULT 'Bebida',
            tiene_sabores INTEGER DEFAULT 0,
            tiene_leche INTEGER DEFAULT 0,
            tiene_hielo INTEGER DEFAULT 1,
            tiene_azucar INTEGER DEFAULT 1,
            tiene_cafe INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS opciones_producto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor TEXT NOT NULL,
            disponible INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS arqueo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL UNIQUE,
            total_ventas REAL DEFAULT 0,
            num_pedidos INTEGER DEFAULT 0,
            notas TEXT,
            cerrado INTEGER DEFAULT 0,
            oculto INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
    """)
    # Valores por defecto de configuracion si no existen
    conn.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('app_activa', '1')")
    conn.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES ('mensaje_inactiva', '')")
    conn.commit()
    conn.close()


# --- INIT DB ----------------------------------------------------------------

def init_db():
    conn = sqlite3.connect("cafe.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            asiento TEXT NOT NULL,
            articulos TEXT NOT NULL,
            detalles TEXT,
            total REAL DEFAULT 0,
            estado TEXT DEFAULT 'pendiente',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT DEFAULT 'Bebida',
            tiene_sabores INTEGER DEFAULT 0,
            tiene_leche INTEGER DEFAULT 0,
            tiene_hielo INTEGER DEFAULT 1,
            tiene_azucar INTEGER DEFAULT 1,
            tiene_cafe INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS opciones_producto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor TEXT NOT NULL,
            disponible INTEGER DEFAULT 1,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        );
        CREATE TABLE IF NOT EXISTS arqueo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL UNIQUE,
            total_ventas REAL DEFAULT 0,
            num_pedidos INTEGER DEFAULT 0,
            notas TEXT,
            cerrado INTEGER DEFAULT 0,
            oculto INTEGER DEFAULT 0
        );
    """)

    count = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO productos (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar) VALUES ('Café frío', 20, 'Café', 0, 1, 1, 1)")
        conn.execute("INSERT INTO productos (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar) VALUES ('Smoothie de frutos rojos', 35, 'Smoothie', 1, 0, 1, 1)")
        conn.execute("INSERT INTO productos (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar) VALUES ('Frappé de café', 30, 'Café', 0, 1, 1, 1)")
        conn.execute("INSERT INTO productos (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar) VALUES ('Empanada', 25, 'Snack', 0, 0, 0, 0)")
        conn.commit()

        conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (2, 'sabor', 'Frutos rojos')")
        conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (2, 'sabor', 'Mango')")
        conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (2, 'sabor', 'Fresa')")
        conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (2, 'sabor', 'Durazno')")
        for pid in [1, 3]:
            conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, 'leche', 'Entera')", (pid,))
            conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, 'leche', 'Deslactosada')", (pid,))
            conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, 'leche', 'De almendra')", (pid,))
        conn.commit()

    conn.close()


# --- HELPER CONFIG ----------------------------------------------------------

def get_config(clave, default=''):
    conn = get_db_connection()
    row = conn.execute("SELECT valor FROM config WHERE clave = ?", (clave,)).fetchone()
    conn.close()
    return row["valor"] if row else default


# --- RUTAS PUBLICAS ---------------------------------------------------------

@app.route("/")
def home():
    app_activa    = get_config('app_activa', '1') == '1'
    mensaje       = get_config('mensaje_inactiva', '')
    return render_template("login.html", app_activa=app_activa, mensaje_inactiva=mensaje)


@app.route("/login", methods=["POST"])
def login():
    # Bloquear acceso si la app esta desactivada (excepto al admin)
    nombre  = request.form["nombre"].strip().lower()
    asiento = request.form["asiento"].strip().lower()

    if nombre == ADMIN_NAME and asiento == ADMIN_SEAT:
        session.permanent = True
        session["admin"] = True
        return redirect(url_for("admin"))

    if get_config('app_activa', '1') != '1':
        flash(get_config('mensaje_inactiva', 'La app no está disponible en este momento.'))
        return redirect(url_for("home"))
    elif not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+", nombre):
        flash("El nombre solo puede contener letras.")
        return redirect(url_for("home"))
    elif len(asiento) > 3:
        flash("El asiento no puede tener más de 3 caracteres.")
        return redirect(url_for("home"))
    elif not re.fullmatch(r"[A-Za-z0-9]+", asiento):
        flash("El asiento solo puede contener letras y números.")
        return redirect(url_for("home"))
    else:
        # Verificar si ya hay un pedido activo (pendiente o preparando) para este asiento
        conn = get_db_connection()
        pedido_activo = conn.execute(
            "SELECT id FROM pedidos WHERE asiento = ? AND estado IN ('pendiente', 'preparando')",
            (asiento,)
        ).fetchone()
        conn.close()

        if pedido_activo:
            flash("Ya tienes un pedido en curso para este asiento. Espera a que te lo entreguen.")
            return redirect(url_for("home"))

        session["nombre"] = nombre
        session["asiento"] = asiento
        return redirect(url_for("panel"))


@app.route("/panel")
def panel():
    if "nombre" not in session:
        return redirect(url_for("home"))

    conn = get_db_connection()
    productos = conn.execute("SELECT * FROM productos WHERE activo = 1").fetchall()
    opciones = conn.execute("SELECT * FROM opciones_producto WHERE disponible = 1").fetchall()
    conn.close()

    opts = {}
    for op in opciones:
        pid = op["producto_id"]
        tipo = op["tipo"]
        if pid not in opts:
            opts[pid] = {}
        if tipo not in opts[pid]:
            opts[pid][tipo] = []
        opts[pid][tipo].append({"id": op["id"], "valor": op["valor"]})

    return render_template("panel.html",
        nombre=session["nombre"],
        asiento=session["asiento"],
        productos=productos,
        opciones=opts)


@app.route("/pagar", methods=["POST"])
def pagar():
    if "nombre" not in session:
        return redirect(url_for("home"))

    nombre  = request.form["nombre"]
    asiento = request.form["asiento"]
    articulos_json = request.form.get("articulos_json", "[]")

    import json
    try:
        items = json.loads(articulos_json)
    except Exception:
        items = []

    if not items:
        flash("Debes seleccionar al menos un artículo.")
        return redirect(url_for("panel"))

    # Verificar nuevamente que no haya pedido activo (proteccion doble)
    conn = get_db_connection()
    pedido_activo = conn.execute(
        "SELECT id FROM pedidos WHERE asiento = ? AND estado IN ('pendiente', 'preparando')",
        (asiento,)
    ).fetchone()
    if pedido_activo:
        conn.close()
        flash("Ya tienes un pedido en curso para este asiento.")
        return redirect(url_for("panel"))

    articulos_str = ", ".join([i["nombre"] for i in items])

    partes = []
    for i in items:
        txt = i["nombre"]
        subs = []
        if i.get("sabor"):  subs.append("Sabor: "  + i["sabor"])
        if i.get("leche"):  subs.append("Leche: "  + i["leche"])
        if i.get("cafe"):   subs.append("Café: "   + i["cafe"])
        if i.get("azucar"): subs.append("Azúcar: " + i["azucar"])
        if i.get("hielo"):  subs.append("Hielo: "  + i["hielo"])
        if subs:
            txt += " (" + ", ".join(subs) + ")"
        partes.append(txt)

    detalles_str = "; ".join(partes)
    total = sum([float(i.get("precio", 0)) for i in items])

    conn.execute(
        "INSERT INTO pedidos (nombre, asiento, articulos, detalles, total, estado) VALUES (?, ?, ?, ?, ?, 'pendiente')",
        (nombre, asiento, articulos_str, detalles_str, total)
    )

    hoy = date.today().isoformat()
    existing = conn.execute("SELECT id FROM arqueo WHERE fecha = ?", (hoy,)).fetchone()
    if existing:
        conn.execute("UPDATE arqueo SET total_ventas = total_ventas + ?, num_pedidos = num_pedidos + 1 WHERE fecha = ?", (total, hoy))
    else:
        conn.execute("INSERT INTO arqueo (fecha, total_ventas, num_pedidos) VALUES (?, ?, 1)", (hoy, total))

    conn.commit()
    conn.close()

    # Guardar datos en sesion para la pagina de estado
    session["ultimo_asiento"] = asiento
    session["ultimo_nombre"]  = nombre
    session.pop("nombre", None)
    session.pop("asiento", None)

    return redirect(url_for("pedido_exitoso"))


@app.route("/pedido_exitoso")
def pedido_exitoso():
    asiento = session.get("ultimo_asiento")
    nombre  = session.get("ultimo_nombre")
    if not asiento:
        return redirect(url_for("home"))

    conn = get_db_connection()
    pedido = conn.execute(
        "SELECT * FROM pedidos WHERE asiento = ? AND estado IN ('pendiente', 'preparando') ORDER BY fecha DESC LIMIT 1",
        (asiento,)
    ).fetchone()
    conn.close()

    return render_template("pedido_exitoso.html", pedido=pedido, nombre=nombre, asiento=asiento)


@app.route("/pedido_exitoso", methods=["POST"])
def pedido_exitoso_post():
    session.pop("ultimo_asiento", None)
    session.pop("ultimo_nombre", None)
    return redirect(url_for("home"))


# Endpoint JSON para el admin: devuelve cuantos pedidos activos hay
@app.route("/admin/conteo_pedidos")
def conteo_pedidos():
    if not session.get("admin"):
        return jsonify({"total": 0})
    conn = get_db_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM pedidos WHERE estado IN ('pendiente', 'preparando')"
    ).fetchone()[0]
    conn.close()
    return jsonify({"total": total})


# Endpoint JSON para que la pagina de estado haga polling sin recargar toda la pagina
@app.route("/estado_pedido/<asiento>")
def estado_pedido(asiento):
    conn = get_db_connection()
    pedido = conn.execute(
        "SELECT estado FROM pedidos WHERE asiento = ? AND estado IN ('pendiente', 'preparando') ORDER BY fecha DESC LIMIT 1",
        (asiento,)
    ).fetchone()
    conn.close()
    if pedido:
        return jsonify({"estado": pedido["estado"]})
    return jsonify({"estado": "entregado"})


# --- RUTAS ADMIN ------------------------------------------------------------

@app.route("/admin")
def admin():
    if not session.get("admin"):
        flash("Acceso no autorizado.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    pedidos   = conn.execute("SELECT * FROM pedidos WHERE estado IN ('pendiente','preparando') ORDER BY fecha DESC").fetchall()
    productos = conn.execute("SELECT * FROM productos ORDER BY categoria, nombre").fetchall()
    opciones  = conn.execute("""
        SELECT op.*, p.nombre as prod_nombre
        FROM opciones_producto op
        JOIN productos p ON op.producto_id = p.id
        ORDER BY p.nombre, op.tipo, op.valor
    """).fetchall()

    hoy = date.today().isoformat()
    arqueo_hoy = conn.execute("SELECT * FROM arqueo WHERE fecha = ?", (hoy,)).fetchone()

    # Solo se guardan y muestran miercoles (2), viernes (4), sabados (5) y domingos (6)
    # Python weekday(): 0=lunes ... 6=domingo
    DIAS_OPERATIVOS = (2, 4, 5, 6)
    NOMBRES_DIA = {2: 'Miércoles', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}

    arqueos_raw = conn.execute(
        "SELECT * FROM arqueo WHERE oculto = 0 ORDER BY fecha DESC LIMIT 120"
    ).fetchall()

    # Filtrar solo dias operativos y agregar dia_semana y dia_nombre como dict
    arqueos = []
    for a in arqueos_raw:
        try:
            fecha_dt = date.fromisoformat(a["fecha"])
            dia = fecha_dt.weekday()
            if dia in DIAS_OPERATIVOS:
                row = dict(a)
                row["dia_semana"] = dia
                row["dia_nombre"] = NOMBRES_DIA[dia]
                arqueos.append(row)
        except Exception:
            pass

    # Desglose de ventas por producto del dia actual
    desglose = conn.execute("""
        SELECT p.nombre, p.categoria, COUNT(*) as cantidad, SUM(p.precio) as subtotal
        FROM pedidos ped
        JOIN productos p ON instr(ped.articulos, p.nombre) > 0
        WHERE date(ped.fecha) = ?
        GROUP BY p.id
        ORDER BY cantidad DESC
    """, (hoy,)).fetchall()

    conn.close()

    return render_template("admin.html",
        pedidos=pedidos,
        productos=productos,
        opciones=opciones,
        arqueo_hoy=arqueo_hoy,
        arqueos=arqueos,
        desglose=desglose,
        hoy=hoy,
        app_activa=get_config('app_activa', '1') == '1',
        mensaje_inactiva=get_config('mensaje_inactiva', ''))


@app.route("/completar/<int:id>")
def completar(id):
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("DELETE FROM pedidos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Pedido completado.")
    return redirect(url_for("admin"))


@app.route("/preparar/<int:id>")
def preparar(id):
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("UPDATE pedidos SET estado = 'preparando' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


# CRUD Productos

@app.route("/admin/producto/nuevo", methods=["POST"])
def producto_nuevo():
    if not session.get("admin"):
        return redirect(url_for("home"))

    nombre       = request.form["nombre"].strip()
    precio       = float(request.form["precio"])
    categoria    = request.form["categoria"].strip()
    tiene_sabores = 1 if request.form.get("tiene_sabores") else 0
    tiene_leche   = 1 if request.form.get("tiene_leche")   else 0
    tiene_hielo   = 1 if request.form.get("tiene_hielo")   else 0
    tiene_azucar  = 1 if request.form.get("tiene_azucar")  else 0
    tiene_cafe    = 1 if request.form.get("tiene_cafe")    else 0

    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO productos (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar, tiene_cafe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar, tiene_cafe)
    )
    prod_id = cur.lastrowid

    sabores = request.form.get("sabores", "")
    if tiene_sabores and sabores:
        for s in [x.strip() for x in sabores.split(",") if x.strip()]:
            conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, 'sabor', ?)", (prod_id, s))

    leches = request.form.get("leches", "")
    if tiene_leche and leches:
        for l in [x.strip() for x in leches.split(",") if x.strip()]:
            conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, 'leche', ?)", (prod_id, l))

    conn.commit()
    conn.close()
    flash("Producto creado.")
    return redirect(url_for("admin"))


@app.route("/admin/producto/editar/<int:id>", methods=["POST"])
def producto_editar(id):
    if not session.get("admin"):
        return redirect(url_for("home"))

    nombre       = request.form["nombre"].strip()
    precio       = float(request.form["precio"])
    categoria    = request.form["categoria"].strip()
    tiene_sabores = 1 if request.form.get("tiene_sabores") else 0
    tiene_leche   = 1 if request.form.get("tiene_leche")   else 0
    tiene_hielo   = 1 if request.form.get("tiene_hielo")   else 0
    tiene_azucar  = 1 if request.form.get("tiene_azucar")  else 0
    tiene_cafe    = 1 if request.form.get("tiene_cafe")    else 0
    activo        = 1 if request.form.get("activo")        else 0

    conn = get_db_connection()
    conn.execute(
        "UPDATE productos SET nombre=?, precio=?, categoria=?, tiene_sabores=?, tiene_leche=?, tiene_hielo=?, tiene_azucar=?, tiene_cafe=?, activo=? WHERE id=?",
        (nombre, precio, categoria, tiene_sabores, tiene_leche, tiene_hielo, tiene_azucar, tiene_cafe, activo, id)
    )
    conn.commit()
    conn.close()
    flash("Producto actualizado.")
    return redirect(url_for("admin"))


@app.route("/admin/producto/borrar/<int:id>")
def producto_borrar(id):
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("DELETE FROM opciones_producto WHERE producto_id = ?", (id,))
    conn.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Producto eliminado.")
    return redirect(url_for("admin"))


# CRUD Opciones

@app.route("/admin/opcion/nueva", methods=["POST"])
def opcion_nueva():
    if not session.get("admin"):
        return redirect(url_for("home"))
    producto_id = int(request.form["producto_id"])
    tipo  = request.form["tipo"]
    valor = request.form["valor"].strip()
    conn = get_db_connection()
    conn.execute("INSERT INTO opciones_producto (producto_id, tipo, valor) VALUES (?, ?, ?)", (producto_id, tipo, valor))
    conn.commit()
    conn.close()
    flash("Opción agregada.")
    return redirect(url_for("admin"))


@app.route("/admin/opcion/toggle/<int:id>")
def opcion_toggle(id):
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("UPDATE opciones_producto SET disponible = CASE WHEN disponible=1 THEN 0 ELSE 1 END WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/opcion/borrar/<int:id>")
def opcion_borrar(id):
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("DELETE FROM opciones_producto WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Opción eliminada.")
    return redirect(url_for("admin"))


# Arqueo

@app.route("/admin/arqueo/nota", methods=["POST"])
def arqueo_nota():
    if not session.get("admin"):
        return redirect(url_for("home"))
    fecha = request.form["fecha"]
    notas = request.form["notas"]
    conn = get_db_connection()
    conn.execute("UPDATE arqueo SET notas=? WHERE fecha=?", (notas, fecha))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/arqueo/reiniciar", methods=["POST"])
def arqueo_reiniciar():
    if not session.get("admin"):
        return redirect(url_for("home"))
    hoy = date.today().isoformat()
    conn = get_db_connection()
    conn.execute("DELETE FROM pedidos")
    conn.execute("UPDATE arqueo SET total_ventas=0, num_pedidos=0 WHERE fecha=?", (hoy,))
    conn.commit()
    conn.close()
    flash("Cuenta reiniciada para hoy. (Solo para pruebas)")
    return redirect(url_for("admin"))


@app.route("/admin/arqueo/limpiar_historial", methods=["POST"])
def arqueo_limpiar_historial():
    if not session.get("admin"):
        return redirect(url_for("home"))
    hoy = date.today().isoformat()
    conn = get_db_connection()
    # Marca como ocultos todos los registros anteriores a hoy
    conn.execute("UPDATE arqueo SET oculto = 1 WHERE fecha < ?", (hoy,))
    conn.commit()
    conn.close()
    flash("Historial anterior ocultado. Los datos siguen guardados en la base de datos.")
    return redirect(url_for("admin"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# --- CONFIG APP -------------------------------------------------------------

@app.route("/admin/config/desactivar", methods=["POST"])
def config_desactivar():
    if not session.get("admin"):
        return redirect(url_for("home"))
    mensaje = request.form.get("mensaje", "").strip()
    conn = get_db_connection()
    conn.execute("UPDATE config SET valor = '0' WHERE clave = 'app_activa'")
    conn.execute("UPDATE config SET valor = ? WHERE clave = 'mensaje_inactiva'", (mensaje,))
    conn.commit()
    conn.close()
    flash("App desactivada.")
    return redirect(url_for("admin"))


@app.route("/admin/config/activar", methods=["POST"])
def config_activar():
    if not session.get("admin"):
        return redirect(url_for("home"))
    conn = get_db_connection()
    conn.execute("UPDATE config SET valor = '1' WHERE clave = 'app_activa'")
    conn.commit()
    conn.close()
    flash("App reactivada. Los usuarios pueden acceder nuevamente.")
    return redirect(url_for("admin"))


@app.route("/reactivar", methods=["GET", "POST"])
def reactivar():
    error = None
    if request.method == "POST":
        clave = request.form.get("clave", "").strip()
        if clave == CLAVE_REACTIVAR:
            conn = get_db_connection()
            conn.execute("UPDATE config SET valor = '1' WHERE clave = 'app_activa'")
            conn.commit()
            conn.close()
            # Iniciar sesion de admin para que pueda acceder al panel completo
            session.permanent = True
            session["admin"] = True
            flash("App reactivada correctamente.")
            return redirect(url_for("admin"))
        else:
            error = "Clave incorrecta."
    return render_template("reactivar.html", error=error)


migrate_db()
init_db()

if __name__ == "__main__":
    # Solo se usa al correr localmente con "python app.py".
    # En PythonAnywhere el servidor WSGI llama directamente a "app",
    # esta sección no se ejecuta.
    print("Iniciando servidor Cafetería Adulam (modo local)...")
    app.run(host="0.0.0.0", port=5000, debug=False)