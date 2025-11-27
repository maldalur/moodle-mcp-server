"""
Módulo de análisis inteligente de entregas con IA
Analiza entregas, genera feedback y detecta estudiantes en riesgo
"""
import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from logger_config import get_logger
import ollama

logger = get_logger(__name__)

# Konfigurazioa - Urruneko Ollama zerbitzaria
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://10.2.50.232:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:30b-a3b")

# JSON Schema erantzunerako - Ollama-k formatu hau erabiliko du
SUBMISSION_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "string",
            "description": "Feedback detallado y constructivo para el estudiante sobre su entrega"
        },
        "grade": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 10,
            "description": "Calificación sugerida de 0 a 10, o null si no se puede evaluar"
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de puntos fuertes identificados en la entrega"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de puntos débiles o áreas de mejora"
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de recomendaciones específicas para mejorar"
        },
        "code_quality": {
            "type": ["object", "null"],
            "properties": {
                "readability": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Puntuación de legibilidad del código (1-5)"
                },
                "structure": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Puntuación de estructura y organización (1-5)"
                },
                "documentation": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Puntuación de documentación y comentarios (1-5)"
                },
                "best_practices": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Puntuación de buenas prácticas (1-5)"
                }
            },
            "description": "Evaluación de calidad del código (solo para entregas de programación)"
        },
        "completeness": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Porcentaje de completitud de los requisitos (0-100)"
        },
        "summary": {
            "type": "string",
            "description": "Resumen breve de una línea sobre la entrega"
        }
    },
    "required": ["feedback", "grade", "strengths", "weaknesses", "recommendations", "completeness", "summary"]
}

# JSON Schema foro erantzunetarako
FORUM_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Erantzun proposatua foroaren mezuari, profesionala eta lagungarria"
        },
        "tone": {
            "type": "string",
            "enum": ["formal", "friendly", "educational", "supportive"],
            "description": "Erantzunaren tonua"
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Erantzunean azpimarratutako puntu nagusiak"
        },
        "follow_up_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Jarraipenerako galdera posibleak ikaslearentzat"
        },
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "description": "Gomendatutako baliabideak edo erreferentziak"
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "urgent"],
            "description": "Erantzunaren lehentasuna"
        },
        "category": {
            "type": "string",
            "enum": ["question", "doubt", "help_request", "discussion", "feedback", "other"],
            "description": "Mezuaren kategoria"
        },
        "summary": {
            "type": "string",
            "description": "Proposatutako erantzunaren laburpena"
        }
    },
    "required": ["response", "tone", "key_points", "priority", "category", "summary"]
}

# JSON Schema FORO-TAREA ebaluaziorako (ikasleen entregak foroan)
FORUM_TASK_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "string",
            "description": "Feedback detallado y constructivo para el estudiante sobre su aportación al foro"
        },
        "grade": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 10,
            "description": "Calificación sugerida de 0 a 10, o null si no se puede evaluar"
        },
        "participation_quality": {
            "type": "object",
            "properties": {
                "relevance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Relevancia de la aportación respecto al tema (1-5)"
                },
                "depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Profundidad del análisis o argumentación (1-5)"
                },
                "originality": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Originalidad y aportación de valor (1-5)"
                },
                "clarity": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Claridad en la expresión escrita (1-5)"
                },
                "interaction": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Interacción con otros participantes (1-5)"
                }
            },
            "description": "Evaluación de la calidad de participación"
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Puntos fuertes de la aportación del estudiante"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Áreas de mejora en la participación"
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Recomendaciones específicas para mejorar"
        },
        "meets_requirements": {
            "type": "boolean",
            "description": "Si la aportación cumple los requisitos mínimos de la tarea"
        },
        "word_count_adequate": {
            "type": "boolean",
            "description": "Si la extensión es adecuada"
        },
        "cited_sources": {
            "type": "boolean",
            "description": "Si se citan fuentes o referencias"
        },
        "responded_to_others": {
            "type": "boolean",
            "description": "Si el estudiante ha respondido a otros compañeros"
        },
        "summary": {
            "type": "string",
            "description": "Resumen breve de una línea sobre la participación"
        }
    },
    "required": ["feedback", "grade", "participation_quality", "strengths", "weaknesses", "recommendations", "meets_requirements", "summary"]
}


