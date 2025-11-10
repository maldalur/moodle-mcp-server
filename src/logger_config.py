import logging
import sys
from pathlib import Path
from datetime import datetime

# Colores para consola (opcional, solo si el terminal lo soporta)
class LogColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ColoredFormatter(logging.Formatter):
    """Formatter personalizado con colores para la consola."""
    
    FORMATS = {
        logging.DEBUG: LogColors.OKCYAN + "%(levelname)-8s" + LogColors.ENDC + " | %(name)s | %(message)s",
        logging.INFO: LogColors.OKGREEN + "%(levelname)-8s" + LogColors.ENDC + " | %(name)s | %(message)s",
        logging.WARNING: LogColors.WARNING + "%(levelname)-8s" + LogColors.ENDC + " | %(name)s | %(message)s",
        logging.ERROR: LogColors.FAIL + "%(levelname)-8s" + LogColors.ENDC + " | %(name)s | %(message)s",
        logging.CRITICAL: LogColors.BOLD + LogColors.FAIL + "%(levelname)-8s" + LogColors.ENDC + " | %(name)s | %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(levelname)-8s | %(name)s | %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str = None,
    console: bool = True,
    file_level: int = logging.DEBUG
) -> logging.Logger:
    """
    Configura y retorna un logger con handlers para consola y/o archivo.
    
    Args:
        name: Nombre del logger (generalmente __name__)
        level: Nivel de logging para consola (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta al archivo de log (opcional)
        console: Si True, añade handler de consola
        file_level: Nivel de logging para archivo (por defecto DEBUG para capturar todo)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Captura todo, los handlers filtran
    
    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger
    
    # Handler de consola con colores
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
    
    # Handler de archivo (sin colores)
    if log_file:
        # Crear directorio de logs si no existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger ya configurado o crea uno nuevo con configuración por defecto.
    
    Args:
        name: Nombre del logger (generalmente __name__)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Si no tiene handlers, configurar con valores por defecto
    if not logger.handlers:
        return setup_logger(
            name=name,
            level=logging.INFO,
            log_file=f"logs/moodle_feedback_{datetime.now().strftime('%Y%m%d')}.log",
            console=True
        )
    
    return logger

def set_level(logger: logging.Logger, console_level: int = None, file_level: int = None):
    """
    Cambia el nivel de logging de un logger existente.
    
    Args:
        logger: Logger a modificar
        console_level: Nuevo nivel para consola (opcional)
        file_level: Nuevo nivel para archivo (opcional)
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and console_level is not None:
            handler.setLevel(console_level)
        elif isinstance(handler, logging.FileHandler) and file_level is not None:
            handler.setLevel(file_level)

# Logger principal del proyecto
def get_main_logger() -> logging.Logger:
    """Obtiene el logger principal del proyecto con configuración completa."""
    return setup_logger(
        name="moodle_feedback",
        level=logging.INFO,
        log_file=f"logs/moodle_feedback_{datetime.now().strftime('%Y%m%d')}.log",
        console=True,
        file_level=logging.DEBUG
    )
