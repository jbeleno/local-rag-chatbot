"""
Servicio de búsqueda web usando DuckDuckGo.
"""
import logging
import re
from typing import List, Dict
from ddgs import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """Servicio para búsquedas web con DuckDuckGo."""
    
    def __init__(self):
        """Inicializar el servicio de búsqueda web."""
        # Inicializar DuckDuckGo
        try:
            self.ddgs = DDGS()
            logger.info("DuckDuckGo inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar DuckDuckGo: {e}")
            self.ddgs = None
        
        # Stop words en español (palabras comunes que no aportan significado)
        self.stop_words = {
            'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
            'de', 'del', 'al', 'a', 'en', 'por', 'para', 'con', 'sin',
            'es', 'son', 'está', 'están', 'ser', 'estar', 'tener',
            'cuál', 'cuáles', 'qué', 'quién', 'quiénes', 'cómo', 
            'cuándo', 'dónde', 'por qué', 'cuánto', 'cuántos',
            'se', 'le', 'les', 'me', 'te', 'nos', 'os',
            'y', 'o', 'pero', 'mas', 'sino', 'aunque',
            'sobre', 'hay', 'que'
        }
    
    def should_search_web(self, query: str) -> bool:
        """
        Determinar si una consulta requiere búsqueda web.
        
        Detecta keywords temporales como:
        - Fechas recientes (2025, 2024, actual, hoy)
        - Palabras relacionadas con noticias (últimas noticias, reciente)
        - Precios actuales (precio actual, cotización)
        - Eventos en tiempo real
        
        Args:
            query: Consulta del usuario
            
        Returns:
            True si debería buscar en web, False si no
        """
        if not settings.WEB_SEARCH_ENABLED:
            return False
        
        query_lower = query.lower()
        
        # Keywords temporales que indican necesidad de información actualizada
        temporal_keywords = [
            "2025", "2024", "2023", "2022", "2021", "2020",  # Años recientes
            "actual", "hoy", "ahora", "reciente",
            "últimas noticias", "precio actual", "cotización",
            "último", "nuevo", "actualizado", "en tiempo real",
            "noticias", "última hora", "recientemente", "ahora mismo",
            "precio", "cotización", "valor actual", "estado actual",
            "tendencias", "estadísticas", "datos actuales",
            "mundial", "campeonato", "evento", "competencia"  # Eventos deportivos/históricos
        ]
        
        # Keywords que indican información que probablemente no está en docs locales
        general_info_keywords = [
            "noticias", "eventos", "precio", "cotización", "tendencias",
            "estadísticas", "ranking", "comparación", "mejor", "peor",
            "recomendaciones", "opiniones", "reseñas", "guía"
        ]
        
        # Keywords que indican preguntas sobre información actual del mundo real
        real_world_keywords = [
            "presidente", "presidenta", "líder", "gobernador", "alcalde",
            "país", "países", "ciudad", "capital", "población",
            "quien es", "quién es", "que es", "qué es", "donde está", "dónde está",
            "cuando fue", "cuándo fue", "como funciona", "cómo funciona"
        ]
        
        # Keywords de lugares/entidades que requieren información actualizada
        location_keywords = [
            "colombia", "méxico", "argentina", "españa", "estados unidos",
            "brasil", "chile", "perú", "venezuela", "ecuador"
        ]
        
        # Verificar keywords temporales
        has_temporal = any(keyword in query_lower for keyword in temporal_keywords)
        
        # Verificar si pide información general
        has_general_info = any(keyword in query_lower for keyword in general_info_keywords)
        
        # Verificar si es pregunta sobre información del mundo real
        has_real_world = any(keyword in query_lower for keyword in real_world_keywords)
        
        # Verificar si menciona lugares/países
        has_location = any(keyword in query_lower for keyword in location_keywords)
        
        # Detectar preguntas sobre eventos históricos/deportivos con años
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', query))
        has_event_keywords = any(keyword in query_lower for keyword in ['mundial', 'campeonato', 'evento', 'competencia', 'ganó', 'gano', 'ganador', 'campeón', 'campeon'])
        has_historical_query = has_year and (has_event_keywords or len(query.split()) > 3)
        
        # Detectar preguntas que requieren información actual (quien, que, donde, etc.)
        question_patterns = [
            r'\bquien\b', r'\bquién\b', r'\bque\b', r'\bqué\b',
            r'\bdonde\b', r'\bdónde\b', r'\bcuando\b', r'\bcuándo\b',
            r'\bcomo\b', r'\bcómo\b', r'\bcuanto\b', r'\bcuánto\b'
        ]
        has_question_word = any(re.search(pattern, query_lower) for pattern in question_patterns)
        
        # Buscar en web si:
        # 1. Tiene keywords temporales
        # 2. Es pregunta histórica/deportiva con año
        # 3. Tiene keywords de info general Y tiene términos específicos
        # 4. Es pregunta sobre información del mundo real (presidente, país, etc.)
        # 5. Tiene palabra de pregunta Y menciona lugares/entidades
        should_search = (
            has_temporal or 
            has_historical_query or 
            (has_general_info and len(query.split()) > 2) or
            (has_real_world and len(query.split()) > 2) or
            (has_question_word and (has_location or has_real_world or len(query.split()) > 3))
        )
        
        if should_search:
            logger.info(f"Consulta requiere búsqueda web: {query[:50]}...")
        
        return should_search
    
    def _extract_keywords(self, query: str) -> str:
        """
        Extraer y optimizar keywords de una query para mejor búsqueda.
        
        Estrategia:
        1. Preservar versiones (ej: 3.12, 2.0)
        2. Remover stop words
        3. Remover signos de puntuación
        4. Priorizar sustantivos y términos específicos
        5. Reordenar para mejor relevancia
        
        Args:
            query: Query original
            
        Returns:
            Query optimizada con keywords relevantes
        """
        # Primero, proteger versiones (ej: "3.12", "2.0") antes de remover puntuación
        version_pattern = r'\b\d+\.\d+\b'
        versions = re.findall(version_pattern, query)
        protected_query = query
        
        # Reemplazar versiones con placeholders temporales
        version_map = {}
        for i, version in enumerate(versions):
            placeholder = f"__VERSION_{i}__"
            version_map[placeholder] = version
            protected_query = protected_query.replace(version, placeholder, 1)
        
        # Ahora remover signos de puntuación
        cleaned = re.sub(r'[¿?¡!.,;:()\[\]{}"\']', '', protected_query)
        
        # Restaurar versiones
        for placeholder, version in version_map.items():
            cleaned = cleaned.replace(placeholder, version)
        
        # Convertir a minúsculas y dividir en palabras
        words = cleaned.lower().split()
        
        # Detectar años (4 dígitos que empiezan con 19 o 20)
        year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        
        # Filtrar stop words y palabras muy cortas, pero mantener versiones y años
        keywords = []
        for w in words:
            # Mantener versiones (contienen punto y números)
            if '.' in w and any(char.isdigit() for char in w):
                keywords.append(w)
            # Mantener años
            elif year_pattern.match(w):
                keywords.append(w)
            # Filtrar stop words y números simples
            elif w not in self.stop_words and len(w) > 2 and not w.isdigit():
                keywords.append(w)
        
        # Si no quedan keywords, usar la query original sin puntuación
        if not keywords:
            # Restaurar versiones en la query original si es necesario
            original_cleaned = re.sub(r'[¿?¡!.,;:()\[\]{}"\']', '', query)
            for placeholder, version in version_map.items():
                original_cleaned = original_cleaned.replace(placeholder, version)
            keywords = [w for w in original_cleaned.lower().split() if len(w) > 1]
        
        # Detectar si es una query sobre precios/cotizaciones
        price_keywords = ['precio', 'price', 'cotización', 'cotizacion', 'valor', 'value', 'costo', 'cost']
        is_price_query = any(keyword in query.lower() for keyword in price_keywords)
        
        # Si es query de precio, priorizar términos financieros
        if is_price_query:
            # Buscar términos de criptomonedas o activos
            crypto_terms = ['bitcoin', 'btc', 'ethereum', 'eth', 'criptomoneda', 'cryptocurrency', 'crypto']
            found_crypto = None
            for crypto in crypto_terms:
                if crypto in query.lower():
                    found_crypto = crypto
                    break
            
            # Reconstruir query priorizando: [crypto] + [price terms] + [year] + [otros]
            if found_crypto:
                price_terms = [k for k in keywords if any(pk in k for pk in price_keywords)]
                year_terms = [k for k in keywords if year_pattern.match(k)]
                other_terms = [k for k in keywords if k not in price_terms and k not in year_terms and k != found_crypto]
                
                # Ordenar: crypto primero, luego price terms, luego año, luego otros
                optimized_parts = [found_crypto] + price_terms + year_terms + other_terms
                optimized = ' '.join(optimized_parts)
            else:
                # Si no hay crypto, ordenar normal pero priorizar price terms
                price_terms = [k for k in keywords if any(pk in k for pk in price_keywords)]
                year_terms = [k for k in keywords if year_pattern.match(k)]
                other_terms = [k for k in keywords if k not in price_terms and k not in year_terms]
                optimized_parts = price_terms + year_terms + other_terms
                optimized = ' '.join(optimized_parts)
            
            # Traducir términos clave al inglés para mejor búsqueda
            spanish_to_english = {
                'precio': 'price',
                'cotización': 'price',
                'cotizacion': 'price',
                'valor': 'value',
                'actual': 'current',
                'hoy': 'today',
                'ahora': 'now',
                'reciente': 'recent',
                'noticias': 'news',
                'últimas noticias': 'latest news'
            }
            
            # Traducir términos comunes al inglés
            optimized_lower = optimized.lower()
            for es_term, en_term in spanish_to_english.items():
                if es_term in optimized_lower:
                    # Reemplazar manteniendo mayúsculas si las hay
                    optimized = re.sub(r'\b' + re.escape(es_term) + r'\b', en_term, optimized, flags=re.IGNORECASE)
                    break  # Solo traducir el primer término encontrado
            
            return optimized if optimized else query
        
        # Reordenar: poner términos más específicos primero
        # (palabras más largas y menos comunes suelen ser más específicas)
        keywords_sorted = sorted(keywords, key=lambda x: (-len(x), x))
        
        optimized = ' '.join(keywords_sorted)
        
        return optimized if optimized else query
    
    def search_web(self, query: str, num_results: int = None) -> List[Dict]:
        """
        Realizar búsqueda web con DuckDuckGo.
        
        Optimiza la query antes de buscar para mejores resultados.
        
        Args:
            query: Términos de búsqueda
            num_results: Número de resultados a retornar (default: usar configuración)
            
        Returns:
            Lista de diccionarios con resultados de búsqueda
            Cada resultado contiene: title, snippet, url
        """
        if not self.ddgs:
            logger.warning("DuckDuckGo no está disponible")
            return []
        
        if num_results is None:
            num_results = settings.WEB_SEARCH_MAX_RESULTS
        
        try:
            # Optimizar la query antes de buscar
            optimized_query = self._extract_keywords(query)
            logger.info(f"Buscando en web: {optimized_query} (original: {query}, max_results={num_results})")
            
            # Realizar búsqueda con query optimizada
            results = self.ddgs.text(
                query=optimized_query,
                max_results=num_results
            )
            
            # DEBUG: Ver qué retorna DuckDuckGo
            logger.info(f"DuckDuckGo retornó {len(results) if results else 0} resultados")
            if results and len(results) > 0:
                logger.info(f"Tipo del primer resultado: {type(results[0])}")
                for i, result in enumerate(results[:3], 1):  # Mostrar primeros 3 resultados
                    logger.info(f"Resultado {i} completo: {result}")
            
            # Formatear resultados con mejor manejo de errores
            formatted_results = []
            if results:
                for i, result in enumerate(results):
                    try:
                        # Verificar que result tenga la estructura esperada
                        if isinstance(result, dict):
                            title = result.get("title", "") or result.get("Title", "")
                            snippet = result.get("body", "") or result.get("snippet", "") or result.get("Body", "") or result.get("Snippet", "")
                            url = result.get("href", "") or result.get("url", "") or result.get("Href", "") or result.get("Url", "")
                            
                            # Solo agregar si tiene al menos título o snippet
                            if title or snippet:
                                formatted_results.append({
                                    "title": title,
                                    "snippet": snippet,
                                    "url": url
                                })
                            else:
                                logger.warning(f"Resultado {i} de DuckDuckGo no tiene título ni snippet: {result}")
                        else:
                            # Si result es string u otro tipo, intentar parsearlo
                            logger.warning(f"Resultado {i} de DuckDuckGo tiene tipo inesperado: {type(result)}, valor: {str(result)[:100]}")
                    except Exception as e:
                        logger.error(f"Error al procesar resultado {i} de DuckDuckGo: {e}")
                        continue
            else:
                logger.warning("DuckDuckGo retornó None o lista vacía")
            
            logger.info(f"DuckDuckGo: Encontrados {len(formatted_results)} resultados web válidos")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda web con DuckDuckGo: {e}", exc_info=True)
            return []
    
    def format_web_results_for_context(self, web_results: List[Dict]) -> str:
        """
        Formatear resultados web para incluir en el contexto del LLM.
        
        Args:
            web_results: Lista de resultados de búsqueda web
            
        Returns:
            String formateado con la información web
        """
        if not web_results:
            return ""
        
        formatted = "\n\n=== INFORMACIÓN DE INTERNET (ACTUALIZADA) ===\n"
        formatted += "IMPORTANTE: Esta información tiene PRIORIDAD sobre la documentación local.\n"
        formatted += "DEBES usar esta información para responder la pregunta del usuario.\n\n"
        
        for i, result in enumerate(web_results, 1):
            formatted += f"Resultado {i}:\n"
            formatted += f"Título: {result.get('title', 'Sin título')}\n"
            formatted += f"Contenido: {result.get('snippet', 'Sin contenido')}\n"
            formatted += f"URL: {result.get('url', 'Sin URL')}\n"
            formatted += "\n"
        
        formatted += "=== FIN DE INFORMACIÓN DE INTERNET ===\n"
        formatted += "INSTRUCCIÓN: Usa la información de arriba para responder la pregunta del usuario.\n"
        
        # Log del contenido formateado
        logger.info(f"Contenido web formateado completo:\n{formatted}")
        
        return formatted