class AIAnalyzer:
    """
    Analiza entregas de estudiantes usando IA para:
    - Generar feedback detallado
    - Calificar según criterios
    - Identificar estudiantes en riesgo
    - Analizar progreso y patrones de entrega
    """
    
    def __init__(self, model: str = None, host: str = None, stream: bool = True, think: bool = False):
        """
        Inicializa el analizador de IA
        
        Args:
            model: Modelo a usar (por defecto desde env o qwen3:30b-a3b)
            host: URL del servidor Ollama (por defecto desde env o http://10.2.50.232:11434)
            stream: Si usar streaming para las respuestas
            think: Si habilitar el modo "thinking" del modelo (qwen3)
        """
        self.model = model or DEFAULT_MODEL
        self.host = host or OLLAMA_HOST
        self.stream = stream
        self.think = think
        
        # Crear cliente Ollama con el host especificado
        self.client = ollama.Client(host=self.host)
        
        logger.info(f"Inicializando AIAnalyzer:")
        logger.info(f"  - Modelo: {self.model}")
        logger.info(f"  - Host: {self.host}")
        logger.info(f"  - Streaming: {self.stream}")
        logger.info(f"  - Think mode: {self.think}")
    
    def analyze_submission(self, 
                          submission_data: Dict[str, Any],
                          assignment_criteria: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza una entrega individual
        
        Args:
            submission_data: Datos de la entrega (archivos, contenido, metadatos)
            assignment_criteria: Criterios de evaluación de la tarea
        
        Returns:
            Dict con análisis, feedback, calificación sugerida
        """
        try:
            # Leer contenido de archivos
            content = self._read_submission_files(submission_data.get('filenames', []))
            
            # Extraer URLs del contenido
            urls = self._extract_urls(content)
            
            # Analizar URLs si existen
            url_analysis = []
            if urls:
                logger.info(f"  Encontradas {len(urls)} URLs en la entrega")
                url_analysis = self._analyze_urls(urls)
            
            # Generar análisis con IA
            prompt = self._build_analysis_prompt(
                content=content,
                criteria=assignment_criteria,
                urls=url_analysis,
                metadata=submission_data
            )
            
            analysis = self._query_ai(prompt)
            
            return {
                'status': 'success',
                'content_length': len(content),
                'urls_found': len(urls),
                'url_analysis': url_analysis,
                'ai_feedback': analysis.get('feedback', ''),
                'suggested_grade': analysis.get('grade'),
                'strengths': analysis.get('strengths', []),
                'weaknesses': analysis.get('weaknesses', []),
                'recommendations': analysis.get('recommendations', []),
                'code_quality': analysis.get('code_quality'),
                'completeness': analysis.get('completeness', 0),
                'summary': analysis.get('summary', ''),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"  Error analizando entrega: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'analyzed_at': datetime.now().isoformat()
            }
    
    def analyze_submission_interactive(self, 
                                       submission_data: Dict[str, Any],
                                       assignment_criteria: Optional[str] = None,
                                       show_thinking: bool = True) -> Dict[str, Any]:
        """
        Analiza una entrega mostrando el progreso en tiempo real (streaming)
        
        Args:
            submission_data: Datos de la entrega
            assignment_criteria: Criterios de evaluación
            show_thinking: Si mostrar el proceso de "thinking" del modelo
        
        Returns:
            Dict con el análisis completo
        """
        print(f"\n{'='*60}")
        print(f"📝 Analizando entrega de: {submission_data.get('student_username', 'Desconocido')}")
        print(f"{'='*60}\n")
        
        try:
            # Leer contenido
            content = self._read_submission_files(submission_data.get('filenames', []))
            print(f"📁 Contenido leído: {len(content)} caracteres")
            
            # URLs
            urls = self._extract_urls(content)
            url_analysis = []
            if urls:
                print(f"🔗 URLs encontradas: {len(urls)}")
                url_analysis = self._analyze_urls(urls)
            
            # Construir prompt
            prompt = self._build_analysis_prompt(
                content=content,
                criteria=assignment_criteria,
                urls=url_analysis,
                metadata=submission_data
            )
            
            print(f"\n🤖 Consultando modelo {self.model}...\n")
            
            # Callback para mostrar progreso
            def on_chunk(text: str, is_thinking: bool):
                if is_thinking and show_thinking:
                    print(f"\033[90m{text}\033[0m", end='', flush=True)  # Gris para thinking
                elif not is_thinking:
                    print(text, end='', flush=True)
            
            # Consultar con streaming
            analysis = self._query_ai(prompt, on_chunk=on_chunk)
            
            print(f"\n\n{'='*60}")
            print("✅ Análisis completado")
            print(f"{'='*60}\n")
            
            return {
                'status': 'success',
                'content_length': len(content),
                'urls_found': len(urls),
                'url_analysis': url_analysis,
                'ai_feedback': analysis.get('feedback', ''),
                'suggested_grade': analysis.get('grade', None),
                'strengths': analysis.get('strengths', []),
                'weaknesses': analysis.get('weaknesses', []),
                'recommendations': analysis.get('recommendations', []),
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'analyzed_at': datetime.now().isoformat()
            }
    
    def _read_submission_files(self, filenames: List[str]) -> str:
        """Lee y combina el contenido de todos los archivos de la entrega"""
        content = ""
        for filepath in filenames:
            try:
                if not os.path.exists(filepath):
                    logger.warning(f"    Archivo no encontrado: {filepath}")
                    continue
                
                # Detectar tipo de archivo
                ext = os.path.splitext(filepath)[1].lower()
                
                if ext in ['.txt', '.md', '.py', '.java', '.js', '.html', '.css', '.json', '.xml']:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content += f"\n--- {os.path.basename(filepath)} ---\n"
                        content += f.read()
                else:
                    content += f"\n--- {os.path.basename(filepath)} (archivo binario) ---\n"
                    
            except Exception as e:
                logger.warning(f"    Error leyendo {filepath}: {e}")
        
        return content
    
    def _extract_urls(self, content: str) -> List[str]:
        """Extrae URLs del contenido"""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        return list(set(urls))  # Eliminar duplicados
    
    def _analyze_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Analiza las URLs encontradas en la entrega"""
        results = []
        for url in urls[:5]:  # Limitar a 5 URLs para no saturar
            try:
                # Verificar accesibilidad
                response = requests.head(url, timeout=5, allow_redirects=True)
                results.append({
                    'url': url,
                    'accessible': response.status_code < 400,
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', 'unknown')
                })
            except Exception as e:
                results.append({
                    'url': url,
                    'accessible': False,
                    'error': str(e)
                })
        return results
    
    def _build_analysis_prompt(self, 
                               content: str, 
                               criteria: Optional[str],
                               urls: List[Dict],
                               metadata: Dict) -> str:
        """Construye el prompt para el análisis con IA"""
        
        prompt = f"""Eres un profesor experto evaluando una entrega de estudiante.

INFORMACIÓN DE LA ENTREGA:
- Estudiante: {metadata.get('student_username', 'Desconocido')}
- Tarea: {metadata.get('assignment_name', 'Desconocida')}
- Fecha de última modificación: {metadata.get('timemodified', 'Desconocida')}

"""
        
        if criteria:
            prompt += f"""CRITERIOS DE EVALUACIÓN:
{criteria}

"""
        
        if urls:
            prompt += f"""ENLACES ENCONTRADOS ({len(urls)}):
"""
            for url_data in urls:
                status = "✓ Accesible" if url_data.get('accessible') else "✗ No accesible"
                prompt += f"- {url_data['url']} [{status}]\n"
            prompt += "\n"
        
        # Limitar contenido para no saturar el modelo
        max_content = 4000
        if len(content) > max_content:
            content = content[:max_content] + "\n... (contenido truncado) ..."
        
        prompt += f"""CONTENIDO DE LA ENTREGA:
{content}

INSTRUCCIONES:
1. Analiza el contenido en base a los criterios de evaluación (si existen)
2. Evalúa la calidad del trabajo y del código (si es programación)
3. Verifica si los enlaces funcionan y son relevantes
4. Proporciona feedback constructivo y específico
5. Sé justo pero exigente en la evaluación

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
{{
    "feedback": "Feedback detallado y constructivo para el estudiante explicando la evaluación",
    "grade": 7.5,
    "strengths": ["Punto fuerte 1", "Punto fuerte 2"],
    "weaknesses": ["Área de mejora 1", "Área de mejora 2"],
    "recommendations": ["Recomendación específica 1", "Recomendación específica 2"],
    "code_quality": {{
        "readability": 4,
        "structure": 3,
        "documentation": 2,
        "best_practices": 3
    }},
    "completeness": 75,
    "summary": "Resumen de una línea sobre la entrega"
}}

NOTAS:
- "grade": número de 0 a 10 (puede tener decimales), o null si no se puede evaluar
- "code_quality": solo incluir si es una entrega de programación, cada valor de 1 a 5
- "completeness": porcentaje de 0 a 100 de requisitos cumplidos
- Los arrays pueden tener de 1 a 5 elementos cada uno
"""
        return prompt
    
    def _query_ai(self, prompt: str, on_chunk: Optional[Callable[[str, bool], None]] = None) -> Dict[str, Any]:
        """
        Consulta al modelo de IA y parsea la respuesta
        
        Args:
            prompt: El prompt a enviar al modelo
            on_chunk: Callback opcional para procesar chunks en streaming
                     Recibe (texto, es_thinking) como parámetros
        
        Returns:
            Dict con la respuesta parseada del modelo
        """
        try:
            if self.stream:
                return self._query_ai_streaming(prompt, on_chunk)
            else:
                return self._query_ai_sync(prompt)
                
        except Exception as e:
            logger.error(f"  Error consultando IA: {e}")
            return {
                'feedback': f"Error: {str(e)}",
                'grade': None,
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
    
    def _query_ai_sync(self, prompt: str) -> Dict[str, Any]:
        """Consulta síncrona (sin streaming) al modelo"""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                think=self.think
            )
            
            content = response['message']['content']
            return json.loads(content)
            
        except json.JSONDecodeError:
            logger.warning("  Respuesta de IA no es JSON válido, extrayendo texto")
            return {
                'feedback': content if 'content' in locals() else "Error procesando respuesta",
                'grade': None,
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
    
    def _get_default_response(self, error_msg: str = "") -> Dict[str, Any]:
        """Erantzun lehenetsia erroreen kasuan"""
        return {
            'feedback': error_msg or "Error procesando respuesta",
            'grade': None,
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'code_quality': None,
            'completeness': 0,
            'summary': "Error en el análisis"
        }
    
    def _query_ai_sync(self, prompt: str) -> Dict[str, Any]:
        """Consulta síncrona (sin streaming) al modelo"""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                format=SUBMISSION_ANALYSIS_SCHEMA,  # JSON Schema erabili
                think=self.think
            )
            
            content = response['message']['content']
            result = json.loads(content)
            return self._validate_response(result)
            
        except json.JSONDecodeError:
            logger.warning("  Respuesta de IA no es JSON válido, extrayendo texto")
            return self._get_default_response(content if 'content' in locals() else "")
    
    def _query_ai_streaming(self, prompt: str, on_chunk: Optional[Callable[[str, bool], None]] = None) -> Dict[str, Any]:
        """
        Consulta con streaming al modelo
        
        Args:
            prompt: El prompt a enviar
            on_chunk: Callback para procesar cada chunk (texto, es_thinking)
        
        Returns:
            Dict con la respuesta completa parseada
        """
        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                format=SUBMISSION_ANALYSIS_SCHEMA,  # JSON Schema erabili
                think=self.think
            )
            
            in_thinking = False
            content = ''
            thinking = ''
            
            for chunk in stream:
                # Procesar thinking (si el modelo lo soporta)
                if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                    if not in_thinking:
                        in_thinking = True
                        logger.debug("  [Thinking mode activado]")
                    
                    thinking += chunk.message.thinking
                    
                    if on_chunk:
                        on_chunk(chunk.message.thinking, True)
                
                # Procesar contenido normal
                elif hasattr(chunk.message, 'content') and chunk.message.content:
                    if in_thinking:
                        in_thinking = False
                        logger.debug("  [Thinking mode finalizado]")
                    
                    content += chunk.message.content
                    
                    if on_chunk:
                        on_chunk(chunk.message.content, False)
            
            # Log del thinking si existió
            if thinking:
                logger.debug(f"  Thinking del modelo ({len(thinking)} chars)")
            
            logger.debug(f"  Respuesta completa ({len(content)} chars)")
            
            # Intentar parsear como JSON
            try:
                result = json.loads(content)
                return self._validate_response(result)
            except json.JSONDecodeError:
                logger.warning("  Respuesta no es JSON válido, intentando extraer")
                return self._extract_json_from_text(content)
                
        except Exception as e:
            logger.error(f"  Error en streaming: {e}")
            raise
    
    def _validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Balidatu eta osatu erantzuna beharrezko eremuak dituela"""
        validated = {
            'feedback': response.get('feedback', ''),
            'grade': response.get('grade'),
            'strengths': response.get('strengths', []),
            'weaknesses': response.get('weaknesses', []),
            'recommendations': response.get('recommendations', []),
            'code_quality': response.get('code_quality'),
            'completeness': response.get('completeness', 0),
            'summary': response.get('summary', '')
        }
        
        # Ziurtatu grade 0-10 tartean dagoela
        if validated['grade'] is not None:
            try:
                validated['grade'] = max(0, min(10, float(validated['grade'])))
            except (ValueError, TypeError):
                validated['grade'] = None
        
        # Ziurtatu completeness 0-100 tartean dagoela
        try:
            validated['completeness'] = max(0, min(100, int(validated['completeness'])))
        except (ValueError, TypeError):
            validated['completeness'] = 0
        
        return validated
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Intenta extraer JSON de un texto que puede contener otros elementos"""
        import re
        
        # Buscar bloques JSON en el texto
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                if 'feedback' in parsed or 'grade' in parsed:
                    return self._validate_response(parsed)
            except json.JSONDecodeError:
                continue
        
        # Si no se encuentra JSON válido, devolver el texto como feedback
        return self._get_default_response(text)
    
    def generate_student_report(self, 
                               student_submissions: List[Dict[str, Any]],
                               student_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un informe completo de un estudiante basado en todas sus entregas
        
        Args:
            student_submissions: Lista de entregas del estudiante con análisis
            student_info: Información del estudiante
        
        Returns:
            Informe con evaluación de riesgo, progreso, patrones
        """
        if not student_submissions:
            return {
                'student_id': student_info.get('id'),
                'student_name': student_info.get('username'),
                'risk_level': 'high',
                'reason': 'Sin entregas',
                'total_submissions': 0
            }
        
        # Análisis de entregas
        total = len(student_submissions)
        on_time = sum(1 for s in student_submissions if not s.get('is_late', False))
        with_analysis = sum(1 for s in student_submissions if s.get('ai_analysis'))
        
        # Calcular días desde última entrega
        last_submission = max(
            student_submissions,
            key=lambda x: x.get('timemodified', 0)
        )
        
        days_since_last = self._calculate_days_since(last_submission.get('timemodified'))
        
        # Evaluar nivel de riesgo
        risk_level, risk_reasons = self._assess_risk(
            total_submissions=total,
            on_time_count=on_time,
            days_since_last=days_since_last,
            submissions=student_submissions
        )
        
        # Análisis de progreso
        progress_analysis = self._analyze_progress(student_submissions)
        
        return {
            'student_id': student_info.get('id'),
            'student_name': student_info.get('username'),
            'student_email': student_info.get('email', ''),
            'risk_level': risk_level,
            'risk_reasons': risk_reasons,
            'statistics': {
                'total_submissions': total,
                'on_time': on_time,
                'late': total - on_time,
                'analyzed': with_analysis,
                'days_since_last_submission': days_since_last
            },
            'progress': progress_analysis,
            'report_generated_at': datetime.now().isoformat()
        }
    
    def _calculate_days_since(self, timestamp: Any) -> int:
        """Calcula días desde un timestamp"""
        try:
            if isinstance(timestamp, str):
                date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                date = datetime.fromtimestamp(timestamp)
            else:
                return 999
            
            delta = datetime.now() - date
            return delta.days
        except:
            return 999
    
    def _assess_risk(self, 
                    total_submissions: int,
                    on_time_count: int,
                    days_since_last: int,
                    submissions: List[Dict]) -> tuple:
        """
        Evalúa el nivel de riesgo del estudiante
        
        Returns:
            (risk_level, reasons) donde risk_level es 'low', 'medium' o 'high'
        """
        reasons = []
        points = 0
        
        # Pocas entregas
        if total_submissions == 0:
            points += 10
            reasons.append("Sin entregas")
        elif total_submissions < 3:
            points += 5
            reasons.append(f"Solo {total_submissions} entrega(s)")
        
        # Entregas tarde
        late_percentage = (total_submissions - on_time_count) / total_submissions if total_submissions > 0 else 0
        if late_percentage > 0.5:
            points += 5
            reasons.append(f"{late_percentage*100:.0f}% de entregas tardías")
        
        # Inactividad
        if days_since_last > 14:
            points += 7
            reasons.append(f"{days_since_last} días sin entregar")
        elif days_since_last > 7:
            points += 3
            reasons.append(f"{days_since_last} días sin entregar")
        
        # Calificaciones bajas (si existen)
        grades = []
        for s in submissions:
            ai_analysis = s.get('ai_analysis')
            if ai_analysis and isinstance(ai_analysis, dict):
                grade = ai_analysis.get('suggested_grade')
                if grade is not None:
                    grades.append(grade)
            # También considerar quizzes
            elif s.get('assignment_type') == 'quiz' and 'grade' in s:
                quiz_grade = s.get('grade', 0)
                max_grade = s.get('max_grade', 10)
                normalized_grade = (quiz_grade / max_grade * 10) if max_grade > 0 else 0
                grades.append(normalized_grade)
        
        if grades:
            avg_grade = sum(grades) / len(grades)
            if avg_grade < 5:
                points += 5
                reasons.append(f"Calificación promedio baja: {avg_grade:.1f}")
            elif avg_grade < 6:
                points += 2
                reasons.append(f"Calificación promedio: {avg_grade:.1f}")
        
        # Determinar nivel
        if points >= 10:
            return 'high', reasons
        elif points >= 5:
            return 'medium', reasons
        else:
            return 'low', reasons if reasons else ['Buen desempeño']
    
    def _analyze_progress(self, submissions: List[Dict]) -> Dict[str, Any]:
        """Analiza el progreso del estudiante a lo largo del tiempo"""
        if not submissions:
            return {'trend': 'unknown', 'description': 'Sin datos suficientes'}
        
        # Ordenar por fecha
        sorted_subs = sorted(
            submissions,
            key=lambda x: x.get('timemodified', 0)
        )
        
        # Analizar tendencia de calificaciones
        grades = []
        for sub in sorted_subs:
            ai_analysis = sub.get('ai_analysis')
            if ai_analysis and isinstance(ai_analysis, dict):
                grade = ai_analysis.get('suggested_grade')
                if grade is not None:
                    grades.append(grade)
            # También considerar calificaciones de quizzes
            elif sub.get('assignment_type') == 'quiz' and 'grade' in sub:
                quiz_grade = sub.get('grade', 0)
                max_grade = sub.get('max_grade', 10)
                # Normalizar a escala 0-10
                normalized_grade = (quiz_grade / max_grade * 10) if max_grade > 0 else 0
                grades.append(normalized_grade)
        
        if len(grades) < 2:
            trend = 'insufficient_data'
            description = 'Datos insuficientes para evaluar tendencia'
        else:
            # Calcular tendencia simple (primera mitad vs segunda mitad)
            mid = len(grades) // 2
            first_half_avg = sum(grades[:mid]) / mid
            second_half_avg = sum(grades[mid:]) / (len(grades) - mid)
            
            diff = second_half_avg - first_half_avg
            
            if diff > 1:
                trend = 'improving'
                description = f'Mejorando: {first_half_avg:.1f} → {second_half_avg:.1f}'
            elif diff < -1:
                trend = 'declining'
                description = f'Declinando: {first_half_avg:.1f} → {second_half_avg:.1f}'
            else:
                trend = 'stable'
                description = f'Estable: ~{second_half_avg:.1f}'
        
        return {
            'trend': trend,
            'description': description,
            'total_graded': len(grades),
            'average_grade': sum(grades) / len(grades) if grades else None
        }
    
    def generate_course_report(self, 
                              all_student_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un informe general del curso con todos los estudiantes
        
        Args:
            all_student_reports: Lista de informes individuales de estudiantes
        
        Returns:
            Informe del curso con estadísticas y estudiantes en riesgo
        """
        total_students = len(all_student_reports)
        
        # Clasificar por nivel de riesgo
        high_risk = [s for s in all_student_reports if s.get('risk_level') == 'high']
        medium_risk = [s for s in all_student_reports if s.get('risk_level') == 'medium']
        low_risk = [s for s in all_student_reports if s.get('risk_level') == 'low']
        
        # Ordenar estudiantes en riesgo
        high_risk_sorted = sorted(
            high_risk,
            key=lambda x: len(x.get('risk_reasons', [])),
            reverse=True
        )
        
        return {
            'course_summary': {
                'total_students': total_students,
                'high_risk_count': len(high_risk),
                'medium_risk_count': len(medium_risk),
                'low_risk_count': len(low_risk)
            },
            'students_at_risk': {
                'high': high_risk_sorted[:10],  # Top 10 en riesgo
                'medium': medium_risk[:10]
            },
            'recommendations': self._generate_course_recommendations(
                high_risk, medium_risk, low_risk
            ),
            'report_generated_at': datetime.now().isoformat()
        }
    
    def _generate_course_recommendations(self, 
                                        high_risk: List,
                                        medium_risk: List,
                                        low_risk: List) -> List[str]:
        """Genera recomendaciones a nivel de curso"""
        recommendations = []
        
        if high_risk:
            recommendations.append(
                f"URGENTE: {len(high_risk)} estudiante(s) en alto riesgo necesitan atención inmediata"
            )
        
        if medium_risk:
            recommendations.append(
                f"ATENCIÓN: {len(medium_risk)} estudiante(s) en riesgo medio requieren seguimiento"
            )
        
        if len(high_risk) + len(medium_risk) > len(low_risk):
            recommendations.append(
                "Considerar sesiones de refuerzo o tutorías adicionales"
            )
        
        return recommendations

    # =========================================================================
    # FOROAK - Erantzun proposamenak
    # =========================================================================
    
    def generate_forum_response(self, 
                                discussion: Dict[str, Any],
                                posts: List[Dict[str, Any]],
                                context: Optional[str] = None) -> Dict[str, Any]:
        """
        Foro eztabaida baterako erantzun proposamena sortu
        
        Args:
            discussion: Eztabaidaren datuak (izena, egilea, mezua)
            posts: Eztabaidako mezu guztiak
            context: Testuinguru gehigarria (kurtsoa, gaia, etab.)
        
        Returns:
            Dict erantzun proposamenarekin
        """
        try:
            prompt = self._build_forum_response_prompt(discussion, posts, context)
            
            # Foroentzako schema erabili
            response = self._query_forum_ai(prompt)
            
            return {
                'status': 'success',
                'discussion_id': discussion.get('id'),
                'discussion_name': discussion.get('name'),
                'proposed_response': response.get('response', ''),
                'tone': response.get('tone', 'friendly'),
                'key_points': response.get('key_points', []),
                'follow_up_questions': response.get('follow_up_questions', []),
                'resources': response.get('resources', []),
                'priority': response.get('priority', 'medium'),
                'category': response.get('category', 'question'),
                'summary': response.get('summary', ''),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sortzen foro erantzuna: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def _build_forum_response_prompt(self, 
                                     discussion: Dict[str, Any],
                                     posts: List[Dict[str, Any]],
                                     context: Optional[str] = None) -> str:
        """Sortu foro erantzunerako prompt-a"""
        
        prompt = """Eres un profesor experto respondiendo a un estudiante en un foro educativo.
Tu objetivo es proporcionar una respuesta clara, útil y educativa.

"""
        
        if context:
            prompt += f"""CONTEXTO DEL CURSO:
{context}

"""
        
        prompt += f"""INFORMACIÓN DE LA DISCUSIÓN:
- Título: {discussion.get('name', 'Sin título')}
- Autor: {discussion.get('userfullname', 'Desconocido')}
- Fecha: {discussion.get('created', 'Desconocida')}
- Respuestas existentes: {discussion.get('numreplies', 0)}

"""
        
        # Añadir el mensaje original
        original_message = discussion.get('message', '')
        if original_message:
            prompt += f"""MENSAJE ORIGINAL DEL ESTUDIANTE:
{original_message}

"""
        
        # Añadir respuestas anteriores si existen
        if posts and len(posts) > 1:
            prompt += "CONVERSACIÓN ANTERIOR:\n"
            for post in posts[1:]:  # Saltar el primer post (es el original)
                author = post.get('author', {}).get('fullname', 'Desconocido')
                message = post.get('message', '')
                prompt += f"- {author}: {message}\n"
            prompt += "\n"
        
        prompt += """INSTRUCCIONES:
1. Analiza la pregunta o comentario del estudiante
2. Determina la categoría (pregunta, duda, solicitud de ayuda, discusión, feedback, otro)
3. Genera una respuesta profesional, clara y educativa
4. Incluye puntos clave que el estudiante debe recordar
5. Si es apropiado, sugiere preguntas de seguimiento o recursos adicionales
6. Determina la prioridad de respuesta (urgent, high, medium, low)

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura:
{
    "response": "Tu respuesta completa y detallada aquí...",
    "tone": "friendly",
    "key_points": ["Punto clave 1", "Punto clave 2"],
    "follow_up_questions": ["¿Has probado...?", "¿Entiendes...?"],
    "resources": [{"title": "Recurso 1", "description": "Descripción del recurso"}],
    "priority": "medium",
    "category": "question",
    "summary": "Resumen breve de la respuesta propuesta"
}

NOTAS:
- "tone": formal, friendly, educational, supportive
- "priority": urgent (errores críticos), high (bloqueo del estudiante), medium (duda normal), low (comentario general)
- "category": question, doubt, help_request, discussion, feedback, other
"""
        
        return prompt
    
    def _query_forum_ai(self, prompt: str) -> Dict[str, Any]:
        """Kontsultatu IA foroen erantzunetarako"""
        try:
            if self.stream:
                return self._query_forum_streaming(prompt)
            else:
                response = self.client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    format=FORUM_RESPONSE_SCHEMA,
                    think=self.think
                )
                content = response['message']['content']
                return json.loads(content)
                
        except Exception as e:
            logger.error(f"Error forum AI query: {e}")
            return self._get_default_forum_response()
    
    def _query_forum_streaming(self, prompt: str) -> Dict[str, Any]:
        """Streaming bidezko kontsulta foroentzat"""
        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                format=FORUM_RESPONSE_SCHEMA,
                think=self.think
            )
            
            content = ''
            for chunk in stream:
                if hasattr(chunk.message, 'content') and chunk.message.content:
                    content += chunk.message.content
            
            return json.loads(content)
            
        except json.JSONDecodeError:
            logger.warning("Forum response not valid JSON")
            return self._get_default_forum_response()
    
    def _get_default_forum_response(self) -> Dict[str, Any]:
        """Foroen erantzun lehenetsia"""
        return {
            'response': 'No se pudo generar una respuesta automática.',
            'tone': 'friendly',
            'key_points': [],
            'follow_up_questions': [],
            'resources': [],
            'priority': 'medium',
            'category': 'other',
            'summary': 'Error generando respuesta'
        }
    
    def analyze_forum_discussions(self, 
                                  discussions: List[Dict[str, Any]],
                                  generate_responses: bool = True) -> Dict[str, Any]:
        """
        Analiza múltiples discusiones de foro y genera respuestas
        
        Args:
            discussions: Lista de eztabaidak mezu guztiekin
            generate_responses: Erantzunak sortu ala ez
        
        Returns:
            Analisi osoa erantzun proposamenekin
        """
        results = {
            'total_discussions': len(discussions),
            'by_priority': {'urgent': [], 'high': [], 'medium': [], 'low': []},
            'by_category': {},
            'responses': [],
            'analyzed_at': datetime.now().isoformat()
        }
        
        for disc in discussions:
            posts = disc.get('posts', [])
            
            if generate_responses:
                response = self.generate_forum_response(disc, posts)
                results['responses'].append(response)
                
                # Klasifikatu lehentasunaren arabera
                priority = response.get('priority', 'medium')
                results['by_priority'][priority].append({
                    'discussion_id': disc.get('id'),
                    'name': disc.get('name'),
                    'response': response
                })
                
                # Klasifikatu kategoriaren arabera
                category = response.get('category', 'other')
                if category not in results['by_category']:
                    results['by_category'][category] = []
                results['by_category'][category].append(disc.get('id'))
        
        # Laburpena
        results['summary'] = {
            'urgent_count': len(results['by_priority']['urgent']),
            'high_count': len(results['by_priority']['high']),
            'needs_immediate_attention': len(results['by_priority']['urgent']) + len(results['by_priority']['high'])
        }
        
        return results

    # =========================================================================
    # FORO-TAREA EBALUAZIOA - Foroak tarea moduan ebaluatzeko
    # =========================================================================
    
    def evaluate_forum_as_task(self,
                               student_posts: List[Dict[str, Any]],
                               forum_info: Dict[str, Any],
                               task_criteria: Optional[str] = None,
                               student_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ikasle baten foro partaidetza ebaluatu tarea moduan
        
        Args:
            student_posts: Ikaslearen mezu guztiak foroan
            forum_info: Foroaren informazioa (izena, deskribapena, gaia)
            task_criteria: Ebaluazio irizpideak (rubrika)
            student_info: Ikaslearen informazioa (izena, id, etab.)
        
        Returns:
            Dict ebaluazio osoarekin (nota, feedback, irizpideak, etab.)
        """
        try:
            prompt = self._build_forum_task_prompt(student_posts, forum_info, task_criteria, student_info)
            
            # Ebaluazio schema erabili
            response = self._query_forum_task_ai(prompt)
            
            return {
                'status': 'success',
                'student_id': student_info.get('id') if student_info else None,
                'student_name': student_info.get('fullname') if student_info else 'Desconocido',
                'forum_id': forum_info.get('id'),
                'forum_name': forum_info.get('name'),
                'posts_evaluated': len(student_posts),
                'evaluation': response,
                'feedback': response.get('feedback', ''),
                'grade': response.get('grade'),
                'participation_quality': response.get('participation_quality', {}),
                'strengths': response.get('strengths', []),
                'weaknesses': response.get('weaknesses', []),
                'recommendations': response.get('recommendations', []),
                'meets_requirements': response.get('meets_requirements', False),
                'summary': response.get('summary', ''),
                'evaluated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error ebaluatzen foro-tarea: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'evaluated_at': datetime.now().isoformat()
            }
    
    def _build_forum_task_prompt(self,
                                  student_posts: List[Dict[str, Any]],
                                  forum_info: Dict[str, Any],
                                  task_criteria: Optional[str] = None,
                                  student_info: Optional[Dict[str, Any]] = None) -> str:
        """Sortu foro-tarea ebaluaziorako prompt-a"""
        
        prompt = """Eres un profesor evaluando la participación de un estudiante en un foro que funciona como tarea evaluable.
Tu objetivo es evaluar de forma justa y constructiva la calidad de las aportaciones del estudiante.

"""
        
        # Foroaren informazioa
        prompt += f"""INFORMACIÓN DEL FORO/TAREA:
- Nombre: {forum_info.get('name', 'Sin nombre')}
- Tipo: {forum_info.get('type', 'general')}
- Descripción/Instrucciones: {forum_info.get('intro', 'No disponible')}

"""
        
        # Irizpideak badaude
        if task_criteria:
            prompt += f"""CRITERIOS DE EVALUACIÓN:
{task_criteria}

"""
        
        # Ikaslearen informazioa
        if student_info:
            prompt += f"""ESTUDIANTE:
- Nombre: {student_info.get('fullname', 'Desconocido')}
- ID: {student_info.get('id', 'N/A')}

"""
        
        # Ikaslearen mezuak
        prompt += f"""APORTACIONES DEL ESTUDIANTE ({len(student_posts)} mensaje(s)):
"""
        
        total_words = 0
        for i, post in enumerate(student_posts, 1):
            message = post.get('message', '')
            word_count = len(message.split())
            total_words += word_count
            
            is_reply = post.get('parentid', 0) > 0
            post_type = "Respuesta a otro compañero" if is_reply else "Aportación inicial"
            
            prompt += f"""
--- Mensaje {i} ({post_type}) ---
Fecha: {post.get('timecreated', 'Desconocida')}
Asunto: {post.get('subject', 'Sin asunto')}
Contenido:
{message}

"""
        
        prompt += f"""
ESTADÍSTICAS:
- Total de mensajes: {len(student_posts)}
- Total de palabras: {total_words}
- Mensajes con respuesta a otros: {sum(1 for p in student_posts if p.get('parentid', 0) > 0)}

"""
        
        prompt += """INSTRUCCIONES DE EVALUACIÓN:
1. Evalúa la relevancia de las aportaciones respecto al tema del foro
2. Valora la profundidad del análisis y la argumentación
3. Considera la originalidad y el valor añadido a la discusión
4. Evalúa la claridad de la expresión escrita
5. Valora la interacción con otros compañeros (si hay respuestas)
6. Proporciona feedback constructivo y específico
7. Sugiere áreas de mejora concretas
8. Asigna una calificación de 0 a 10

Responde ÚNICAMENTE con un objeto JSON válido siguiendo el schema proporcionado.
"""
        
        return prompt
    
    def _query_forum_task_ai(self, prompt: str) -> Dict[str, Any]:
        """Kontsultatu IA foro-tarea ebaluaziorako"""
        try:
            if self.stream:
                return self._query_forum_task_streaming(prompt)
            else:
                response = self.client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    format=FORUM_TASK_EVALUATION_SCHEMA,
                    think=self.think
                )
                content = response['message']['content']
                return json.loads(content)
                
        except Exception as e:
            logger.error(f"Error forum-task AI query: {e}")
            return self._get_default_forum_task_response()
    
    def _query_forum_task_streaming(self, prompt: str) -> Dict[str, Any]:
        """Streaming bidezko kontsulta foro-tarearentzat"""
        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                format=FORUM_TASK_EVALUATION_SCHEMA,
                think=self.think
            )
            
            content = ''
            for chunk in stream:
                if hasattr(chunk.message, 'content') and chunk.message.content:
                    content += chunk.message.content
            
            return json.loads(content)
            
        except json.JSONDecodeError:
            logger.warning("Forum-task response not valid JSON")
            return self._get_default_forum_task_response()
    
    def _get_default_forum_task_response(self) -> Dict[str, Any]:
        """Foro-tarea ebaluazioaren erantzun lehenetsia"""
        return {
            'feedback': 'No se pudo generar una evaluación automática.',
            'grade': None,
            'participation_quality': {
                'relevance': 0,
                'depth': 0,
                'originality': 0,
                'clarity': 0,
                'interaction': 0
            },
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'meets_requirements': False,
            'word_count_adequate': False,
            'cited_sources': False,
            'responded_to_others': False,
            'summary': 'Error generando evaluación'
        }
    
    def evaluate_all_students_in_forum(self,
                                       forum_data: Dict[str, Any],
                                       task_criteria: Optional[str] = None) -> Dict[str, Any]:
        """
        Foro bateko ikasle guztien partaidetzak ebaluatu
        
        Args:
            forum_data: Foroaren datu osoak (eztabaidak, mezuak)
            task_criteria: Ebaluazio irizpideak
        
        Returns:
            Dict ikasle guztien ebaluazioekin
        """
        results = {
            'forum_id': forum_data.get('id'),
            'forum_name': forum_data.get('name'),
            'total_students': 0,
            'evaluations': [],
            'statistics': {
                'average_grade': 0,
                'highest_grade': 0,
                'lowest_grade': 10,
                'passed': 0,  # Nota >= 5
                'failed': 0   # Nota < 5
            },
            'evaluated_at': datetime.now().isoformat()
        }
        
        # Bildu ikasle bakoitzaren mezuak
        students_posts = {}  # {user_id: {'info': {...}, 'posts': [...]}}
        
        for discussion in forum_data.get('discussions', []):
            for post in discussion.get('posts', []):
                author = post.get('author', {})
                user_id = author.get('id')
                
                if user_id:
                    if user_id not in students_posts:
                        students_posts[user_id] = {
                            'info': {
                                'id': user_id,
                                'fullname': author.get('fullname', 'Desconocido')
                            },
                            'posts': []
                        }
                    students_posts[user_id]['posts'].append(post)
        
        # Ebaluatu ikasle bakoitza
        grades = []
        for user_id, data in students_posts.items():
            evaluation = self.evaluate_forum_as_task(
                student_posts=data['posts'],
                forum_info=forum_data,
                task_criteria=task_criteria,
                student_info=data['info']
            )
            
            results['evaluations'].append(evaluation)
            
            grade = evaluation.get('grade')
            if grade is not None:
                grades.append(grade)
                if grade >= 5:
                    results['statistics']['passed'] += 1
                else:
                    results['statistics']['failed'] += 1
        
        # Estatistikak kalkulatu
        results['total_students'] = len(students_posts)
        
        if grades:
            results['statistics']['average_grade'] = round(sum(grades) / len(grades), 2)
            results['statistics']['highest_grade'] = max(grades)
            results['statistics']['lowest_grade'] = min(grades)
        
        return results


# =============================================================================
# Ejemplo de uso / Test
# =============================================================================
if __name__ == "__main__":
    """
    Adibidea: AIAnalyzer erabiltzeko modua streaming-arekin
    
    Ingurune aldagaiak (aukerakoak):
        OLLAMA_HOST: Ollama zerbitzariaren URLa (defektuz: http://10.2.50.232:11434)
        OLLAMA_MODEL: Erabiliko den modeloa (defektuz: qwen3:30b-a3b)
    """
    
    print("=" * 70)
    print("🧪 AIAnalyzer Test - Streaming modua")
    print("=" * 70)
    
    # Analizatzailea sortu
    analyzer = AIAnalyzer(
        model="qwen3:30b-a3b",           # Modeloa
        host="http://10.2.50.232:11434",  # Ollama zerbitzaria
        stream=True,                      # Streaming aktibatu
        think=False                       # Think modua desaktibatu
    )
    
    # Test sinplea - konexioa egiaztatu
    print("\n📡 Probando conexión con Ollama...")
    
    try:
        # Test prompt sinple bat
        test_prompt = """Responde en JSON: {"status": "ok", "message": "Conexión exitosa"}"""
        
        print("\n🔄 Enviando prompt de prueba...\n")
        
        def print_chunk(text: str, is_thinking: bool):
            if is_thinking:
                print(f"\033[90m[think] {text}\033[0m", end='', flush=True)
            else:
                print(text, end='', flush=True)
        
        result = analyzer._query_ai(test_prompt, on_chunk=print_chunk)
        
        print(f"\n\n✅ Resultado parseado: {result}")
        print("\n" + "=" * 70)
        print("🎉 Conexión establecida correctamente!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        print("\nAsegúrate de que:")
        print(f"  1. El servidor Ollama está corriendo en {analyzer.host}")
        print(f"  2. El modelo '{analyzer.model}' está disponible")
        print("  3. No hay firewall bloqueando la conexión")
