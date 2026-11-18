"""
Fase 4 - Programación (213023) - UNAD
Sistema Integral de Gestión de Clientes, Servicios y Reservas - Software FJ
Autor: Jesús David Molina González

Ejecución:  python proyecto.py
Resultado:  salida en consola + archivo de logs "software_fj.log"

Organización del archivo:
    1. Logger y excepciones personalizadas
    2. Clase abstracta EntidadBase y clase Cliente
    3. Clase abstracta Servicio y servicios especializados
    4. Clase Reserva
    5. Gestor del sistema y simulación de operaciones
"""

import logging
import re
from abc import ABC, abstractmethod


# =====================================================================
# 1. LOGGER Y EXCEPCIONES PERSONALIZADAS
# =====================================================================

def configurar_logger(nombre_archivo: str = "software_fj.log") -> logging.Logger:
    """Crea el logger que registra errores y eventos en un archivo."""
    log = logging.getLogger("SoftwareFJ")  # obtiene (o crea) el logger del sistema
    log.setLevel(logging.INFO)  # registra desde nivel INFO hacia arriba
    if not log.handlers:  # evita duplicar manejadores si se llama dos veces
        manejador = logging.FileHandler(nombre_archivo, encoding="utf-8")  # archivo de logs
        formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")  # fecha | nivel | mensaje
        manejador.setFormatter(formato)  # asigna el formato al manejador
        log.addHandler(manejador)  # conecta el manejador al logger
    return log


logger = configurar_logger()  # logger global usado por todas las clases


class SoftwareFJError(Exception):
    """Excepción base de todo el sistema."""


