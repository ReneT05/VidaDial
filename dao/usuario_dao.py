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

