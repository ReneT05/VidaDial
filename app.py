# python.exe -m venv .venv
# cd .venv/Scripts
# activate.bat
# py -m ensurepip --upgrade
# pip install -r requirements.txt

from functools import wraps
from flask import Flask, render_template, request, jsonify, make_response, session

from flask_cors import CORS, cross_origin

import mysql.connector.pooling
import pusher
import pytz
import datetime

from bitacora_service import (
    BitacoraConnectionSingleton, 
    BitacoraSearchFactory,
    BitacoraFacade,
    BitacoraValidationDecorator,
    BitacoraDateFormatDecorator,
    BitacoraCountDecorator,
    BitacoraLogObserver,
    BitacoraNotificationObserver
)

app            = Flask(__name__)
app.secret_key = "Test12345"
CORS(app)

con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host="185.232.14.52",
    database="u760464709_23005102_bd",
    user="u760464709_23005102_usr",
    password="*Q~ic:$9XVr2"
)
"""
con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host="localhost",
    database="practicas",
    user="root",
    password="Test12345"
)
"""

# Inicializar el Singleton para la conexión de bitácora
bitacora_connection = BitacoraConnectionSingleton.get_instance(con_pool)

# Inicializar el Facade con decoradores
bitacora_facade = BitacoraFacade(bitacora_connection)
# Configurar decoradores en cadena: validación -> formateo -> conteo
# Cada decorador envuelve al anterior (patrón Decorator)
decorator_validation = BitacoraValidationDecorator(None)
decorator_date_format = BitacoraDateFormatDecorator(decorator_validation)
decorator_count = BitacoraCountDecorator(decorator_date_format)
bitacora_facade.set_decorator_chain(decorator_count)

# Configurar observadores (patrón Observer)
log_observer = BitacoraLogObserver()
notification_observer = BitacoraNotificationObserver()
bitacora_facade.attach_observer(log_observer)
bitacora_facade.attach_observer(notification_observer)

def pusherProductos():    
    pusher_client = pusher.Pusher(
        app_id="2046005",
        key="12cb9c6b5319b2989000",
        secret="7c193405c24182d96965",
        cluster="us2",
        ssl=True
    )
    
    pusher_client.trigger("canalProductos", "eventoProductos", {"message": "Hola Mundo!"})
    return make_response(jsonify({}))