class DatosInvalidosError(SoftwareFJError):
    """Datos inválidos, mal formados o parámetros faltantes."""


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio solicitado no está disponible."""


class OperacionNoPermitidaError(SoftwareFJError):
    """Operación que no corresponde al estado actual del objeto."""


class CalculoInconsistenteError(SoftwareFJError):
    """Cálculo de costos con resultados incoherentes."""


class ReservaInvalidaError(SoftwareFJError):
    """La reserva no pudo crearse o procesarse."""


# =====================================================================
# 2. ENTIDAD BASE (ABSTRACTA) Y CLIENTE
# =====================================================================

class EntidadBase(ABC):
    """Clase abstracta que representa cualquier entidad general del sistema."""

    _contador = 0  # contador compartido para generar identificadores únicos

    def __init__(self):
        EntidadBase._contador += 1  # incrementa el contador global
        self._id = EntidadBase._contador  # guarda el id (encapsulado)

    @property
    def id(self) -> int:
        """Identificador de solo lectura."""
        return self._id

    @abstractmethod
    def describir(self) -> str:
        """Cada entidad debe describirse a sí misma."""

    def __str__(self) -> str:
        return self.describir()  # str(objeto) usa la descripción polimórfica


class Cliente(EntidadBase):
    """Cliente con datos personales encapsulados y validaciones estrictas."""

    _PATRON_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{3,60}$")
    _PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

    def __init__(self, nombre: str, documento: str, correo: str, telefono: str):
        self.nombre = nombre  # pasa por el setter (valida)
        self.documento = documento
        self.correo = correo
        self.telefono = telefono
        super().__init__()  # el id se genera solo si todos los datos fueron válidos

    # ---- nombre ----
    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        if not isinstance(valor, str) or not self._PATRON_NOMBRE.match(valor.strip()):
            raise DatosInvalidosError("El nombre debe tener entre 3 y 60 letras.")
        self._nombre = valor.strip()

    # ---- documento ----
    @property
    def documento(self) -> str:
        return self._documento

    @documento.setter
    def documento(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.isdigit() or not 6 <= len(valor) <= 12:
            raise DatosInvalidosError("El documento debe tener entre 6 y 12 dígitos.")
        self._documento = valor

    # ---- correo ----
    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: str) -> None:
        if not isinstance(valor, str) or not self._PATRON_CORREO.match(valor):
            raise DatosInvalidosError("El correo electrónico no es válido.")
        self._correo = valor

    # ---- teléfono ----
    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.isdigit() or not 7 <= len(valor) <= 10:
            raise DatosInvalidosError("El teléfono debe tener entre 7 y 10 dígitos.")
        self._telefono = valor

    def describir(self) -> str:
        return f"Cliente #{self.id}: {self.nombre} (doc. {self.documento})"


# =====================================================================
# 3. SERVICIO (ABSTRACTA) Y SERVICIOS ESPECIALIZADOS
# =====================================================================

class Servicio(EntidadBase, ABC):
    """Clase abstracta base de todos los servicios que ofrece Software FJ."""

    def __init__(self, codigo: str, nombre: str, tarifa_hora: float):
        if not isinstance(codigo, str) or not codigo.strip():
            raise DatosInvalidosError("El código del servicio es obligatorio.")
        if not isinstance(nombre, str) or not nombre.strip():
            raise DatosInvalidosError("El nombre del servicio es obligatorio.")
        if not isinstance(tarifa_hora, (int, float)) or isinstance(tarifa_hora, bool) or tarifa_hora <= 0:
            raise DatosInvalidosError("La tarifa por hora debe ser un número positivo.")
        self.codigo = codigo.strip()
        self.nombre = nombre.strip()
        self._tarifa_hora = float(tarifa_hora)  # encapsulada: solo se usa dentro de la jerarquía
        self._disponible = True  # todo servicio nace disponible
        super().__init__()  # el id se genera solo si los datos fueron válidos

    @property
    def disponible(self) -> bool:
        return self._disponible

    def deshabilitar(self) -> None:
        """Marca el servicio como no disponible."""
        self._disponible = False

    def habilitar(self) -> None:
        """Marca el servicio como disponible."""
        self._disponible = True

    def _aplicar_ajustes(self, costo: float, impuesto: float, descuento: float) -> float:
        """Aplica descuento e impuesto (fracciones entre 0 y 1) al costo base."""
        for etiqueta, valor in (("impuesto", impuesto), ("descuento", descuento)):
            if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not 0 <= valor <= 1:
                raise DatosInvalidosError(f"El {etiqueta} debe ser un valor entre 0 y 1.")
        total = costo * (1 - descuento) * (1 + impuesto)  # primero descuento, luego impuesto
        if total < 0:
            raise CalculoInconsistenteError("El costo total calculado es negativo.")
        return round(total, 2)

    def calcular_costo_simple(self, duracion: float) -> float:
        """Variante 1 (sobrecarga): costo sin impuestos ni descuentos."""
        return self.calcular_costo(duracion)

    def calcular_costo_con_impuesto(self, duracion: float, impuesto: float) -> float:
        """Variante 2 (sobrecarga): costo solo con impuesto."""
        return self.calcular_costo(duracion, impuesto=impuesto)

    @abstractmethod
    def validar_parametros(self, **kwargs) -> None:
        """Valida los parámetros propios de cada servicio."""

    @abstractmethod
    def calcular_costo(self, duracion: float, *args,
                       impuesto: float = 0, descuento: float = 0, **kwargs) -> float:
        """Calcula el costo; variantes con impuesto y/o descuento opcionales."""

    @abstractmethod
    def describir(self) -> str:
        """Descripción textual del servicio."""


class ReservaSala(Servicio):
    """Servicio de reserva de salas para reuniones, talleres o eventos."""

    def __init__(self, codigo: str, nombre: str, tarifa_hora: float, capacidad: int):
        # la capacidad se valida primero: si es inválida no se crea ningún objeto
        if type(capacidad) is not int or capacidad < 1:
            raise DatosInvalidosError("La capacidad de la sala debe ser un entero mayor que cero.")
        super().__init__(codigo, nombre, tarifa_hora)  # valida código, nombre y tarifa
        self.capacidad = capacidad  # personas máximas que admite la sala

    def validar_parametros(self, **kwargs) -> None:
        """La reserva de sala exige indicar cuántas personas asistirán."""
        if "personas" not in kwargs:
            raise DatosInvalidosError("Falta el parámetro 'personas' para reservar una sala.")
        personas = kwargs["personas"]
        if type(personas) is not int or personas < 1:
            raise DatosInvalidosError("El número de personas debe ser un entero mayor que cero.")
        if personas > self.capacidad:
            raise DatosInvalidosError(
                f"{personas} personas superan la capacidad de la sala ({self.capacidad}).")

    def calcular_costo(self, duracion: float, *args,
                       impuesto: float = 0, descuento: float = 0, **kwargs) -> float:
        """Costo = tarifa por hora x horas, con descuento e impuesto opcionales."""
        if not isinstance(duracion, (int, float)) or isinstance(duracion, bool) or duracion <= 0:
            raise DatosInvalidosError("La duración debe ser un número positivo de horas.")
        costo_base = self._tarifa_hora * duracion  # costo antes de ajustes
        return self._aplicar_ajustes(costo_base, impuesto, descuento)

    def describir(self) -> str:
        return f"Sala '{self.nombre}' (capacidad: {self.capacidad} personas)"


class AlquilerEquipo(Servicio):
    """Servicio de alquiler de equipos (el costo depende de la cantidad)."""

    def __init__(self, codigo: str, nombre: str, tarifa_hora: float, stock: int):
        super().__init__(codigo, nombre, tarifa_hora)
        if not isinstance(stock, int) or isinstance(stock, bool) or stock <= 0:
            raise DatosInvalidosError("El stock debe ser un entero positivo.")
        self.stock = stock

    def validar_parametros(self, **kwargs) -> None:
        cantidad = kwargs.get("cantidad", 1)  # si no se indica, se alquila una unidad
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            raise DatosInvalidosError("La cantidad de equipos debe ser un entero positivo.")
        if cantidad > self.stock:
            raise DatosInvalidosError("No hay suficientes equipos en stock.")

    def calcular_costo(self, duracion: float, *args,
                       impuesto: float = 0, descuento: float = 0,
                       **kwargs) -> float:
        if not isinstance(duracion, (int, float)) or isinstance(duracion, bool) or duracion <= 0:
            raise DatosInvalidosError("La duracion debe ser positiva.")
        cantidad = args[0] if args else kwargs.get("cantidad", 1)  # cantidad posicional u opcional
        costo = self._tarifa_hora * duracion * cantidad
        return self._aplicar_ajustes(costo, impuesto, descuento)

    def describir(self) -> str:
        return f"Equipo: {self.nombre}, stock {self.stock}"


class AsesoriaEspecializada(Servicio):
    """Asesoría con recargo según el nivel del asesor."""

    RECARGOS = {"junior": 0.0, "senior": 0.20, "experto": 0.50}  # recargo por nivel

    def __init__(self, codigo: str, nombre: str, tarifa_hora: float, nivel: str):
        super().__init__(codigo, nombre, tarifa_hora)
        if not isinstance(nivel, str) or nivel.lower() not in self.RECARGOS:
            raise DatosInvalidosError("El nivel debe ser junior, senior o experto.")
        self.nivel = nivel.lower()

    def validar_parametros(self, **kwargs) -> None:
        tema = kwargs.get("tema")
        if not isinstance(tema, str) or len(tema.strip()) < 3:
            raise DatosInvalidosError("Debe indicar el tema de la asesoría.")

    def calcular_costo(self, duracion: float, *args,
                       impuesto: float = 0, descuento: float = 0,
                       **kwargs) -> float:
        if not isinstance(duracion, (int, float)) or isinstance(duracion, bool) or duracion <= 0:
            raise DatosInvalidosError("La duracion debe ser positiva.")
        costo = self._tarifa_hora * duracion * (1 + self.RECARGOS[self.nivel])
        return self._aplicar_ajustes(costo, impuesto, descuento)

    def describir(self) -> str:
        return f"Asesoría {self.nivel}: {self.nombre}"


# =====================================================================
# 4. RESERVA
# =====================================================================

class Reserva(EntidadBase):
    """Integra cliente, servicio, duración y estado."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    FALLIDA = "FALLIDA"

    def __init__(self, cliente: Cliente, servicio: Servicio, duracion: float, **parametros):
        super().__init__()
        if not isinstance(cliente, Cliente):
            raise ReservaInvalidaError("La reserva requiere un cliente válido.")
        if not isinstance(servicio, Servicio):
            raise ReservaInvalidaError("La reserva requiere un servicio válido.")
        if not isinstance(duracion, (int, float)) or isinstance(duracion, bool) or duracion <= 0:
            raise ReservaInvalidaError("La duración debe ser un número positivo.")
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.parametros = parametros  # datos propios del servicio (personas, cantidad, tema...)
        self._estado = self.PENDIENTE
        self._costo_total = None

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_total(self):
        return self._costo_total

    def confirmar(self) -> None:
        """Confirma la reserva si está pendiente y el servicio lo permite."""
        if self._estado != self.PENDIENTE:
            raise OperacionNoPermitidaError(
                f"No se puede confirmar una reserva en estado {self._estado}.")
        if not self.servicio.disponible:
            raise ServicioNoDisponibleError(f"El servicio '{self.servicio.nombre}' no está disponible.")
        self.servicio.validar_parametros(**self.parametros)  # validación polimórfica
        self._estado = self.CONFIRMADA
        logger.info("Reserva #%s confirmada.", self.id)

    def cancelar(self) -> None:
        """Cancela la reserva si aún no está cancelada ni fallida."""
        if self._estado in (self.CANCELADA, self.FALLIDA):
            raise OperacionNoPermitidaError(
                f"No se puede cancelar una reserva en estado {self._estado}.")
        self._estado = self.CANCELADA
        logger.info("Reserva #%s cancelada.", self.id)

    def procesar(self, impuesto: float = 0.19, descuento: float = 0.0) -> float:
        """Confirma la reserva y calcula su costo (try/except/else/finally + encadenamiento)."""
        estado_inicial = self._estado
        try:
            self.confirmar()
            costo = self.servicio.calcular_costo(
                self.duracion, impuesto=impuesto, descuento=descuento, **self.parametros)
        except SoftwareFJError as error:
            if estado_inicial == self.PENDIENTE:  # solo se marca fallida si estaba pendiente
                self._estado = self.FALLIDA
            logger.error("Reserva #%s falló: %s", self.id, error)
            # encadenamiento de excepciones: conserva la causa original con "from"
            raise ReservaInvalidaError(f"No se pudo procesar la reserva #{self.id}: {error}") from error
        else:
            self._costo_total = costo  # solo si no hubo errores
            logger.info("Reserva #%s procesada. Costo: $%s", self.id, costo)
            return costo
        finally:
            logger.info("Fin del intento de procesamiento de la reserva #%s (estado %s).",
                        self.id, self._estado)

    def describir(self) -> str:
        costo = f" | ${self._costo_total:,.2f}" if self._costo_total is not None else ""
        return (f"Reserva #{self.id} | {self.cliente.nombre} | {self.servicio.describir()} | "
                f"{self.duracion} h | {self._estado}{costo}")


