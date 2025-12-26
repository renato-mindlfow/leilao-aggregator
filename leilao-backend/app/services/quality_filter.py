"""
Quality Filter Service - Validates and cleans property data using AI and rules.
Filters out non-properties, normalizes categories, validates location, images, and prices.
"""
import logging
import re
import requests
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.models.property import Property, PropertyCategory, AuctionType

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Result of property validation."""
    VALID = "valid"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass
class QualityFilterResult:
    """Result of quality filtering."""
    is_valid: bool
    property: Optional[Property] = None
    rejection_reason: Optional[str] = None
    warnings: list[str] = None
    changes_made: list[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.changes_made is None:
            self.changes_made = []


class QualityFilter:
    """
    Quality filter that validates property data using:
    1. Rule-based validation (fast, no API calls)
    2. AI-based validation (GPT-4o-mini for ambiguous cases)
    """
    
    # Invalid items - automatically reject
    INVALID_KEYWORDS = [
        "veículos", "veiculo", "motocicleta", "caminhão", "caminhao", "carro", "automóvel", "automovel",
        "máquinas", "maquinas", "equipamentos", "sucata", "móveis", "moveis",
        "título patrimonial", "titulo patrimonial", "cédula de crédito", "cedula de credito",
        "página não encontrada", "pagina nao encontrada", "error", "teste",
        "bens móveis", "bens moveis", "equipamento", "ferramenta"
    ]
    
    # Invalid cities
    INVALID_CITIES = [
        "shrink", "das mesmas", "e no campo", "VOLTAR...", "Não informada", "Nao informada",
        "Não informado", "Nao informado", "N/A", "n/a", "null", "undefined"
    ]
    
    # Brazilian states (2-letter codes)
    BRAZILIAN_STATES = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
        'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
        'SP', 'SE', 'TO'
    ]
    
    # Keywords for category inference
    CATEGORY_KEYWORDS = {
        PropertyCategory.CASA: ["casa", "sobrado", "residência", "residencia", "chácara", "chacara", "sítio", "sitio", "fazenda"],
        PropertyCategory.APARTAMENTO: ["apartamento", "apto", "apt", "ap", "flat", "cobertura", "kitnet", "loft"],
        PropertyCategory.TERRENO: ["terreno", "lote", "área", "area", "gleba", "chácara", "chacara"],
        PropertyCategory.COMERCIAL: ["comercial", "loja", "sala", "galpão", "galpao", "prédio comercial", "predio comercial", "escritório", "escritorio", "ponto comercial"],
        PropertyCategory.RURAL: ["fazenda", "sítio", "sitio", "chácara", "chacara", "hectares", "hectare"],
        PropertyCategory.ESTACIONAMENTO: ["garagem", "vaga", "estacionamento", "box"]
    }
    
    def __init__(self, use_ai: bool = True, openai_api_key: Optional[str] = None):
        """
        Initialize quality filter.
        
        Args:
            use_ai: Whether to use AI for category inference (requires OpenAI API key)
            openai_api_key: OpenAI API key (optional, can use env var OPENAI_API_KEY)
        """
        self.use_ai = use_ai
        self.openai_api_key = openai_api_key
        if self.use_ai and not self.openai_api_key:
            import os
            self.openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    def validate_and_clean(self, prop: Property) -> QualityFilterResult:
        """
        Validate and clean a property.
        
        Args:
            prop: Property to validate
            
        Returns:
            QualityFilterResult with validation result and cleaned property
        """
        result = QualityFilterResult(is_valid=True, property=prop)
        
        # 1. Validate if it's a property (not vehicle, equipment, etc.)
        if not self._is_valid_property(prop, result):
            result.is_valid = False
            return result
        
        # 2. Normalize category
        self._normalize_category(prop, result)
        
        # 3. Validate state/city
        if not self._validate_location(prop, result):
            result.is_valid = False
            return result
        
        # 4. Validate image
        self._validate_image(prop, result)
        
        # 5. Validate prices
        if not self._validate_prices(prop, result):
            result.is_valid = False
            return result
        
        return result
    
    def _is_valid_property(self, prop: Property, result: QualityFilterResult) -> bool:
        """Check if this is a valid property (not vehicle, equipment, etc.)."""
        title = (prop.title or "").lower()
        description = (prop.description or "").lower()
        category = (prop.category.value if prop.category else "").lower()
        
        combined_text = f"{title} {description} {category}"
        
        # Check for invalid keywords
        for keyword in self.INVALID_KEYWORDS:
            if keyword in combined_text:
                result.rejection_reason = f"Contém palavra-chave inválida: '{keyword}' (não é imóvel)"
                logger.warning(f"Property rejected - invalid keyword '{keyword}': {title[:50]}")
                return False
        
        # If we have AI available, use it for ambiguous cases
        if self.use_ai and self.openai_api_key:
            # Only use AI if title/description is ambiguous
            if any(word in combined_text for word in ["bem", "lote", "item", "objeto"]):
                is_valid = self._ai_validate_is_property(title, description)
                if not is_valid:
                    result.rejection_reason = "IA determinou que não é um imóvel"
                    return False
        
        return True
    
    def _normalize_category(self, prop: Property, result: QualityFilterResult) -> None:
        """Normalize category using keywords or AI."""
        if prop.category and prop.category != PropertyCategory.OUTRO:
            return  # Already has a valid category
        
        title = (prop.title or "").lower()
        description = (prop.description or "").lower()
        combined_text = f"{title} {description}"
        
        # Try keyword-based inference first
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    old_category = prop.category.value if prop.category else "Outro"
                    prop.category = category
                    result.changes_made.append(f"Categoria inferida: {old_category} -> {category.value}")
                    logger.info(f"Inferred category '{category.value}' for property: {title[:50]}")
                    return
        
        # If still "Outro" and AI is available, use AI
        if self.use_ai and self.openai_api_key and (not prop.category or prop.category == PropertyCategory.OUTRO):
            inferred_category = self._ai_infer_category(title, description)
            if inferred_category:
                old_category = prop.category.value if prop.category else "Outro"
                prop.category = inferred_category
                result.changes_made.append(f"Categoria inferida pela IA: {old_category} -> {inferred_category.value}")
                logger.info(f"AI inferred category '{inferred_category.value}' for property: {title[:50]}")
    
    def _validate_location(self, prop: Property, result: QualityFilterResult) -> bool:
        """Validate state and city."""
        # Validate state
        if not prop.state or len(prop.state) != 2 or prop.state.upper() not in self.BRAZILIAN_STATES:
            # Try to extract from title or address
            extracted_state = self._extract_state_from_text(prop.title or "", prop.address or "")
            if extracted_state:
                result.changes_made.append(f"Estado extraído do texto: {prop.state} -> {extracted_state}")
                prop.state = extracted_state
            else:
                result.rejection_reason = f"Estado inválido: {prop.state}"
                logger.warning(f"Property rejected - invalid state: {prop.state}")
                return False
        
        # Validate city
        if not prop.city or prop.city.strip() in self.INVALID_CITIES:
            # Try to extract from title or address
            extracted_city = self._extract_city_from_text(prop.title or "", prop.address or "", prop.state)
            if extracted_city:
                result.changes_made.append(f"Cidade extraída do texto: {prop.city} -> {extracted_city}")
                prop.city = extracted_city
            else:
                result.rejection_reason = f"Cidade inválida: {prop.city}"
                logger.warning(f"Property rejected - invalid city: {prop.city}")
                return False
        
        return True
    
    def _validate_image(self, prop: Property, result: QualityFilterResult) -> None:
        """Validate image URL - reject logos, check if image is valid."""
        if not prop.image_url:
            result.warnings.append("Propriedade sem foto")
            return
        
        image_url_lower = prop.image_url.lower()
        
        # Reject URLs with "logo"
        if "logo" in image_url_lower:
            prop.image_url = None
            result.changes_made.append("URL de imagem removida (contém 'logo')")
            result.warnings.append("Foto inválida removida (logo)")
            return
        
        # Optional: Check if image URL returns valid image (HTTP 200)
        # This is disabled by default to avoid slowing down the process
        # Uncomment if needed:
        # try:
        #     response = requests.head(prop.image_url, timeout=5, allow_redirects=True)
        #     if response.status_code != 200 or 'image' not in response.headers.get('content-type', ''):
        #         prop.image_url = None
        #         result.warnings.append("URL de imagem inválida")
        # except:
        #     result.warnings.append("Não foi possível validar URL de imagem")
    
    def _validate_prices(self, prop: Property, result: QualityFilterResult) -> bool:
        """Validate prices - second_auction_value must be > 0 or extract from first_auction_value."""
        # second_auction_value is the most important price
        if not prop.second_auction_value or prop.second_auction_value <= 0:
            # Try to use first_auction_value
            if prop.first_auction_value and prop.first_auction_value > 0:
                prop.second_auction_value = prop.first_auction_value
                result.changes_made.append(f"second_auction_value definido a partir de first_auction_value: {prop.second_auction_value}")
            # Try to use evaluation_value
            elif prop.evaluation_value and prop.evaluation_value > 0:
                prop.second_auction_value = prop.evaluation_value
                result.changes_made.append(f"second_auction_value definido a partir de evaluation_value: {prop.second_auction_value}")
            else:
                result.rejection_reason = "Preço inválido (second_auction_value não disponível)"
                logger.warning(f"Property rejected - no valid price")
                return False
        
        return True
    
    def _extract_state_from_text(self, title: str, address: str) -> Optional[str]:
        """Extract state (UF) from text."""
        text = f"{title} {address}".upper()
        
        # Look for state codes in the text
        for state in self.BRAZILIAN_STATES:
            # Look for patterns like " - SP", "/SP", " SP " (with spaces/punctuation)
            if re.search(rf'[-/\s]{state}[\s.,]', text) or text.endswith(state):
                return state
        
        return None
    
    def _extract_city_from_text(self, title: str, address: str, state: Optional[str]) -> Optional[str]:
        """Extract city from text."""
        # This is a simple heuristic - in production, you might want to use a city database
        # or AI for better extraction
        text = f"{title} {address}"
        
        # Try to find city before state code
        if state:
            pattern = rf'(.+?)\s*[-/]\s*{state}'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                city_candidate = match.group(1).strip()
                # Remove common prefixes
                city_candidate = re.sub(r'^.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$', r'\1', city_candidate)
                if len(city_candidate) > 3 and city_candidate.lower() not in self.INVALID_CITIES:
                    return city_candidate.title()
        
        return None
    
    def _ai_validate_is_property(self, title: str, description: str) -> bool:
        """Use AI to validate if this is a property (not vehicle, equipment, etc.)."""
        if not self.openai_api_key:
            return True  # Default to valid if AI not available
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            prompt = f"""Analise o título e descrição abaixo e determine se é um IMÓVEL (casa, apartamento, terreno, comercial) ou outro tipo de bem (veículo, equipamento, etc.).

Título: {title}
Descrição: {description[:500]}

Responda APENAS com "SIM" se for um imóvel ou "NÃO" se não for um imóvel."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return "SIM" in answer
            
        except Exception as e:
            logger.error(f"Error in AI validation: {e}")
            return True  # Default to valid on error
    
    def _ai_infer_category(self, title: str, description: str) -> Optional[PropertyCategory]:
        """Use AI to infer property category."""
        if not self.openai_api_key:
            return None
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            categories = [cat.value for cat in PropertyCategory]
            
            prompt = f"""Analise o título e descrição abaixo e determine a categoria do imóvel.

Título: {title}
Descrição: {description[:500]}

Categorias disponíveis: {', '.join(categories)}

Responda APENAS com uma das categorias acima."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Try to match answer to category
            for category in PropertyCategory:
                if category.value.lower() in answer.lower():
                    return category
            
            return None
            
        except Exception as e:
            logger.error(f"Error in AI category inference: {e}")
            return None

