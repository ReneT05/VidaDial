"""
Módulo que implementa los patrones Singleton, Factory, Facade, Decorator y Observer para el servicio de bitácora.
"""

import mysql.connector
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


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
    Filtra los registros de bitácora por el mes proporcionado (en cualquier año).
    """

    def search(self, connection, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca registros de bitácora por mes (en cualquier año)."""
        mes = params.get('mes')
        
        if not mes:
            return []

        try:
            cursor = connection.cursor(dictionary=True)
            # Buscamos registros donde el mes coincida (sin importar el año)
            sql = """
            SELECT *
            FROM bitacora
            WHERE MONTH(fecha) = %s
            ORDER BY idBitacora DESC;
            """
            val = (mes,)
            
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
                   - 'mes': mes a buscar (requerido)
        
        Returns:
            Instancia de la estrategia de búsqueda apropiada
        """
        mes = params.get('mes')
        
        # Si hay mes, buscar por mes
        if mes:
            return BitacoraSearchByMonth()
        
        # Si no hay mes, retornar búsqueda vacía
        else:
            return BitacoraSearchByText()


# ============================================================================
# PATRÓN DECORATOR
# ============================================================================

class BitacoraDecorator(ABC):
    """
    Clase base abstracta para los decoradores de bitácora.
    Patrón Decorator para agregar funcionalidades adicionales.
    """
    
    def __init__(self, component):
        self._component = component
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Procesa los datos según la funcionalidad del decorador."""
        pass