# =====================================================================
# 5. GESTOR DEL SISTEMA Y SIMULACIÓN
# =====================================================================

class GestorSoftwareFJ:
    """Administra las listas internas de clientes, servicios y reservas."""

    def __init__(self):
        self.clientes = []
        self.servicios = []
        self.reservas = []

    def registrar_cliente(self, **datos) -> Cliente:
        try:
            cliente = Cliente(**datos)
        except TypeError as error:  # parámetros faltantes o inesperados
            raise DatosInvalidosError(f"Parámetros faltantes o inesperados: {error}") from error
        if any(c.documento == cliente.documento for c in self.clientes):
            raise DatosInvalidosError("Ya existe un cliente con ese documento.")
        self.clientes.append(cliente)
        logger.info("Cliente registrado: %s", cliente)
        return cliente

    def agregar_servicio(self, clase_servicio, **datos) -> Servicio:
        try:
            servicio = clase_servicio(**datos)
        except TypeError as error:
            raise DatosInvalidosError(f"Parámetros faltantes o inesperados: {error}") from error
        self.servicios.append(servicio)
        logger.info("Servicio creado: %s", servicio)
        return servicio

    def crear_reserva(self, cliente, servicio, duracion, **parametros) -> Reserva:
        reserva = Reserva(cliente, servicio, duracion, **parametros)
        self.reservas.append(reserva)
        logger.info("Reserva creada: %s", reserva)
        return reserva


