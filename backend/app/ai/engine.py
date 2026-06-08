"""
Motor de IA para análisis de propiedades inmobiliarias.

Funcionalidades:
- Clasificación y scoring de propiedades
- Detección de propiedades premium y subvaluadas
- Generación de descripciones comerciales
- Estimación de valor de mercado
- Matching comprador-propiedad
- Análisis de sentimiento
"""
import asyncio
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.engine")


class PropertyAIEngine:
    """
    Motor de IA especializado en el mercado inmobiliario de Punta del Este.

    Usa GPT-4o-mini para análisis masivo y GPT-4o para análisis premium.
    Incluye prompts optimizados con contexto del mercado local.
    """

    # Contexto del mercado para los prompts
    MARKET_CONTEXT = """
    Eres un experto en el mercado inmobiliario de Punta del Este, Uruguay.

    CONTEXTO DEL MERCADO:
    - Punta del Este es un destino de lujo internacional, referente de América Latina
    - Zonas premium: La Barra, José Ignacio, Manantiales, Punta Ballena, San Rafael
    - Zonas estándar: Cantegril, Pinares, Beverly Hills, Aidy Grill, Roosevelt
    - Precios promedio:
      * Apartamento zona premium: USD 3.000 - 6.000/m²
      * Apartamento zona estándar: USD 1.500 - 3.000/m²
      * Casa zona premium: USD 2.500 - 8.000/m²
      * Terreno: USD 200 - 2.000/m² dependiendo zona
    - Temporada alta: diciembre-marzo (precios alquiler 3-5x)
    - Moneda: dólares americanos (USD) para transacciones
    - El mercado tiene alta demanda de argentinos, brasileños y europeos
    - Rentabilidad típica de alquiler: 4-8% anual en zonas buenas
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.model_premium = settings.OPENAI_MODEL_PREMIUM

    async def _call_ai(
        self,
        messages: List[Dict],
        response_format: Optional[Dict] = None,
        premium: bool = False,
        temperature: float = 0.3,
    ) -> Optional[str]:
        """Llamada base a la API de OpenAI."""
        try:
            model = self.model_premium if premium else self.model
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error("Error en llamada a OpenAI", error=str(e))
            return None

    async def score_property(self, property_data: Dict) -> Dict:
        """
        Calcular score de calidad y oportunidad de una propiedad.

        Returns:
            {
                "quality_score": 0-100,
                "opportunity_score": 0-100,
                "is_premium": bool,
                "is_opportunity": bool,
                "is_undervalued": bool,
                "tags": [...],
                "summary": "...",
                "reasoning": "...",
            }
        """
        price = property_data.get("price_usd") or property_data.get("price", 0)
        area = property_data.get("area_total") or property_data.get("area_built", 0)
        price_m2 = (price / area) if price and area and area > 0 else 0

        messages = [
            {
                "role": "system",
                "content": self.MARKET_CONTEXT + """

                Tu tarea es analizar propiedades inmobiliarias y dar:
                1. Score de CALIDAD (0-100): Basado en características, ubicación, presentación
                2. Score de OPORTUNIDAD (0-100): Precio vs mercado, potencial de valorización
                3. Clasificación: premium / oportunidad / subvaluada
                4. Tags descriptivos

                Responde SOLO con JSON válido, sin texto adicional.
                """,
            },
            {
                "role": "user",
                "content": f"""
                Analiza esta propiedad:

                TIPO: {property_data.get('property_type', 'N/A')}
                OPERACIÓN: {property_data.get('operation', 'N/A')}
                TÍTULO: {property_data.get('title', 'N/A')}
                PRECIO: USD {price:,.0f}
                ÁREA TOTAL: {area} m²
                PRECIO/M²: USD {price_m2:,.0f}/m²
                DORMITORIOS: {property_data.get('bedrooms', 'N/A')}
                BAÑOS: {property_data.get('bathrooms', 'N/A')}
                BARRIO/ZONA: {property_data.get('neighborhood', 'N/A')}
                AMENIDADES: {', '.join(property_data.get('amenities', [])[:10])}
                DESCRIPCIÓN: {(property_data.get('description') or '')[:500]}
                AÑO CONSTRUCCIÓN: {property_data.get('year_built', 'N/A')}
                INMOBILIARIA: {property_data.get('agency_name', 'N/A')}

                Responde con este JSON exacto:
                {{
                    "quality_score": <0-100>,
                    "opportunity_score": <0-100>,
                    "is_premium": <true/false>,
                    "is_opportunity": <true/false>,
                    "is_undervalued": <true/false>,
                    "estimated_market_value_usd": <número o null>,
                    "price_assessment": <"below_market"|"at_market"|"above_market">,
                    "roi_estimate_pct": <número o null>,
                    "tags": [<lista de tags relevantes, max 8>],
                    "summary": "<resumen en 2-3 oraciones>",
                    "reasoning": "<explicación del score, max 150 palabras>"
                }}
                """,
            },
        ]

        response = await self._call_ai(
            messages,
            response_format={"type": "json_object"},
        )

        if not response:
            return self._default_score()

        try:
            result = json.loads(response)
            # Validar y limpiar
            result["quality_score"] = max(0, min(100, float(result.get("quality_score", 50))))
            result["opportunity_score"] = max(0, min(100, float(result.get("opportunity_score", 50))))
            return result
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error("Error parseando respuesta de IA", error=str(e))
            return self._default_score()

    def _default_score(self) -> Dict:
        """Score por defecto cuando falla la IA."""
        return {
            "quality_score": 50.0,
            "opportunity_score": 50.0,
            "is_premium": False,
            "is_opportunity": False,
            "is_undervalued": False,
            "estimated_market_value_usd": None,
            "price_assessment": "at_market",
            "roi_estimate_pct": None,
            "tags": [],
            "summary": "Propiedad pendiente de análisis.",
            "reasoning": "Análisis de IA no disponible.",
        }

    async def generate_commercial_description(
        self,
        property_data: Dict,
        tone: str = "professional",
        language: str = "es",
    ) -> str:
        """
        Generar descripción comercial optimizada para venta.

        Args:
            property_data: Datos de la propiedad
            tone: "professional", "luxury", "casual"
            language: "es" o "en"
        """
        tone_instructions = {
            "professional": "Formal, preciso, enfocado en datos y valor de inversión.",
            "luxury": "Aspiracional, exclusivo, evocador. Usa lenguaje de lujo y experiencias.",
            "casual": "Amigable, accesible, directo. Para el mercado masivo.",
        }

        lang_instructions = {
            "es": "Español rioplatense (Uruguay/Argentina). No uses 'vos'.",
            "en": "American English. Professional and concise.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""{self.MARKET_CONTEXT}

                Eres un copywriter experto en real estate de lujo.
                Tono: {tone_instructions.get(tone, tone_instructions['professional'])}
                Idioma: {lang_instructions.get(language, lang_instructions['es'])}

                Genera descripciones que:
                - Sean atractivas y vendan la experiencia de vivir en el lugar
                - Destaquen los beneficios únicos de la zona
                - Incluyan detalles específicos de la propiedad
                - Tengan entre 150-250 palabras
                - NO uses clichés como "no pierdas esta oportunidad"
                - SÍ menciona el estilo de vida de Punta del Este cuando sea relevante
                """,
            },
            {
                "role": "user",
                "content": f"""
                Genera una descripción comercial para esta propiedad:

                {json.dumps(property_data, ensure_ascii=False, default=str)}

                La descripción debe ser perfecta para publicar en portales inmobiliarios premium
                y redes sociales. Solo devuelve la descripción, sin títulos ni formatos adicionales.
                """,
            },
        ]

        response = await self._call_ai(messages, temperature=0.7)
        return response or ""

    async def analyze_sentiment(self, text: str) -> Dict:
        """
        Analizar sentimiento y calidad del texto de una propiedad.

        Detecta: alertas rojas (urgencia de venta, problemas), señales positivas.
        """
        if not text or len(text) < 50:
            return {"score": 0, "label": "neutral", "red_flags": [], "green_flags": []}

        messages = [
            {
                "role": "system",
                "content": """Analiza el texto de un anuncio inmobiliario.
                Identifica señales positivas y negativas (red flags).
                Responde SOLO con JSON válido.""",
            },
            {
                "role": "user",
                "content": f"""
                Texto: "{text[:1000]}"

                Responde con:
                {{
                    "score": <-1.0 a 1.0>,
                    "label": <"very_positive"|"positive"|"neutral"|"negative"|"very_negative">,
                    "red_flags": [<señales preocupantes como "urgente", "owner needs money", etc.>],
                    "green_flags": [<señales positivas como "renovado", "exclusivo", "inversión"]>
                }}
                """,
            },
        ]

        response = await self._call_ai(messages, response_format={"type": "json_object"})
        if not response:
            return {"score": 0, "label": "neutral", "red_flags": [], "green_flags": []}

        try:
            return json.loads(response)
        except Exception:
            return {"score": 0, "label": "neutral", "red_flags": [], "green_flags": []}

    async def match_buyer_to_properties(
        self,
        buyer_preferences: Dict,
        properties: List[Dict],
        top_n: int = 10,
    ) -> List[Dict]:
        """
        Matching inteligente entre un comprador y propiedades disponibles.

        Returns:
            Lista de propiedades ordenadas por match_score con razones
        """
        if not properties:
            return []

        messages = [
            {
                "role": "system",
                "content": self.MARKET_CONTEXT + """

                Eres un asesor inmobiliario experto que encuentra la propiedad perfecta
                para cada cliente. Analiza las preferencias del comprador y calcula
                el porcentaje de match con cada propiedad.

                Responde SOLO con JSON válido.
                """,
            },
            {
                "role": "user",
                "content": f"""
                PERFIL DEL COMPRADOR:
                {json.dumps(buyer_preferences, ensure_ascii=False, default=str)}

                PROPIEDADES DISPONIBLES (máximo 20):
                {json.dumps(properties[:20], ensure_ascii=False, default=str)}

                Para cada propiedad devuelve su ID y el match score.
                Ordena de mayor a menor match.

                Responde con este formato:
                {{
                    "matches": [
                        {{
                            "property_id": "<id>",
                            "match_score": <0-100>,
                            "match_reasons": ["razón 1", "razón 2"],
                            "concerns": ["preocupación si hay alguna"]
                        }}
                    ]
                }}

                Solo incluye propiedades con match_score >= 40.
                """,
            },
        ]

        response = await self._call_ai(
            messages,
            response_format={"type": "json_object"},
            premium=True,
        )

        if not response:
            return []

        try:
            result = json.loads(response)
            matches = result.get("matches", [])
            # Ordenar por score y tomar top N
            matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return matches[:top_n]
        except Exception as e:
            logger.error("Error en matching", error=str(e))
            return []

    async def estimate_market_value(
        self,
        property_data: Dict,
        comparable_properties: List[Dict],
    ) -> Dict:
        """
        Estimar el valor de mercado basado en comparables.
        """
        messages = [
            {
                "role": "system",
                "content": self.MARKET_CONTEXT + """

                Eres un tasador inmobiliario profesional con 20 años de experiencia
                en Punta del Este. Usa el método comparativo de mercado (CMA) para
                estimar el valor real de la propiedad.

                Responde SOLO con JSON válido.
                """,
            },
            {
                "role": "user",
                "content": f"""
                PROPIEDAD A TASAR:
                {json.dumps(property_data, ensure_ascii=False, default=str)}

                PROPIEDADES COMPARABLES:
                {json.dumps(comparable_properties[:10], ensure_ascii=False, default=str)}

                Calcula el valor estimado de mercado.

                Responde con:
                {{
                    "estimated_value_usd": <número>,
                    "value_range_min": <número>,
                    "value_range_max": <número>,
                    "price_per_m2_estimated": <número>,
                    "confidence": <"high"|"medium"|"low">,
                    "vs_listing_price_pct": <% diferencia vs precio publicado, negativo=subvaluado>,
                    "methodology": "<explicación breve>",
                    "adjustments": [<ajustes aplicados: "vista al mar +8%", etc.>]
                }}
                """,
            },
        ]

        response = await self._call_ai(
            messages,
            response_format={"type": "json_object"},
            premium=True,
        )

        if not response:
            return {}

        try:
            return json.loads(response)
        except Exception:
            return {}

    async def generate_market_report(
        self,
        zone_name: str,
        stats: Dict,
    ) -> str:
        """
        Generar reporte de mercado para una zona específica.
        """
        messages = [
            {
                "role": "system",
                "content": self.MARKET_CONTEXT + """

                Eres un analista de mercado inmobiliario que escribe reportes
                profesionales para inversores y desarrolladores.
                Usa datos reales para conclusiones concretas.
                """,
            },
            {
                "role": "user",
                "content": f"""
                Genera un reporte de mercado para la zona: {zone_name}

                DATOS ACTUALES:
                {json.dumps(stats, ensure_ascii=False, default=str)}

                El reporte debe incluir:
                1. Resumen ejecutivo (2-3 párrafos)
                2. Análisis de precios y tendencias
                3. Oportunidades detectadas
                4. Riesgos o alertas
                5. Recomendación de inversión

                Formato: texto corrido con subtítulos en markdown.
                Extensión: 300-500 palabras.
                """,
            },
        ]

        response = await self._call_ai(messages, temperature=0.5, premium=True)
        return response or "Reporte no disponible."

    async def batch_score_properties(
        self,
        properties: List[Dict],
        batch_size: int = 10,
    ) -> List[Dict]:
        """
        Puntuar un lote de propiedades en paralelo.
        Optimizado para procesar muchas propiedades eficientemente.
        """
        results = []
        semaphore = asyncio.Semaphore(5)  # Max 5 llamadas concurrentes

        async def score_with_semaphore(prop_data: Dict) -> Dict:
            async with semaphore:
                score = await self.score_property(prop_data)
                score["property_id"] = prop_data.get("id")
                return score

        for i in range(0, len(properties), batch_size):
            batch = properties[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[score_with_semaphore(p) for p in batch],
                return_exceptions=True,
            )
            for r in batch_results:
                if not isinstance(r, Exception):
                    results.append(r)

        logger.info(f"✅ {len(results)} propiedades puntuadas por IA")
        return results


# Instancia singleton del motor
ai_engine = PropertyAIEngine()