def login(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        if not session.get("login"):
            return jsonify({
                "estado": "error",
                "respuesta": "No has iniciado sesión"
            }), 401
        return fun(*args, **kwargs)
    return decorador

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/login")
def appLogin():
    return render_template("login.html")
    # return "<h5>Hola, soy la view app</h5>"

@app.route("/fechaHora")
def fechaHora():
    tz    = pytz.timezone("America/Matamoros")
    ahora = datetime.datetime.now(tz)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

@app.route("/iniciarSesion", methods=["POST"])
# Usar cuando solo se quiera usar CORS en rutas específicas
# @cross_origin()
def iniciarSesion():
    usuario    = request.form["usuario"]
    contrasena = request.form["contrasena"]

    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT idUsuario, nombre, tipo_usuario
    FROM usuario
    WHERE nombre = %s
    AND contrasena = %s
    """
    val    = (usuario, contrasena)

    cursor.execute(sql, val)
    registros = cursor.fetchall()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
    session["login-id"]   = None
    if registros:
        usuario = registros[0]
        session["login"]      = True
        session["login-usr"]  = usuario["nombre"]
        session["login-tipo"] = usuario["tipo_usuario"]
        session["login-id"]   = usuario["idUsuario"]

    return make_response(jsonify(registros))

@app.route("/cerrarSesion", methods=["POST"])
@login
def cerrarSesion():
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
    session["login-id"]   = None
    return make_response(jsonify({}))

@app.route("/preferencias")
@login
def preferencias():
    return make_response(jsonify({
        "usr": session.get("login-usr"),
        "tipo": session.get("login-tipo", 2),
        "id": session.get("login-id")
    }))

@app.route("/log", methods=["GET"])
def logProductos():
    args         = request.args
    actividad    = args["actividad"]
    descripcion  = args["descripcion"]
    tz           = pytz.timezone("America/Matamoros")
    ahora        = datetime.datetime.now(tz)
    fechaHoraStr = ahora.strftime("%Y-%m-%d %H:%M:%S")

    with open("log-busquedas.txt", "a") as f:
        f.write(f"{actividad}\t{descripcion}\t{fechaHoraStr}\n")

    with open("log-busquedas.txt") as f:
        log = f.read()

    return log

@app.route("/productos")
def productos():
    return render_template("productos.html")

@app.route("/bitacora")
def bitacora():
    return render_template("bitacora.html")

@app.route("/productos/buscar", methods=["GET"])
@login
def buscarProductos():
    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"

    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = """
        SELECT Id_Producto,
            Nombre_Producto,
            Precio,
            Existencias
        FROM productos
        WHERE Nombre_Producto LIKE %s
        OR    Precio          LIKE %s
        OR    Existencias     LIKE %s
        ORDER BY Id_Producto DESC
        LIMIT 10 OFFSET 0
        """
        val    = (busqueda, busqueda, busqueda)

        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        registros = []

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(registros))

@app.route("/productos/categoria", methods=["GET"])
@login
def productosCategorias():
    args      = request.args
    categoria = args["categoria"]
    
    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = """
        SELECT Nombre_Producto
        FROM productos
        WHERE Categoria = %s
        ORDER BY Nombre_Producto ASC
        LIMIT 50 OFFSET 0
        """
        val    = (categoria, )

        cursor.execute(sql, val)
        registros = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        registros = []

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(registros))

@app.route("/productos/ingredientes/<int:id>")
@login
def productosIngredientes(id):
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT productos.Nombre_Producto, ingredientes.*, productos_ingredientes.Cantidad FROM productos_ingredientes
    INNER JOIN productos ON productos.Id_Producto = productos_ingredientes.Id_Producto
    INNER JOIN ingredientes ON ingredientes.Id_Ingrediente = productos_ingredientes.Id_Ingrediente
    WHERE productos_ingredientes.Id_Producto = %s
    ORDER BY productos.Nombre_Producto
    """
    val    = (id,)

    cursor.execute(sql, val)
    registros = cursor.fetchall()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    return make_response(jsonify(registros))

@app.route("/producto", methods=["POST"])
@login
def guardarProducto():
    id     = request.form["id"]
    nombre = request.form["nombre"]
    precio = request.form["precio"]

    existencias = request.form["existencias"]
    if existencias == '':
        existencias = None

    # fechahora   = datetime.datetime.now(pytz.timezone("America/Matamoros"))

    con    = con_pool.get_connection()
    cursor = con.cursor()

    if id:
        sql = """
        UPDATE productos
        SET Nombre_Producto = %s,
            Precio          = %s,
            Existencias     = %s
        WHERE Id_Producto = %s
        """
        val = (nombre, precio, existencias, id)
    else:
        sql = """
        INSERT INTO productos (Nombre_Producto, Precio, Existencias)
        VALUES                (%s,          %s,      %s)
        """
        val =                 (nombre, precio, existencias)
    
    cursor.execute(sql, val)
    con.commit()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    pusherProductos()

    return make_response(jsonify({}))

@app.route("/producto/<int:id>")
@login
def editarProducto(id):
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT Id_Producto, Nombre_Producto, Precio, Existencias
    FROM productos
    WHERE Id_Producto = %s
    """
    val    = (id,)

    cursor.execute(sql, val)
    registros = cursor.fetchall()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    return make_response(jsonify(registros))

@app.route("/producto/eliminar", methods=["POST"])
def eliminarProducto():
    id = request.form["id"]

    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    DELETE FROM productos
    WHERE Id_Producto = %s
    """
    val    = (id,)

    cursor.execute(sql, val)
    con.commit()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    pusherProductos()

    return make_response(jsonify({}))

@app.route("/bitacora/buscar", methods=["GET"])
@login
def buscarBitacora():
    args = request.args
    mes = args.get("mes", "").strip()

    # Convertir mes a entero
    mes_int = int(mes) if mes and mes.isdigit() else None

    # Obtener ID del usuario de la sesión
    id_usuario = session.get("login-id")

    # Usar el Facade para buscar (simplifica todo el proceso)
    resultado = bitacora_facade.buscar_por_mes(mes_int, id_usuario=id_usuario, aplicar_decoradores=True)

    # Retornar solo los registros para mantener compatibilidad con el frontend
    # El frontend puede acceder a resultado['registros'] o usar resultado completo
    return make_response(jsonify(resultado.get('registros', [])))

@app.route("/bitacora/<int:id>", methods=["GET"])
@login
def obtenerBitacora(id):
    """Obtiene un registro de bitácora por su ID."""
    # Obtener ID del usuario de la sesión
    id_usuario = session.get("login-id")
    resultado = bitacora_facade.obtener_registro(id, id_usuario=id_usuario)
    
    if resultado.get('success'):
        return make_response(jsonify(resultado.get('registro')))
    else:
        return make_response(jsonify({"error": resultado.get('error', 'Registro no encontrado')}), 404)

@app.route("/bitacora", methods=["POST"])
@login
def guardarBitacora():
    # Recopilar datos del formulario
    id_bitacora = request.form.get("id", "").strip()
    
    # Obtener tipo de usuario y ID de usuario de la sesión
    tipo_usuario = session.get("login-tipo", 0)
    id_usuario = session.get("login-id")
    
    datos = {
        "fecha": request.form.get("fecha", "").strip(),
        "horaInicio": request.form.get("horaInicio", "").strip() or None,
        "horaFin": request.form.get("horaFin", "").strip() or None,
        "drenajeInicial": None,
        "ufTotal": None,
        "tiempoMedioPerm": None,
        "liquidoIngerido": None,
        "cantidadOrina": None,
        "glucosa": None,
        "presionArterial": request.form.get("presionArterial", "").strip() or None
    }

    # Agregar ID si existe (para actualización)
    if id_bitacora and id_bitacora.isdigit():
        datos["id"] = int(id_bitacora)

    # Convertir valores vacíos a None para campos numéricos
    campos_numericos = ['drenajeInicial', 'ufTotal', 'tiempoMedioPerm', 
                       'liquidoIngerido', 'cantidadOrina', 'glucosa']
    
    for campo in campos_numericos:
        valor = request.form.get(campo, "").strip()
        datos[campo] = float(valor) if valor else None

    # Usar el Facade para guardar (simplifica todo el proceso)
    # Pasar tipo_usuario para que los observadores puedan filtrar
    # Pasar id_usuario para asociar el registro al usuario
    resultado = bitacora_facade.guardar_registro(datos, tipo_usuario=tipo_usuario, id_usuario=id_usuario)

    if resultado.get('success'):
        return make_response(jsonify({"success": True, "id": resultado.get('id')}))
    else:
        return make_response(jsonify({"error": resultado.get('error', 'Error desconocido')}), 400)

@app.route("/bitacora/eliminar", methods=["POST"])
@login
def eliminarRegistro():
    id_bitacora = request.form.get("id")
    
    if not id_bitacora:
        return make_response(jsonify({"error": "ID no proporcionado"}), 400)

    try:
        id_int = int(id_bitacora)
    except ValueError:
        return make_response(jsonify({"error": "ID inválido"}), 400)

    # Obtener tipo de usuario e ID de usuario de la sesión
    tipo_usuario = session.get("login-tipo", 0)
    id_usuario = session.get("login-id")

    # Usar el Facade para eliminar (simplifica todo el proceso)
    # Pasar tipo_usuario para que los observadores puedan filtrar
    # Pasar id_usuario para verificar permisos
    resultado = bitacora_facade.eliminar_registro(id_int, tipo_usuario=tipo_usuario, id_usuario=id_usuario)

    if resultado.get('success'):
        return make_response(jsonify({"success": True}))
    else:
        return make_response(jsonify({"error": resultado.get('error', 'Error al eliminar')}), 400)