class BitacoraValidationDecorator(BitacoraDecorator):
    """
    Decorator para validar registros antes de mostrarlos.
    Valida que los registros tengan los campos requeridos y valores válidos.
    """
    
    def process(self, registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida y filtra registros inválidos."""
        # Procesar con el componente anterior si existe
        if self._component:
            registros = self._component.process(registros)
        
        if not isinstance(registros, list):
            return []
        
        registros_validos = []
        for registro in registros:
            if self._validar_registro(registro):
                registros_validos.append(registro)
        
        return registros_validos
    
    def _validar_registro(self, registro: Dict[str, Any]) -> bool:
        """Valida que un registro tenga los campos mínimos requeridos."""
        # Validar que tenga fecha (campo requerido)
        if not registro.get('fecha'):
            return False
        
        # Validar que los valores numéricos sean válidos si existen
        campos_numericos = ['drenajeInicial', 'ufTotal', 'tiempoMedioPerm', 
                           'liquidoIngerido', 'cantidadOrina', 'glucosa']
        
        for campo in campos_numericos:
            valor = registro.get(campo)
            if valor is not None:
                try:
                    float(valor)
                except (ValueError, TypeError):
                    return False
        
        return True


class BitacoraDateFormatDecorator(BitacoraDecorator):
    """
    Decorator para formatear fechas en los registros.
    Convierte las fechas a un formato legible.
    """
    
    def __init__(self, component, formato_fecha: str = "%d/%m/%Y"):
        super().__init__(component)
        self.formato_fecha = formato_fecha
    
    def process(self, registros: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formatea las fechas en los registros."""
        # Procesar con el componente anterior si existe
        if self._component:
            registros = self._component.process(registros)
        
        if not isinstance(registros, list):
            return []
        
        registros_formateados = []
        for registro in registros.copy():
            registro_formateado = registro.copy()
            
            # Formatear fecha
            if registro_formateado.get('fecha'):
                try:
                    fecha_obj = datetime.strptime(str(registro_formateado['fecha']), "%Y-%m-%d")
                    registro_formateado['fecha_formateada'] = fecha_obj.strftime(self.formato_fecha)
                except (ValueError, TypeError):
                    registro_formateado['fecha_formateada'] = registro_formateado['fecha']
            
            # Formatear fechaCreacion y fechaActualizacion si existen
            for campo_fecha in ['fechaCreacion', 'fechaActualizacion']:
                if registro_formateado.get(campo_fecha):
                    try:
                        fecha_obj = datetime.strptime(str(registro_formateado[campo_fecha]), "%Y-%m-%d %H:%M:%S")
                        registro_formateado[f'{campo_fecha}_formateada'] = fecha_obj.strftime("%d/%m/%Y %H:%M")
                    except (ValueError, TypeError):
                        registro_formateado[f'{campo_fecha}_formateada'] = registro_formateado[campo_fecha]
            
            registros_formateados.append(registro_formateado)
        
        return registros_formateados


class BitacoraCountDecorator(BitacoraDecorator):
    """
    Decorator para contar registros y agregar metadatos.
    Agrega información sobre el total de registros.
    """
    
    def process(self, registros: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Agrega el conteo de registros a los resultados."""
        # Procesar con el componente anterior si existe
        if self._component:
            resultado_anterior = self._component.process(registros)
            # Si el componente anterior devolvió un dict, extraer los registros
            if isinstance(resultado_anterior, dict):
                registros = resultado_anterior.get('registros', registros)
            else:
                registros = resultado_anterior
        
        if not isinstance(registros, list):
            return {
                'registros': [],
                'total': 0,
                'metadata': {}
            }
        
        total = len(registros)
        
        # Calcular estadísticas básicas si hay registros
        metadata = {}
        if total > 0:
            # Contar registros con valores en campos importantes
            metadata['con_glucosa'] = sum(1 for r in registros if r.get('glucosa') is not None)
            metadata['con_presion'] = sum(1 for r in registros if r.get('presionArterial') is not None)
            metadata['con_uf_total'] = sum(1 for r in registros if r.get('ufTotal') is not None)
        
        return {
            'registros': registros,
            'total': total,
            'metadata': metadata
        }


# ============================================================================
# PATRÓN OBSERVER
# ============================================================================

class BitacoraObserver(ABC):
    """
    Interfaz abstracta para los observadores de bitácora.
    Patrón Observer para notificar cambios en los registros.
    """
    
    @abstractmethod
    def update(self, event_type: str, data: Dict[str, Any]):
        """
        Se llama cuando ocurre un evento en la bitácora.
        
        Args:
            event_type: Tipo de evento ('created', 'updated', 'deleted')
            data: Datos del evento (contiene 'id' y posiblemente 'datos')
        """
        pass


class BitacoraSubject:
    """
    Sujeto observable que notifica a los observadores cuando ocurren eventos.
    Mantiene una lista de observadores y los notifica cuando hay cambios.
    """
    
    def __init__(self):
        self._observers: List[BitacoraObserver] = []
    
    def attach(self, observer: BitacoraObserver):
        """
        Agrega un observador a la lista.
        
        Args:
            observer: Instancia de un observador
        """
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: BitacoraObserver):
        """
        Elimina un observador de la lista.
        
        Args:
            observer: Instancia del observador a eliminar
        """
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, event_type: str, data: Dict[str, Any]):
        """
        Notifica a todos los observadores sobre un evento.
        
        Args:
            event_type: Tipo de evento ('created', 'updated', 'deleted')
            data: Datos del evento
        """
        for observer in self._observers:
            try:
                observer.update(event_type, data)
            except Exception as e:
                # No fallar si un observador tiene error
                print(f"Error en observador: {e}")


class BitacoraLogObserver(BitacoraObserver):
    """
    Observador concreto que registra eventos en un log.
    Implementa el patrón Observer para logging de eventos.
    """
    
    def update(self, event_type: str, data: Dict[str, Any]):
        """Registra el evento en el log."""
        registro_id = data.get('id', 'N/A')
        mensaje = f"[BITACORA LOG] Evento: {event_type.upper()}, Registro ID: {registro_id}"
        print(mensaje)


class BitacoraNotificationObserver(BitacoraObserver):
    """
    Observador concreto que envía notificaciones sobre eventos.
    Puede extenderse para integrar con sistemas de notificaciones.
    """
    
    def update(self, event_type: str, data: Dict[str, Any]):
        """Envía una notificación sobre el evento."""
        registro_id = data.get('id', 'N/A')
        
        if event_type == 'created':
            mensaje = f"Notificación: Nuevo registro de bitácora creado (ID: {registro_id})"
        elif event_type == 'updated':
            mensaje = f"Notificación: Registro de bitácora actualizado (ID: {registro_id})"
        elif event_type == 'deleted':
            mensaje = f"Notificación: Registro de bitácora eliminado (ID: {registro_id})"
        else:
            mensaje = f"Notificación: Evento desconocido '{event_type}' en registro (ID: {registro_id})"
        
        print(mensaje)


# ============================================================================
# PATRÓN FACADE
# ============================================================================

class BitacoraFacade:
    """
    Patrón Facade para simplificar el acceso a la base de datos y la lógica de bitácora.
    Proporciona una interfaz simple y unificada para todas las operaciones de bitácora.
    """
    
    def __init__(self, connection_singleton: BitacoraConnectionSingleton):
        """
        Inicializa el Facade con el Singleton de conexión.
        
        Args:
            connection_singleton: Instancia del Singleton de conexión
        """
        self.connection_singleton = connection_singleton
        self.decorator_chain = None
        self.subject = BitacoraSubject()  # Sujeto observable para el patrón Observer
    
    def set_decorator_chain(self, decorator: BitacoraDecorator):
        """
        Establece la cadena de decoradores. El decorador pasado debe ser el último
        de la cadena, que envuelve a los anteriores.
        
        Args:
            decorator: El último decorador de la cadena
        """
        self.decorator_chain = decorator
    
    def attach_observer(self, observer: BitacoraObserver):
        """
        Agrega un observador para recibir notificaciones de eventos.
        
        Args:
            observer: Instancia de un observador
        """
        self.subject.attach(observer)
    
    def detach_observer(self, observer: BitacoraObserver):
        """
        Elimina un observador de la lista.
        
        Args:
            observer: Instancia del observador a eliminar
        """
        self.subject.detach(observer)
    
    def buscar_por_mes(self, mes: int, aplicar_decoradores: bool = True) -> Dict[str, Any]:
        """
        Busca registros de bitácora por mes.
        
        Args:
            mes: Número del mes (1-12)
            aplicar_decoradores: Si se deben aplicar los decoradores configurados
        
        Returns:
            Diccionario con los registros y metadatos
        """
        if not mes or mes < 1 or mes > 12:
            return {'registros': [], 'total': 0, 'metadata': {}}
        
        params = {'mes': mes}
        search_strategy = BitacoraSearchFactory.create_search_strategy(params)
        
        con = None
        try:
            con = self.connection_singleton.get_connection()
            registros = search_strategy.search(con, params)
            
            # Aplicar cadena de decoradores si está configurada
            if aplicar_decoradores and self.decorator_chain:
                resultado = self.decorator_chain.process(registros)
                # Si el decorador devolvió un diccionario (como CountDecorator), retornarlo
                if isinstance(resultado, dict):
                    return resultado
                # Si devolvió una lista, crear estructura estándar
                registros = resultado
            
            # Crear estructura estándar
            return {
                'registros': registros,
                'total': len(registros),
                'metadata': {}
            }
            
        except Exception as error:
            return {'registros': [], 'total': 0, 'metadata': {'error': str(error)}}
        finally:
            if con and con.is_connected():
                con.close()
    
    def obtener_registro(self, id_bitacora: int) -> Dict[str, Any]:
        """
        Obtiene un registro de bitácora por su ID.
        
        Args:
            id_bitacora: ID del registro a obtener
        
        Returns:
            Diccionario con el registro o error
        """
        con = None
        try:
            con = self.connection_singleton.get_connection()
            cursor = con.cursor(dictionary=True)
            
            sql = "SELECT * FROM bitacora WHERE idBitacora = %s"
            val = (id_bitacora,)
            
            cursor.execute(sql, val)
            registro = cursor.fetchone()
            
            if cursor:
                cursor.close()
            
            if registro:
                return {
                    'success': True,
                    'registro': registro
                }
            else:
                return {
                    'success': False,
                    'error': 'Registro no encontrado'
                }
            
        except Exception as error:
            return {
                'success': False,
                'error': str(error),
                'message': 'Error al obtener el registro'
            }
        finally:
            if con and con.is_connected():
                con.close()
    
    def guardar_registro(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guarda un nuevo registro o actualiza uno existente en la bitácora.
        
        Args:
            datos: Diccionario con los datos del registro (debe incluir 'id' si es actualización)
        
        Returns:
            Diccionario con el resultado de la operación
        """
        id_bitacora = datos.get('id')
        con = None
        try:
            con = self.connection_singleton.get_connection()
            cursor = con.cursor()
            
            if id_bitacora:
                # Actualizar registro existente
                sql = """
                UPDATE bitacora 
                SET fecha = %s, horaInicio = %s, horaFin = %s, drenajeInicial = %s, 
                    ufTotal = %s, tiempoMedioPerm = %s, liquidoIngerido = %s, 
                    cantidadOrina = %s, glucosa = %s, presionArterial = %s
                WHERE idBitacora = %s
                """
                val = (
                    datos.get('fecha'),
                    datos.get('horaInicio'),
                    datos.get('horaFin'),
                    datos.get('drenajeInicial'),
                    datos.get('ufTotal'),
                    datos.get('tiempoMedioPerm'),
                    datos.get('liquidoIngerido'),
                    datos.get('cantidadOrina'),
                    datos.get('glucosa'),
                    datos.get('presionArterial'),
                    id_bitacora
                )
            else:
                # Insertar nuevo registro
                sql = """
                INSERT INTO bitacora (fecha, horaInicio, horaFin, drenajeInicial, ufTotal, 
                                     tiempoMedioPerm, liquidoIngerido, cantidadOrina, glucosa, presionArterial)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                val = (
                    datos.get('fecha'),
                    datos.get('horaInicio'),
                    datos.get('horaFin'),
                    datos.get('drenajeInicial'),
                    datos.get('ufTotal'),
                    datos.get('tiempoMedioPerm'),
                    datos.get('liquidoIngerido'),
                    datos.get('cantidadOrina'),
                    datos.get('glucosa'),
                    datos.get('presionArterial')
                )
            
            cursor.execute(sql, val)
            con.commit()
            registro_id = id_bitacora if id_bitacora else cursor.lastrowid
            
            if cursor:
                cursor.close()
            
            resultado = {
                'success': True,
                'id': registro_id,
                'message': 'Registro guardado exitosamente' if not id_bitacora else 'Registro actualizado exitosamente'
            }
            
            # Notificar a los observadores
            event_type = 'updated' if id_bitacora else 'created'
            self.subject.notify(event_type, {
                'id': registro_id,
                'datos': datos
            })
            
            return resultado
            
        except Exception as error:
            if con:
                con.rollback()
            return {
                'success': False,
                'error': str(error),
                'message': 'Error al guardar el registro'
            }
        finally:
            if con and con.is_connected():
                con.close()
    
    def eliminar_registro(self, id_bitacora: int) -> Dict[str, Any]:
        """
        Elimina un registro de la bitácora.
        
        Args:
            id_bitacora: ID del registro a eliminar
        
        Returns:
            Diccionario con el resultado de la operación
        """
        con = None
        try:
            con = self.connection_singleton.get_connection()
            cursor = con.cursor()
            
            sql = "DELETE FROM bitacora WHERE idBitacora = %s"
            val = (id_bitacora,)
            
            cursor.execute(sql, val)
            con.commit()
            filas_afectadas = cursor.rowcount
            
            if cursor:
                cursor.close()
            
            resultado = {
                'success': filas_afectadas > 0,
                'filas_afectadas': filas_afectadas,
                'message': 'Registro eliminado exitosamente' if filas_afectadas > 0 else 'Registro no encontrado'
            }
            
            # Notificar a los observadores si se eliminó exitosamente
            if filas_afectadas > 0:
                self.subject.notify('deleted', {'id': id_bitacora})
            
            return resultado
            
        except Exception as error:
            if con:
                con.rollback()
            return {
                'success': False,
                'error': str(error),
                'message': 'Error al eliminar el registro'
            }
        finally:
            if con and con.is_connected():
                con.close()

