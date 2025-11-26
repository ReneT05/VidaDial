"""
Módulo que implementa los patrones Singleton y Factory para el servicio de bitácora.
"""

import mysql.connector
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BitacoraConnectionSingleton:
    """
    Patrón Singleton para gestionar la conexión a la base de datos de bitácora.
    Asegura que solo exista una instancia de conexión en toda la aplicación.
    """
    _instance = None
    _connection_pool = None

    def __new__(cls, connection_pool):
        if cls._instance is None:
            cls._instance = super(BitacoraConnectionSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self, connection_pool):
        if self._connection_pool is None:
            self._connection_pool = connection_pool

    def get_connection(self):
        """Obtiene una conexión del pool."""
        return self._connection_pool.get_connection()

    @classmethod
    def get_instance(cls, connection_pool=None):
        """Método estático para obtener la instancia única del Singleton."""
        if cls._instance is None:
            if connection_pool is None:
                raise ValueError("Se requiere un connection_pool para la primera inicialización")
            cls._instance = cls(connection_pool)
        return cls._instance


class BitacoraSearchStrategy(ABC):
    """
    Interfaz abstracta para las estrategias de búsqueda de bitácora.
    Patrón Strategy que será usado por el Factory.
    """

    @abstractmethod
    def search(self, connection, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ejecuta la búsqueda según la estrategia específica.
        
        Args:
            connection: Conexión a la base de datos
            params: Diccionario con los parámetros de búsqueda
            
        Returns:
            Lista de registros encontrados
        """
        pass


class BitacoraSearchByMonth(BitacoraSearchStrategy):
    """
    Estrategia de búsqueda por mes específico.
    Filtra los registros de bitácora por el mes y año proporcionados.
    """

    def search(self, connection, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca registros de bitácora por mes y año."""
        mes = params.get('mes')
        año = params.get('año')
        
        if not mes or not año:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            # Formato de fecha esperado: YYYY-MM-DD
            # Buscamos registros donde el mes y año coincidan
            sql = """
            SELECT *
            FROM bitacora
            WHERE YEAR(fecha) = %s AND MONTH(fecha) = %s
            ORDER BY idBitacora DESC;
            """
            val = (año, mes)
            
            cursor.execute(sql, val)
            registros = cursor.fetchall()
            
            if cursor:
                cursor.close()
                
            return registros
            
        except mysql.connector.errors.ProgrammingError as error:
            return []
        except Exception as error:
            return []


class BitacoraSearchByText(BitacoraSearchStrategy):
    """
    Estrategia de búsqueda por texto general.
    Busca en los campos idBitacora, fecha y glucosa.
    """

    def search(self, connection, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca registros de bitácora por texto."""
        busqueda = params.get('busqueda', '')
        busqueda = f"%{busqueda}%"

        try:
            cursor = connection.cursor(dictionary=True)
            sql = """
            SELECT *
            FROM bitacora
            WHERE 
                idBitacora LIKE %s OR
                fecha LIKE %s OR
                glucosa LIKE %s
            ORDER BY idBitacora DESC;
            """
            val = (busqueda, busqueda, busqueda)
            
            cursor.execute(sql, val)
            registros = cursor.fetchall()
            
            if cursor:
                cursor.close()
                
            return registros
            
        except mysql.connector.errors.ProgrammingError as error:
            return []
        except Exception as error:
            return []


class BitacoraSearchByMonthAndText(BitacoraSearchStrategy):
    """
    Estrategia de búsqueda combinada: por mes y texto.
    Filtra por mes y además busca texto en los campos.
    """

    def search(self, connection, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca registros de bitácora por mes y texto."""
        mes = params.get('mes')
        año = params.get('año')
        busqueda = params.get('busqueda', '')
        busqueda = f"%{busqueda}%"

        if not mes or not año:
            # Si no hay mes, usar búsqueda por texto solamente
            strategy = BitacoraSearchByText()
            return strategy.search(connection, params)

        try:
            cursor = connection.cursor(dictionary=True)
            sql = """
            SELECT *
            FROM bitacora
            WHERE 
                YEAR(fecha) = %s AND MONTH(fecha) = %s
                AND (
                    idBitacora LIKE %s OR
                    fecha LIKE %s OR
                    glucosa LIKE %s
                )
            ORDER BY idBitacora DESC;
            """
            val = (año, mes, busqueda, busqueda, busqueda)
            
            cursor.execute(sql, val)
            registros = cursor.fetchall()
            
            if cursor:
                cursor.close()
                
            return registros
            
        except mysql.connector.errors.ProgrammingError as error:
            return []
        except Exception as error:
            return []


class BitacoraSearchFactory:
    """
    Patrón Factory para crear las diferentes estrategias de búsqueda.
    Determina qué estrategia usar basándose en los parámetros proporcionados.
    """

    @staticmethod
    def create_search_strategy(params: Dict[str, Any]) -> BitacoraSearchStrategy:
        """
        Crea la estrategia de búsqueda apropiada según los parámetros.
        
        Args:
            params: Diccionario con los parámetros de búsqueda
                   - 'mes': mes a buscar (opcional)
                   - 'año': año a buscar (opcional)
                   - 'busqueda': texto a buscar (opcional)
        
        Returns:
            Instancia de la estrategia de búsqueda apropiada
        """
        mes = params.get('mes')
        año = params.get('año')
        busqueda = params.get('busqueda', '').strip()
        
        # Si hay mes y año, y también hay texto de búsqueda
        if mes and año and busqueda:
            return BitacoraSearchByMonthAndText()
        
        # Si solo hay mes y año
        elif mes and año:
            return BitacoraSearchByMonth()
        
        # Si solo hay texto de búsqueda o no hay parámetros
        else:
            return BitacoraSearchByText()

