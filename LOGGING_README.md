# Configuración de Logging para Moodle Feedback

## Niveles de Logging

El sistema utiliza los niveles estándar de Python logging:

- **DEBUG**: Información detallada para diagnóstico (incluye respuestas API, hashes, etc.)
- **INFO**: Eventos normales del programa (entregas procesadas, estadísticas, etc.)
- **WARNING**: Situaciones inesperadas pero recuperables
- **ERROR**: Errores que impiden funcionalidades específicas
- **CRITICAL**: Errores graves que pueden detener el programa

## Archivos Modificados

### `src/logger_config.py` (NUEVO)
Módulo centralizado de configuración de logging con:
- Formatter con colores para consola
- Configuración automática de handlers (consola + archivo)
- Función `get_logger()` para obtener loggers configurados
- Función `get_main_logger()` para el logger principal

### `src/moodle_client.py`
- Reemplazados prints con `logger.debug()`, `logger.error()`, etc.
- Log de respuestas API en nivel DEBUG
- Log de errores en nivel ERROR

### `src/main.py`
- Reemplazados prints con niveles apropiados:
  - `logger.info()` para estadísticas y entregas procesadas
  - `logger.debug()` para entregas sin cambios (reduce ruido)
  - `logger.error()` para errores de descarga

### `src/submission_cache.py`
- Log de operaciones de caché (cargar, guardar, limpiar)
- Warnings para errores recuperables

## Uso del Sistema

### Ejecución Normal (INFO level)
```powershell
python src\main.py
```
**Muestra**: Estadísticas, entregas procesadas, resumen final

### Modo Detallado (DEBUG level)
Para ver también entregas sin cambios y respuestas API:

**Opción 1: Variable de entorno**
```powershell
$env:LOG_LEVEL="DEBUG"; python src\main.py
```

**Opción 2: Modificar código temporalmente**
En `src/main.py`, cambiar:
```python
logger = get_main_logger()  # Por defecto INFO
```
a:
```python
import logging
logger = get_main_logger()
from logger_config import set_level
set_level(logger, console_level=logging.DEBUG)
```

### Solo Errores y Warnings (WARNING level)
```powershell
$env:LOG_LEVEL="WARNING"; python src\main.py
```

## Archivos de Log

Los logs se guardan automáticamente en:
```
logs/moodle_feedback_YYYYMMDD.log
```

Por ejemplo:
- `logs/moodle_feedback_20251107.log`

Los archivos contienen:
- Timestamp completo
- Nivel de log
- Módulo/función que genera el log
- Mensaje

Ejemplo de entrada:
```
2025-11-07 14:30:15 | INFO     | moodle_feedback | Processing Course: Programación I (ID: 10)
2025-11-07 14:30:16 | DEBUG    | moodle_client | Obteniendo entrega VPL: cmid=301, vplid=201, student_id=1001
2025-11-07 14:30:17 | ERROR    | moodle_client | Error downloading file test.py: Connection timeout
```

## Personalización

### Cambiar nivel de consola globalmente

En `src/logger_config.py`, función `get_main_logger()`:
```python
return setup_logger(
    name="moodle_feedback",
    level=logging.DEBUG,  # Cambiar aquí (DEBUG, INFO, WARNING, ERROR)
    log_file=f"logs/moodle_feedback_{datetime.now().strftime('%Y%m%d')}.log",
    console=True,
    file_level=logging.DEBUG
)
```

### Cambiar ubicación de logs

En `src/logger_config.py`, modificar `log_file`:
```python
log_file="mi_carpeta/logs.log"
```

### Deshabilitar colores en consola

Si los colores causan problemas, modificar `ColoredFormatter` para usar formato simple:
```python
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = "%(levelname)-8s | %(name)s | %(message)s"
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)
```

### Añadir logger a nuevos módulos

```python
from logger_config import get_logger

logger = get_logger(__name__)

# Usar en tu código
logger.debug("Mensaje de debug")
logger.info("Mensaje informativo")
logger.warning("Advertencia")
logger.error("Error")
logger.critical("Error crítico")
```

## Ejemplos de Salida

### Consola (INFO level) - Colores
```
INFO     | moodle_feedback | ==============================================================
INFO     | moodle_feedback | ESTADÍSTICAS DEL CACHÉ
INFO     | moodle_feedback | ==============================================================
INFO     | moodle_feedback | Total de entregas en caché: 25
INFO     | moodle_feedback | ==============================================================

INFO     | moodle_feedback | Processing Course: Programación I (ID: 10)
INFO     | moodle_feedback | 
Encontradas 3 tareas de asignación en el curso
INFO     | moodle_feedback | 
------------------------------------------------------------
INFO     | moodle_feedback | ASIGNACIÓN: Ensayo Final (ID: 123)
INFO     | moodle_feedback | ------------------------------------------------------------
INFO     | moodle_feedback |   ✓ alumno1 (ID: 456) - NUEVA o MODIFICADA
INFO     | moodle_feedback |       - downloads/ensayo.pdf
```

### Archivo de log (DEBUG level) - Sin colores
```
2025-11-07 14:30:15 | INFO     | moodle_feedback | Processing Course: Programación I (ID: 10)
2025-11-07 14:30:16 | DEBUG    | moodle_client | Obteniendo entrega VPL: cmid=301, vplid=201, student_id=1001
2025-11-07 14:30:17 | DEBUG    | moodle_client | Respuesta API: {'files': [{'name': 'main.py', 'data': '...'}]}
2025-11-07 14:30:18 | INFO     | moodle_feedback |   ✓ alumno1 (ID: 1001) - NUEVA o MODIFICADA
2025-11-07 14:30:19 | INFO     | moodle_feedback |     Archivos descargados: 1
2025-11-07 14:30:20 | DEBUG    | moodle_feedback |   ○ alumno2 (ID: 1002) - SIN CAMBIOS (omitida)
```

## Ventajas del Sistema

1. **Flexible**: Cambia niveles sin modificar código
2. **Profesional**: Logs estructurados con timestamps
3. **Depurable**: DEBUG level muestra todo el flujo
4. **Limpio**: INFO level muestra solo lo importante
5. **Persistente**: Logs guardados automáticamente por fecha
6. **Coloreado**: Fácil de leer en consola
7. **Escalable**: Fácil añadir logging a nuevos módulos

## Solución de Problemas

### Los colores no se muestran correctamente
Desactivar colores o usar terminal compatible (Windows Terminal, PowerShell 7+)

### Los logs no se guardan
Verificar permisos de escritura en carpeta `logs/`

### Demasiado output en consola
Cambiar nivel a WARNING: `set_level(logger, console_level=logging.WARNING)`

### No veo entregas sin cambios
Es intencional (nivel DEBUG). Para verlas: cambiar nivel a DEBUG
