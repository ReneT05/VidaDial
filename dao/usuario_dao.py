import mysql.connector


class UsuarioDAO:
    """
    Data Access Object para operaciones relacionadas con usuarios.
    Encapsula el acceso a datos del módulo de autenticación.
    """

    def __init__(self, connection_pool):
        self.connection_pool = connection_pool

    def autenticar(self, nombre: str, contrasena: str):
        """
        Autentica a un usuario usando nombre y contraseña.

        Returns:
            Lista de registros (puede estar vacía si no hay coincidencias).
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor(dictionary=True)
            sql = """
            SELECT idUsuario, nombre, tipo_usuario
            FROM usuario
            WHERE nombre = %s
            AND contrasena = %s
            """
            cursor.execute(sql, (nombre, contrasena))
            registros = cursor.fetchall()
            return registros
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al autenticar usuario: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

    def listar_todos(self):
        """
        Lista todos los usuarios.
        
        Returns:
            Lista de usuarios.
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor(dictionary=True)
            sql = """
            SELECT idUsuario, nombre, tipo_usuario
            FROM usuario
            ORDER BY idUsuario DESC
            """
            cursor.execute(sql)
            registros = cursor.fetchall()
            return registros
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al listar usuarios: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

    def obtener_por_id(self, id_usuario: int):
        """
        Obtiene un usuario por su ID.
        
        Returns:
            Usuario o None si no existe.
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor(dictionary=True)
            sql = """
            SELECT idUsuario, nombre, tipo_usuario
            FROM usuario
            WHERE idUsuario = %s
            """
            cursor.execute(sql, (id_usuario,))
            registros = cursor.fetchall()
            return registros[0] if registros else None
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al obtener usuario: {error}")
            return None
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

    def crear(self, nombre: str, contrasena: str, tipo_usuario: int):
        """
        Crea un nuevo usuario.
        
        Returns:
            ID del usuario creado o None si hay error.
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor()
            sql = """
            INSERT INTO usuario (nombre, contrasena, tipo_usuario)
            VALUES (%s, %s, %s)
            """
            # Convertir tipo_usuario a string porque en la BD es VARCHAR
            cursor.execute(sql, (nombre, contrasena, str(tipo_usuario)))
            con.commit()
            return cursor.lastrowid
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al crear usuario: {error}")
            con.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

    def actualizar(self, id_usuario: int, nombre: str, contrasena: str = None, tipo_usuario: int = None):
        """
        Actualiza un usuario existente.
        
        Returns:
            True si se actualizó correctamente, False en caso contrario.
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor()
            
            # Construir la consulta dinámicamente según los campos proporcionados
            campos = []
            valores = []
            
            if nombre:
                campos.append("nombre = %s")
                valores.append(nombre)
            
            if contrasena:
                campos.append("contrasena = %s")
                valores.append(contrasena)
            
            if tipo_usuario is not None:
                campos.append("tipo_usuario = %s")
                # Convertir tipo_usuario a string porque en la BD es VARCHAR
                valores.append(str(tipo_usuario))
            
            if not campos:
                return False
            
            valores.append(id_usuario)
            sql = f"""
            UPDATE usuario
            SET {', '.join(campos)}
            WHERE idUsuario = %s
            """
            cursor.execute(sql, tuple(valores))
            con.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al actualizar usuario: {error}")
            con.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

    def eliminar(self, id_usuario: int):
        """
        Elimina un usuario.
        
        Returns:
            True si se eliminó correctamente, False en caso contrario.
        """
        con = None
        cursor = None
        try:
            con = self.connection_pool.get_connection()
            cursor = con.cursor()
            sql = """
            DELETE FROM usuario
            WHERE idUsuario = %s
            """
            cursor.execute(sql, (id_usuario,))
            con.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as error:
            print(f"[UsuarioDAO] Error al eliminar usuario: {error}")
            con.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if con and con.is_connected():
                con.close()

