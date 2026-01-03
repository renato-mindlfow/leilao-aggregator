import os
import json
import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

class AINormalizer:
    """Serviço de normalização de dados de imóveis usando IA"""
    
    # Categorias válidas padronizadas
    VALID_CATEGORIES = [
        "Apartamento",
        "Casa",
        "Terreno",
        "Comercial",
        "Galpão",
        "Fazenda",
        "Sítio",
        "Chácara",
        "Sala Comercial",
        "Loja",
        "Prédio",
        "Garagem",
        "Imóvel Rural",
        "Outro"
    ]
    
    # Estados brasileiros
    BRAZILIAN_STATES = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
        "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
        "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
        "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
        "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"
    }
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        
    async def normalize_property(self, property_data: Dict) -> Dict:
        """Normaliza um único imóvel usando IA"""
        
        # Primeiro, tenta normalização baseada em regras
        normalized = self._rule_based_normalization(property_data)
        
        # Se dados ainda estão incompletos ou inconsistentes, usa IA
        if self._needs_ai_normalization(normalized):
            normalized = await self._ai_normalization(normalized)
        
        return normalized
    
    async def normalize_batch(self, properties: List[Dict], batch_size: int = 10) -> List[Dict]:
        """Normaliza um lote de imóveis"""
        normalized = []
        
        for i in range(0, len(properties), batch_size):
            batch = properties[i:i + batch_size]
            
            # Processar batch com IA
            batch_normalized = await self._ai_normalize_batch(batch)
            normalized.extend(batch_normalized)
            
            logger.info(f"Normalizados {len(normalized)}/{len(properties)} imóveis")
        
        return normalized
    
    def _rule_based_normalization(self, data: Dict) -> Dict:
        """Normalização baseada em regras (sem IA)"""
        
        normalized = data.copy()
        
        # Normalizar categoria
        if 'category' in normalized and normalized['category']:
            normalized['category'] = self._normalize_category(normalized['category'])
        
        # Normalizar estado
        if 'state' in normalized and normalized['state']:
            normalized['state'] = self._normalize_state(normalized['state'])
        
        # Normalizar cidade (capitalização)
        if 'city' in normalized and normalized['city']:
            normalized['city'] = self._normalize_city(normalized['city'])
        
        # Limpar valores numéricos
        if 'price' in normalized:
            normalized['price'] = self._clean_price(normalized['price'])
        
        if 'area' in normalized:
            normalized['area'] = self._clean_area(normalized['area'])
        
        if 'discount' in normalized:
            normalized['discount'] = self._clean_discount(normalized['discount'])
        
        return normalized
    
    def _normalize_category(self, category: str) -> str:
        """Normaliza categoria para uma das categorias válidas"""
        
        if not category:
            return "Outro"
        
        category_lower = category.lower().strip()
        
        # Mapeamento de variações comuns
        category_map = {
            # Apartamento
            "apartamento": "Apartamento",
            "apto": "Apartamento",
            "ap": "Apartamento",
            "flat": "Apartamento",
            "kitnet": "Apartamento",
            "kitinete": "Apartamento",
            "studio": "Apartamento",
            "cobertura": "Apartamento",
            "duplex": "Apartamento",
            "triplex": "Apartamento",
            "loft": "Apartamento",
            
            # Casa
            "casa": "Casa",
            "residência": "Casa",
            "residencia": "Casa",
            "sobrado": "Casa",
            "casa térrea": "Casa",
            "casa terrea": "Casa",
            "bangalô": "Casa",
            "bangalo": "Casa",
            "edícula": "Casa",
            "edicula": "Casa",
            
            # Terreno
            "terreno": "Terreno",
            "lote": "Terreno",
            "gleba": "Terreno",
            "área": "Terreno",
            "area": "Terreno",
            "fração de terra": "Terreno",
            "fracao de terra": "Terreno",
            
            # Comercial
            "comercial": "Comercial",
            "ponto comercial": "Comercial",
            "imóvel comercial": "Comercial",
            "imovel comercial": "Comercial",
            "estabelecimento": "Comercial",
            
            # Galpão
            "galpão": "Galpão",
            "galpao": "Galpão",
            "barracão": "Galpão",
            "barracao": "Galpão",
            "armazém": "Galpão",
            "armazem": "Galpão",
            "depósito": "Galpão",
            "deposito": "Galpão",
            "pavilhão": "Galpão",
            "pavilhao": "Galpão",
            
            # Fazenda
            "fazenda": "Fazenda",
            "hacienda": "Fazenda",
            "estância": "Fazenda",
            "estancia": "Fazenda",
            
            # Sítio
            "sítio": "Sítio",
            "sitio": "Sítio",
            
            # Chácara
            "chácara": "Chácara",
            "chacara": "Chácara",
            
            # Sala Comercial
            "sala comercial": "Sala Comercial",
            "sala": "Sala Comercial",
            "conjunto comercial": "Sala Comercial",
            "escritório": "Sala Comercial",
            "escritorio": "Sala Comercial",
            
            # Loja
            "loja": "Loja",
            "box": "Loja",
            "quiosque": "Loja",
            
            # Prédio
            "prédio": "Prédio",
            "predio": "Prédio",
            "edifício": "Prédio",
            "edificio": "Prédio",
            
            # Garagem
            "garagem": "Garagem",
            "vaga de garagem": "Garagem",
            "vaga": "Garagem",
            "estacionamento": "Garagem",
            
            # Imóvel Rural
            "imóvel rural": "Imóvel Rural",
            "imovel rural": "Imóvel Rural",
            "rural": "Imóvel Rural",
            "propriedade rural": "Imóvel Rural",
        }
        
        # Busca direta
        if category_lower in category_map:
            return category_map[category_lower]
        
        # Busca parcial
        for key, value in category_map.items():
            if key in category_lower or category_lower in key:
                return value
        
        # Se não encontrou, retorna "Outro"
        return "Outro"
    
    def _normalize_state(self, state: str) -> str:
        """Normaliza estado para sigla de 2 letras"""
        
        if not state:
            return ""
        
        state = state.strip().upper()
        
        # Já é sigla válida
        if len(state) == 2 and state in self.BRAZILIAN_STATES:
            return state
        
        # Busca por nome completo
        state_lower = state.lower()
        for sigla, nome in self.BRAZILIAN_STATES.items():
            if nome.lower() == state_lower:
                return sigla
        
        # Busca parcial
        for sigla, nome in self.BRAZILIAN_STATES.items():
            if state_lower in nome.lower() or nome.lower() in state_lower:
                return sigla
        
        return state[:2].upper() if len(state) >= 2 else ""
    
    def _normalize_city(self, city: str) -> str:
        """Normaliza nome da cidade"""
        
        if not city:
            return ""
        
        # Remove espaços extras e capitaliza
        city = ' '.join(city.split())
        
        # Capitalização inteligente (mantém preposições em minúsculo)
        prepositions = ['de', 'da', 'do', 'das', 'dos', 'e']
        words = city.lower().split()
        
        normalized_words = []
        for i, word in enumerate(words):
            if i == 0 or word not in prepositions:
                normalized_words.append(word.capitalize())
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def _clean_price(self, price) -> Optional[float]:
        """Limpa e converte preço para float"""
        
        if price is None:
            return None
        
        if isinstance(price, (int, float)):
            return float(price) if price > 0 else None
        
        if isinstance(price, str):
            # Remove caracteres não numéricos exceto ponto e vírgula
            cleaned = ''.join(c for c in price if c.isdigit() or c in '.,')
            
            # Trata formato brasileiro (1.234.567,89)
            if ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                cleaned = cleaned.replace(',', '.')
            
            try:
                value = float(cleaned)
                return value if value > 0 else None
            except:
                return None
        
        return None
    
    def _clean_area(self, area) -> Optional[float]:
        """Limpa e converte área para float"""
        
        if area is None:
            return None
        
        if isinstance(area, (int, float)):
            return float(area) if area > 0 else None
        
        if isinstance(area, str):
            # Remove unidades e caracteres especiais
            cleaned = area.lower().replace('m²', '').replace('m2', '').replace('ha', '')
            cleaned = ''.join(c for c in cleaned if c.isdigit() or c in '.,')
            
            # Trata formato brasileiro
            if ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                cleaned = cleaned.replace(',', '.')
            
            try:
                value = float(cleaned)
                
                # Se tinha 'ha', converte para m²
                if 'ha' in area.lower():
                    value = value * 10000
                
                return value if value > 0 else None
            except:
                return None
        
        return None
    
    def _clean_discount(self, discount) -> Optional[float]:
        """Limpa e converte desconto para float (percentual)"""
        
        if discount is None:
            return None
        
        if isinstance(discount, (int, float)):
            # Se for maior que 1, assume que já é percentual
            if discount > 1:
                return float(discount) if 0 < discount <= 100 else None
            else:
                return float(discount) * 100 if 0 < discount <= 1 else None
        
        if isinstance(discount, str):
            cleaned = ''.join(c for c in discount if c.isdigit() or c in '.,')
            
            if ',' in cleaned:
                cleaned = cleaned.replace(',', '.')
            
            try:
                value = float(cleaned)
                return value if 0 < value <= 100 else None
            except:
                return None
        
        return None
    
    def _needs_ai_normalization(self, data: Dict) -> bool:
        """Verifica se precisa de normalização com IA"""
        
        # Se categoria ainda é "Outro", pode precisar de IA
        if data.get('category') == 'Outro':
            return True
        
        # Se não tem cidade ou estado, pode extrair do endereço
        if not data.get('city') or not data.get('state'):
            if data.get('address'):
                return True
        
        return False
    
    async def _ai_normalization(self, data: Dict) -> Dict:
        """Normalização usando GPT-4o-mini"""
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY não configurada, pulando normalização IA")
            return data
        
        prompt = f"""Analise os dados do imóvel abaixo e retorne um JSON normalizado.

Dados originais:
- Título: {data.get('title', '')}
- Descrição: {data.get('description', '')[:500]}
- Endereço: {data.get('address', '')}
- Categoria atual: {data.get('category', '')}
- Cidade: {data.get('city', '')}
- Estado: {data.get('state', '')}

Categorias válidas: {', '.join(self.VALID_CATEGORIES)}

Retorne APENAS um JSON válido com:
{{
    "category": "categoria normalizada",
    "city": "nome da cidade",
    "state": "UF (2 letras)",
    "address_normalized": "endereço limpo e padronizado"
}}

Se não conseguir determinar algum campo, use null."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 200
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Validar resposta da API antes de acessar campos
                    if not result or 'choices' not in result or len(result['choices']) == 0:
                        logger.warning(f"Resposta vazia ou inválida da OpenAI")
                        return data  # Retorna dados originais sem normalização
                    
                    message = result['choices'][0].get('message', {})
                    content = message.get('content', '')
                    if not content:
                        logger.warning(f"Content vazio na resposta da OpenAI")
                        return data  # Retorna dados originais sem normalização
                    
                    # Extrair JSON da resposta
                    try:
                        # Remove possíveis marcadores de código
                        content = content.replace('```json', '').replace('```', '').strip()
                        ai_data = json.loads(content)
                        
                        # Mesclar dados da IA com os originais
                        if ai_data.get('category') and ai_data['category'] in self.VALID_CATEGORIES:
                            data['category'] = ai_data['category']
                        
                        if ai_data.get('city') and not data.get('city'):
                            data['city'] = ai_data['city']
                        
                        if ai_data.get('state') and not data.get('state'):
                            data['state'] = ai_data['state']
                        
                        if ai_data.get('address_normalized'):
                            data['address'] = ai_data['address_normalized']
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Erro ao parsear resposta da IA: {content}")
                
        except Exception as e:
            logger.error(f"Erro na normalização IA: {e}")
        
        return data
    
    async def _ai_normalize_batch(self, batch: List[Dict]) -> List[Dict]:
        """Normaliza um batch de imóveis com uma única chamada à IA"""
        
        if not self.api_key:
            return [self._rule_based_normalization(p) for p in batch]
        
        # Primeiro aplica regras
        batch = [self._rule_based_normalization(p) for p in batch]
        
        # Filtra os que precisam de IA
        needs_ai = [(i, p) for i, p in enumerate(batch) if self._needs_ai_normalization(p)]
        
        if not needs_ai:
            return batch
        
        # Prepara prompt para batch
        items_text = "\n".join([
            f"[{i}] Título: {p.get('title', '')[:100]} | Categoria: {p.get('category', '')} | Endereço: {p.get('address', '')[:100]}"
            for i, p in needs_ai
        ])
        
        prompt = f"""Analise os imóveis abaixo e normalize os dados.

