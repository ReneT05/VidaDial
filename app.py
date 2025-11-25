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
    SELECT id, nombre, tipo_usuario
    FROM Usuario
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
    if registros:
        usuario = registros[0]
        session["login"]      = True
        session["login-usr"]  = usuario["nombre"]
        session["login-tipo"] = usuario["tipo_usuario"]

    return make_response(jsonify(registros))

@app.route("/cerrarSesion", methods=["POST"])
@login
def cerrarSesion():
    session["login"]      = False
    session["login-usr"]  = None
    session["login-tipo"] = 0
    return make_response(jsonify({}))

@app.route("/preferencias")
@login
def preferencias():
    return make_response(jsonify({
        "usr": session.get("login-usr"),
        "tipo": session.get("login-tipo", 2)
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
    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"

    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = """
        SELECT *
        FROM bitacora
        WHERE 
            idBitacora LIKE %s OR
            fecha LIKE %s OR
            glucosa LIKE %s
        ORDER BY idBitacora DESC;
        """ 
        val    = (busqueda, )

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

@app.route("/bitacora/eliminar", methods=["POST"])
def eliminarRegistro():
    id = request.form["id"]

    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)

    sql    = """
    DELETE FROM bitacora
    WHERE idBitacora = %s
    """
    val    = (id,)
    cursor.execute(sql, val)
    con.commit()

    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    return make_response(jsonify({}))
