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
from dao.usuario_dao import UsuarioDAO

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

# Inicializar DAO (patrón DAO para usuarios)
usuario_dao = UsuarioDAO(con_pool)

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

def admin_required(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        if not session.get("login"):
            return jsonify({
                "estado": "error",
                "respuesta": "No has iniciado sesión"
            }), 401
        # Comparar como string porque en la BD es VARCHAR
        if str(session.get("login-tipo")) != "1":
            return jsonify({
                "estado": "error",
                "respuesta": "No tienes permisos de administrador"
            }), 403
        return fun(*args, **kwargs)
    return decorador

def obtener_contexto_usuario():
    """
    Retorna información de la sesión del usuario.
    """
    tipo_usuario = session.get("login-tipo", 0)
    id_usuario = session.get("login-id")
    # Convertir a string para comparación porque en la BD es VARCHAR
    es_admin = (str(tipo_usuario) == "1")
    paciente = session.get("login-usr")
    return tipo_usuario, id_usuario, es_admin, paciente

def obtener_id_paciente_por_nombre(nombre_paciente: str):
    """
    Obtiene el idPaciente desde el nombre del paciente.
    Retorna el idPaciente o None si no se encuentra.
    Busca de forma case-insensitive y permite coincidencias parciales.
    """
    if not nombre_paciente:
        return None
    
    con = None
    cursor = None
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        # Buscar primero por coincidencia exacta (case-insensitive)
        sql = """
        SELECT idPaciente
        FROM pacientes
        WHERE LOWER(TRIM(nombreCompleto)) = LOWER(TRIM(%s))
        LIMIT 1
        """
        cursor.execute(sql, (nombre_paciente,))
        resultado = cursor.fetchone()
        if resultado:
            return resultado['idPaciente']
        
        # Si no encuentra, buscar por coincidencia parcial (case-insensitive)
        sql = """
        SELECT idPaciente
        FROM pacientes
        WHERE LOWER(nombreCompleto) LIKE LOWER(%s)
        LIMIT 1
        """
        cursor.execute(sql, (f"%{nombre_paciente}%",))
        resultado = cursor.fetchone()
        return resultado['idPaciente'] if resultado else None
    except mysql.connector.Error as error:
        print(f"[app.py] Error al obtener idPaciente: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

def obtener_id_paciente_por_id_usuario(id_usuario: int):
    """
    Obtiene el idPaciente asociado a un idUsuario.
    Retorna el idPaciente o None si no se encuentra.
    """
    if not id_usuario:
        return None
    
    con = None
    cursor = None
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT idPaciente
        FROM pacientes
        WHERE idUsuario = %s
        LIMIT 1
        """
        cursor.execute(sql, (id_usuario,))
        resultado = cursor.fetchone()
        return resultado['idPaciente'] if resultado else None
    except mysql.connector.Error as error:
        print(f"[app.py] Error al obtener idPaciente por idUsuario: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

def obtener_nombre_paciente_por_id(id_paciente: int):
    """
    Obtiene el nombre del paciente desde su idPaciente.
    Retorna el nombre o None si no se encuentra.
    """
    if not id_paciente:
        return None
    
    con = None
    cursor = None
    try:
        con = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql = """
        SELECT nombreCompleto
        FROM pacientes
        WHERE idPaciente = %s
        LIMIT 1
        """
        cursor.execute(sql, (id_paciente,))
        resultado = cursor.fetchone()
        return resultado['nombreCompleto'] if resultado else None
    except mysql.connector.Error as error:
        print(f"[app.py] Error al obtener nombre de paciente: {error}")
        return None
    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

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

    registros = usuario_dao.autenticar(usuario, contrasena)

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
        "id": session.get("login-id"),
        "idUsuario": session.get("login-id"),
        "paciente": session.get("login-usr")
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
    paciente_param = args.get("paciente", "").strip()

    # Convertir mes a entero
    mes_int = int(mes) if mes and mes.isdigit() else None

    # Definir contexto de usuario para aplicar reglas por rol
    tipo_usuario, id_usuario, es_admin, paciente_sesion = obtener_contexto_usuario()

    # Convertir nombre de paciente a idPaciente
    id_paciente_filtro = None
    if es_admin:
        if paciente_param:
            id_paciente_filtro = obtener_id_paciente_por_nombre(paciente_param)
        filtro_usuario = None
    else:
        # Si no es admin, obtener el idPaciente desde la relación con el usuario
        id_paciente_filtro = obtener_id_paciente_por_id_usuario(id_usuario)
        filtro_usuario = id_usuario

    # Usar el Facade para buscar (simplifica todo el proceso)
    resultado = bitacora_facade.buscar_por_mes(
        mes_int,
        id_usuario=filtro_usuario,
        id_paciente=id_paciente_filtro,
        aplicar_decoradores=True
    )

    # Retornar solo los registros para mantener compatibilidad con el frontend
    # El frontend puede acceder a resultado['registros'] o usar resultado completo
    return make_response(jsonify(resultado.get('registros', [])))

@app.route("/bitacora/<int:id>", methods=["GET"])
@login
def obtenerBitacora(id):
    """Obtiene un registro de bitácora por su ID."""
    tipo_usuario, id_usuario, es_admin, paciente_sesion = obtener_contexto_usuario()
    filtro_usuario = None if es_admin else id_usuario
    id_paciente_filtro = None
    if not es_admin:
        # Si no es admin, obtener el idPaciente desde la relación con el usuario
        id_paciente_filtro = obtener_id_paciente_por_id_usuario(id_usuario)
    resultado = bitacora_facade.obtener_registro(
        id,
        id_usuario=filtro_usuario,
        id_paciente=id_paciente_filtro
    )
    
    if resultado.get('success'):
        return make_response(jsonify(resultado.get('registro')))
    else:
        return make_response(jsonify({"error": resultado.get('error', 'Registro no encontrado')}), 404)

@app.route("/bitacora", methods=["POST"])
@login
def guardarBitacora():
    # Recopilar datos del formulario
    id_bitacora = request.form.get("id", "").strip()
    
    # Obtener contexto de usuario
    tipo_usuario, id_usuario, es_admin, paciente_sesion = obtener_contexto_usuario()
    
    nombre_paciente = request.form.get("paciente", "").strip()
    id_paciente = None
    
    if not es_admin:
        # Si no es admin, obtener el idPaciente desde la relación con el usuario
        id_paciente = obtener_id_paciente_por_id_usuario(id_usuario)
        if id_paciente:
            # Obtener el nombre completo del paciente para mantener consistencia
            nombre_paciente = obtener_nombre_paciente_por_id(id_paciente) or nombre_paciente
        else:
            # Si no hay paciente asociado al usuario, intentar buscar por nombre
            if nombre_paciente:
                id_paciente = obtener_id_paciente_por_nombre(nombre_paciente)
    else:
        # Si es admin, buscar por el nombre proporcionado
        if nombre_paciente:
            id_paciente = obtener_id_paciente_por_nombre(nombre_paciente)
    
    if not id_paciente:
        return make_response(jsonify({"error": "Paciente no encontrado en la base de datos. Verifique que el nombre del paciente sea correcto."}), 400)
    
    if not nombre_paciente:
        return make_response(jsonify({"error": "El campo paciente es obligatorio"}), 400)
    
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
        "presionArterial": request.form.get("presionArterial", "").strip() or None,
        "paciente": nombre_paciente,  # Mantener para compatibilidad
        "idPaciente": id_paciente     # Agregar idPaciente para la BD
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
    resultado = bitacora_facade.guardar_registro(
        datos,
        tipo_usuario=tipo_usuario,
        id_usuario=id_usuario,
        es_admin=es_admin,
        paciente_contexto=None if es_admin else paciente_sesion
    )

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

    # Obtener contexto de usuario
    tipo_usuario, id_usuario, es_admin, paciente_sesion = obtener_contexto_usuario()

    # Usar el Facade para eliminar (simplifica todo el proceso)
    # Pasar tipo_usuario para que los observadores puedan filtrar
    # Pasar id_usuario para verificar permisos
    resultado = bitacora_facade.eliminar_registro(
        id_int,
        tipo_usuario=tipo_usuario,
        id_usuario=id_usuario,
        es_admin=es_admin,
        paciente_contexto=None if es_admin else paciente_sesion
    )

    if resultado.get('success'):
        return make_response(jsonify({"success": True}))
    else:
        return make_response(jsonify({"error": resultado.get('error', 'Error al eliminar')}), 400)

# ============================================================================
# RUTAS PARA GESTIÓN DE USUARIOS Y ADMINISTRADORES
# ============================================================================

@app.route("/usuarios", methods=["GET"])
@admin_required
def listarUsuarios():
    """Lista todos los usuarios (solo administradores)."""
    try:
        usuarios = usuario_dao.listar_todos()
        return make_response(jsonify(usuarios))
    except Exception as error:
        print(f"[app.py] Error al listar usuarios: {error}")
        return make_response(jsonify({"error": "Error al listar usuarios"}), 500)

@app.route("/usuario/<int:id>", methods=["GET"])
@admin_required
def obtenerUsuario(id):
    """Obtiene un usuario por su ID (solo administradores)."""
    try:
        usuario = usuario_dao.obtener_por_id(id)
        if usuario:
            return make_response(jsonify(usuario))
        else:
            return make_response(jsonify({"error": "Usuario no encontrado"}), 404)
    except Exception as error:
        print(f"[app.py] Error al obtener usuario: {error}")
        return make_response(jsonify({"error": "Error al obtener usuario"}), 500)

@app.route("/usuario", methods=["POST"])
@admin_required
def guardarUsuario():
    """Crea o actualiza un usuario (solo administradores)."""
    try:
        id_usuario = request.form.get("id", "").strip()
        nombre = request.form.get("nombre", "").strip()
        contrasena = request.form.get("contrasena", "").strip()
        tipo_usuario = request.form.get("tipo_usuario", "").strip()
        
        if not nombre:
            return make_response(jsonify({"error": "El nombre es obligatorio"}), 400)
        
        # Convertir tipo_usuario a entero
        try:
            tipo_usuario_int = int(tipo_usuario) if tipo_usuario else 2
        except ValueError:
            tipo_usuario_int = 2
        
        # Validar que tipo_usuario sea 1 (admin) o 2 (usuario)
        if tipo_usuario_int not in [1, 2]:
            tipo_usuario_int = 2
        
        if id_usuario and id_usuario.isdigit():
            # Actualizar usuario existente
            id_int = int(id_usuario)
            # Si no se proporciona contraseña, no la actualizamos
            if contrasena:
                exito = usuario_dao.actualizar(id_int, nombre, contrasena, tipo_usuario_int)
            else:
                exito = usuario_dao.actualizar(id_int, nombre, None, tipo_usuario_int)
            
            if exito:
                return make_response(jsonify({"success": True, "id": id_int}))
            else:
                return make_response(jsonify({"error": "Error al actualizar usuario"}), 400)
        else:
            # Crear nuevo usuario
            if not contrasena:
                return make_response(jsonify({"error": "La contraseña es obligatoria para nuevos usuarios"}), 400)
            
            nuevo_id = usuario_dao.crear(nombre, contrasena, tipo_usuario_int)
            if nuevo_id:
                return make_response(jsonify({"success": True, "id": nuevo_id}))
            else:
                return make_response(jsonify({"error": "Error al crear usuario"}), 400)
    except Exception as error:
        print(f"[app.py] Error al guardar usuario: {error}")
        return make_response(jsonify({"error": "Error al guardar usuario"}), 500)

@app.route("/usuario/eliminar", methods=["POST"])
@admin_required
def eliminarUsuario():
    """Elimina un usuario (solo administradores)."""
    try:
        id_usuario = request.form.get("id")
        if not id_usuario:
            return make_response(jsonify({"error": "ID no proporcionado"}), 400)
        
        try:
            id_int = int(id_usuario)
        except ValueError:
            return make_response(jsonify({"error": "ID inválido"}), 400)
        
        # No permitir que un administrador se elimine a sí mismo
        if id_int == session.get("login-id"):
            return make_response(jsonify({"error": "No puedes eliminar tu propio usuario"}), 400)
        
        exito = usuario_dao.eliminar(id_int)
        if exito:
            return make_response(jsonify({"success": True}))
        else:
            return make_response(jsonify({"error": "Error al eliminar usuario o usuario no encontrado"}), 400)
    except Exception as error:
        print(f"[app.py] Error al eliminar usuario: {error}")
        return make_response(jsonify({"error": "Error al eliminar usuario"}), 500)
