import json
import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, Any
from logger_config import get_logger

logger = get_logger(__name__)

class SubmissionCache:
    """
    Gestiona el caché de entregas para evitar reprocesar trabajos que no han cambiado.
    Guarda información sobre cada entrega (usuario, tarea, hash, timestamp, estado).
    """
    
    def __init__(self, cache_file: str = "submission_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Carga el caché desde el archivo JSON."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error cargando caché: {e}. Creando nuevo caché.")
                return {}
        return {}
    
    def _save_cache(self):
        """Guarda el caché en el archivo JSON."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error guardando caché: {e}")
    
    def _compute_hash(self, data: Any) -> str:
        """
        Calcula un hash MD5 de los datos de la entrega.
        
        Args:
            data: Puede ser un dict, string, lista de archivos, etc.
        
        Returns:
            Hash MD5 en hexadecimal
        """
        # Convertir los datos a string JSON ordenado para consistencia
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            data_str = json.dumps(sorted([str(item) for item in data]))
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()
    
    def _get_key(self, course_id: int, assignment_id: int, student_id: int, assignment_type: str = "vpl") -> str:
        """
        Genera una clave única para identificar una entrega.
        
        Args:
            course_id: ID del curso
            assignment_id: ID de la tarea (vplid o assignmentid)
            student_id: ID del estudiante
            assignment_type: Tipo de tarea ('vpl' o 'assign')
        
        Returns:
            Clave en formato: "type_courseID_assignmentID_studentID"
        """
        return f"{assignment_type}_{course_id}_{assignment_id}_{student_id}"
    
    def has_changed(self, course_id: int, assignment_id: int, student_id: int, 
                    submission_data: Any, assignment_type: str = "vpl") -> bool:
        """
        Verifica si una entrega ha cambiado comparando con el caché.
        
        Args:
            course_id: ID del curso
            assignment_id: ID de la tarea
            student_id: ID del estudiante
            submission_data: Datos de la entrega (dict con respuesta API o lista de archivos)
            assignment_type: Tipo de tarea ('vpl' o 'assign')
        
        Returns:
            True si la entrega ha cambiado o es nueva, False si no ha cambiado
        """
        key = self._get_key(course_id, assignment_id, student_id, assignment_type)
        new_hash = self._compute_hash(submission_data)
        
        if key not in self.cache:
            # Es una entrega nueva
            return True
        
        cached_entry = self.cache[key]
        old_hash = cached_entry.get("hash")
        
        # Comparar hashes
        return old_hash != new_hash
    
    def update(self, course_id: int, assignment_id: int, student_id: int, 
               submission_data: Any, assignment_type: str = "vpl",
               student_username: str = "", assignment_name: str = "",
               status: str = "processed", additional_info: Dict = None):
        """
        Actualiza el caché con una nueva entrega o modifica una existente.
        
        Args:
            course_id: ID del curso
            assignment_id: ID de la tarea
            student_id: ID del estudiante
            submission_data: Datos de la entrega
            assignment_type: Tipo de tarea ('vpl' o 'assign')
            student_username: Nombre de usuario del estudiante
            assignment_name: Nombre de la tarea
            status: Estado de procesamiento ('processed', 'error', 'pending', etc.)
            additional_info: Información adicional a guardar (calificación, feedback, etc.)
        """
        key = self._get_key(course_id, assignment_id, student_id, assignment_type)
        new_hash = self._compute_hash(submission_data)
        
        entry = {
            "course_id": course_id,
            "assignment_id": assignment_id,
            "student_id": student_id,
            "student_username": student_username,
            "assignment_name": assignment_name,
            "assignment_type": assignment_type,
            "hash": new_hash,
            "status": status,
            "last_updated": datetime.now().isoformat(),
            "first_seen": self.cache.get(key, {}).get("first_seen", datetime.now().isoformat())
        }
        
        # Añadir información adicional si se proporciona
        if additional_info:
            entry.update(additional_info)
        
        self.cache[key] = entry
        self._save_cache()
    
    def get_entry(self, course_id: int, assignment_id: int, student_id: int, 
                  assignment_type: str = "vpl") -> Optional[Dict]:
        """
        Obtiene la entrada del caché para una entrega específica.
        
        Returns:
            Dict con la información de la entrega o None si no existe
        """
        key = self._get_key(course_id, assignment_id, student_id, assignment_type)
        return self.cache.get(key)
    
    def get_all_entries(self, course_id: Optional[int] = None, 
                       assignment_id: Optional[int] = None) -> list:
        """
        Obtiene todas las entregas del caché, opcionalmente filtradas por curso o tarea.
        
        Args:
            course_id: Filtrar por ID de curso (opcional)
            assignment_id: Filtrar por ID de tarea (opcional)
        
        Returns:
            Lista de entradas que cumplen los criterios
        """
        entries = []
        for entry in self.cache.values():
            if course_id is not None and entry.get("course_id") != course_id:
                continue
            if assignment_id is not None and entry.get("assignment_id") != assignment_id:
                continue
            entries.append(entry)
        return entries
    
    def clear_cache(self):
        """Limpia todo el caché."""
        self.cache = {}
        self._save_cache()
        logger.info("Caché limpiado completamente")
    
    def remove_entry(self, course_id: int, assignment_id: int, student_id: int, 
                     assignment_type: str = "vpl"):
        """Elimina una entrada específica del caché."""
        key = self._get_key(course_id, assignment_id, student_id, assignment_type)
        if key in self.cache:
            del self.cache[key]
            self._save_cache()
            return True
        return False
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            Dict con estadísticas: total de entregas, por estado, por tipo, etc.
        """
        stats = {
            "total_entries": len(self.cache),
            "by_status": {},
            "by_type": {},
            "by_course": {}
        }
        
        for entry in self.cache.values():
            # Por estado
            status = entry.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Por tipo
            atype = entry.get("assignment_type", "unknown")
            stats["by_type"][atype] = stats["by_type"].get(atype, 0) + 1
            
            # Por curso
            course = entry.get("course_id", "unknown")
            stats["by_course"][course] = stats["by_course"].get(course, 0) + 1
        
        return stats