{items_text}

Categorias válidas: {', '.join(self.VALID_CATEGORIES)}

Retorne APENAS um JSON array com objetos no formato:
[
    {{"index": 0, "category": "...", "city": "...", "state": "UF"}},
    ...
]"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Validar resposta da API antes de acessar campos
                    if not result or 'choices' not in result or len(result['choices']) == 0:
                        logger.warning(f"Resposta vazia ou inválida da OpenAI no batch")
                        return batch  # Retorna dados originais sem normalização
                    
                    message = result['choices'][0].get('message', {})
                    content = message.get('content', '')
                    if not content:
                        logger.warning(f"Content vazio na resposta da OpenAI no batch")
                        return batch  # Retorna dados originais sem normalização
                    
                    content = content.replace('```json', '').replace('```', '').strip()
                    
                    ai_results = json.loads(content)
                    
                    # Aplicar resultados da IA
                    for ai_item in ai_results:
                        idx = ai_item.get('index')
                        if idx is not None:
                            # Encontrar o item original
                            for orig_idx, orig_data in needs_ai:
                                if orig_idx == idx:
                                    if ai_item.get('category') in self.VALID_CATEGORIES:
                                        batch[orig_idx]['category'] = ai_item['category']
                                    if ai_item.get('city'):
                                        batch[orig_idx]['city'] = ai_item['city']
                                    if ai_item.get('state'):
                                        batch[orig_idx]['state'] = ai_item['state']
                                    break
        
        except Exception as e:
            logger.error(f"Erro na normalização IA batch: {e}")
        
        return batch


# Instância global
ai_normalizer = AINormalizer()