def ejecutar_operacion(numero: int, descripcion: str, accion):
    """Ejecuta una operación; ante cualquier error lo registra y el programa continúa."""
    print(f"\n[{numero:02d}] {descripcion}")
    try:
        resultado = accion()
    except SoftwareFJError as error:  # errores controlados del dominio
        logger.error("Operación %02d (%s) falló: %s", numero, descripcion, error)
        causa = f" [causa: {type(error.__cause__).__name__}]" if error.__cause__ else ""
        print(f"     ERROR CONTROLADO -> {error}{causa}")
    except Exception as error:  # cualquier error inesperado: el sistema no se cae
        logger.critical("Operación %02d con error inesperado: %r", numero, error)
        print(f"     ERROR INESPERADO -> {error!r}")
    else:
        print(f"     OK -> {resultado}")
        return resultado
    finally:
        logger.info("Operación %02d finalizada.", numero)
    return None


def simular() -> None:
    """Ejecuta 14 operaciones (válidas e inválidas) para demostrar la robustez."""
    logger.info("===== INICIO DE LA SIMULACIÓN =====")
    sistema = GestorSoftwareFJ()

    # --- Clientes ---
    ana = ejecutar_operacion(1, "Registrar cliente válido",
        lambda: sistema.registrar_cliente(nombre="Ana Torres", documento="1020304050",
                                          correo="ana@correo.com", telefono="3101234567"))
    ejecutar_operacion(2, "Registrar cliente con correo inválido",
        lambda: sistema.registrar_cliente(nombre="Luis Pérez", documento="1090807060",
                                          correo="luis-correo", telefono="3119876543"))
    ejecutar_operacion(3, "Registrar cliente con parámetro faltante (sin teléfono)",
        lambda: sistema.registrar_cliente(nombre="Marta Ruiz", documento="1055566677",
                                          correo="marta@correo.com"))
    carlos = ejecutar_operacion(4, "Registrar segundo cliente válido",
        lambda: sistema.registrar_cliente(nombre="Carlos Díaz", documento="79123456",
                                          correo="carlos@correo.com", telefono="3205557788"))

    # --- Servicios ---
    sala = ejecutar_operacion(5, "Crear servicio ReservaSala válido",
        lambda: sistema.agregar_servicio(ReservaSala, codigo="S01", nombre="Sala Júpiter",
                                         tarifa_hora=50000, capacidad=10))
    ejecutar_operacion(6, "Crear ReservaSala con capacidad negativa",
        lambda: sistema.agregar_servicio(ReservaSala, codigo="S02", nombre="Sala Marte",
                                         tarifa_hora=40000, capacidad=-5))
    equipo = ejecutar_operacion(7, "Crear servicio AlquilerEquipo válido",
        lambda: sistema.agregar_servicio(AlquilerEquipo, codigo="E01", nombre="Portátil Pro",
                                         tarifa_hora=8000, stock=5))
    asesoria = ejecutar_operacion(8, "Crear servicio AsesoriaEspecializada válido",
        lambda: sistema.agregar_servicio(AsesoriaEspecializada, codigo="A01", nombre="Asesoría en Python",
                                         tarifa_hora=70000, nivel="experto"))

    # --- Reservas ---
    def reserva_exitosa():
        reserva = sistema.crear_reserva(ana, sala, 3, personas=8)
        reserva.procesar(impuesto=0.19, descuento=0.10)
        return reserva
    reserva_ok = ejecutar_operacion(9, "Reserva de sala exitosa (con impuesto y descuento)", reserva_exitosa)

    ejecutar_operacion(10, "Reserva de sala fallida: personas superan la capacidad",
        lambda: sistema.crear_reserva(carlos, sala, 2, personas=25).procesar())

    def servicio_no_disponible():
        equipo.deshabilitar()  # simula equipo fuera de servicio
        return sistema.crear_reserva(carlos, equipo, 4, cantidad=2).procesar()
    ejecutar_operacion(11, "Reserva fallida: servicio no disponible", servicio_no_disponible)

    def asesoria_exitosa():
        reserva = sistema.crear_reserva(carlos, asesoria, 2, tema="Excepciones en Python")
        reserva.procesar()
        return reserva
    ejecutar_operacion(12, "Reserva de asesoría exitosa", asesoria_exitosa)

    ejecutar_operacion(13, "Reserva con descuento inconsistente (150%)",
        lambda: sistema.crear_reserva(ana, sala, 1, personas=4).procesar(descuento=1.5))

    ejecutar_operacion(14, "Reserva sin cliente (None)",
        lambda: sistema.crear_reserva(None, sala, 1, personas=2))

    # --- Cancelaciones ---
    if reserva_ok:
        def cancelar_reserva():
            reserva_ok.cancelar()
            return reserva_ok
        ejecutar_operacion(15, "Cancelar reserva confirmada", cancelar_reserva)
        ejecutar_operacion(16, "Cancelar de nuevo la misma reserva (no permitido)", reserva_ok.cancelar)

    # --- Resumen ---
    print("\n" + "=" * 60)
    print(f"Clientes: {len(sistema.clientes)} | Servicios: {len(sistema.servicios)} | "
          f"Reservas: {len(sistema.reservas)}")
    for reserva in sistema.reservas:
        print("  -", reserva)
    print("El sistema terminó sin interrupciones. Revise 'software_fj.log'.")
    logger.info("===== FIN DE LA SIMULACIÓN =====")


if __name__ == "__main__":
    simular()
