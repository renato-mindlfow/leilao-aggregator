"""
Geocoding service for converting addresses to coordinates.
Uses a simple approach with Brazilian city coordinates for MVP.
For production, integrate with Google Maps Geocoding API.
"""
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Brazilian city coordinates (latitude, longitude)
# This is a simplified approach for MVP - in production, use Google Maps Geocoding API
CITY_COORDINATES = {
    # Sao Paulo
    ("sao paulo", "sp"): (-23.5505, -46.6333),
    ("campinas", "sp"): (-22.9099, -47.0626),
    ("santos", "sp"): (-23.9608, -46.3336),
    ("ribeirao preto", "sp"): (-21.1775, -47.8103),
    ("sorocaba", "sp"): (-23.5015, -47.4526),
    ("sao jose dos campos", "sp"): (-23.1896, -45.8841),
    ("osasco", "sp"): (-23.5324, -46.7917),
    ("guarulhos", "sp"): (-23.4543, -46.5337),
    
    # Rio de Janeiro
    ("rio de janeiro", "rj"): (-22.9068, -43.1729),
    ("niteroi", "rj"): (-22.8838, -43.1034),
    ("petropolis", "rj"): (-22.5112, -43.1779),
    ("nova iguacu", "rj"): (-22.7556, -43.4603),
    
    # Minas Gerais
    ("belo horizonte", "mg"): (-19.9167, -43.9345),
    ("uberlandia", "mg"): (-18.9186, -48.2772),
    ("contagem", "mg"): (-19.9318, -44.0539),
    ("juiz de fora", "mg"): (-21.7642, -43.3496),
    
    # Parana
    ("curitiba", "pr"): (-25.4284, -49.2733),
    ("londrina", "pr"): (-23.3045, -51.1696),
    ("maringa", "pr"): (-23.4205, -51.9333),
    ("ponta grossa", "pr"): (-25.0916, -50.1668),
    ("cascavel", "pr"): (-24.9578, -53.4595),
    
    # Rio Grande do Sul
    ("porto alegre", "rs"): (-30.0346, -51.2177),
    ("caxias do sul", "rs"): (-29.1634, -51.1797),
    ("pelotas", "rs"): (-31.7654, -52.3376),
    ("canoas", "rs"): (-29.9178, -51.1839),
    
    # Santa Catarina
    ("florianopolis", "sc"): (-27.5954, -48.5480),
    ("joinville", "sc"): (-26.3045, -48.8487),
    ("blumenau", "sc"): (-26.9194, -49.0661),
    ("chapeco", "sc"): (-27.1006, -52.6152),
    
    # Bahia
    ("salvador", "ba"): (-12.9714, -38.5014),
    ("feira de santana", "ba"): (-12.2664, -38.9663),
    ("vitoria da conquista", "ba"): (-14.8615, -40.8442),
    
    # Pernambuco
    ("recife", "pe"): (-8.0476, -34.8770),
    ("olinda", "pe"): (-8.0089, -34.8553),
    ("jaboatao dos guararapes", "pe"): (-8.1128, -35.0158),
    
    # Ceara
    ("fortaleza", "ce"): (-3.7172, -38.5433),
    ("caucaia", "ce"): (-3.7361, -38.6531),
    ("juazeiro do norte", "ce"): (-7.2131, -39.3151),
    
    # Goias
    ("goiania", "go"): (-16.6869, -49.2648),
    ("aparecida de goiania", "go"): (-16.8198, -49.2469),
    ("anapolis", "go"): (-16.3281, -48.9534),
    
    # Distrito Federal
    ("brasilia", "df"): (-15.7975, -47.8919),
    
    # Amazonas
    ("manaus", "am"): (-3.1190, -60.0217),
    
    # Para
    ("belem", "pa"): (-1.4558, -48.4902),
    
    # Maranhao
    ("sao luis", "ma"): (-2.5307, -44.3068),
    
    # Piaui
    ("teresina", "pi"): (-5.0892, -42.8019),
    
    # Rio Grande do Norte
    ("natal", "rn"): (-5.7945, -35.2110),
    
    # Paraiba
    ("joao pessoa", "pb"): (-7.1195, -34.8450),
    
    # Alagoas
    ("maceio", "al"): (-9.6498, -35.7089),
    
    # Sergipe
    ("aracaju", "se"): (-10.9472, -37.0731),
    
    # Espirito Santo
    ("vitoria", "es"): (-20.3155, -40.3128),
    ("vila velha", "es"): (-20.3297, -40.2925),
    
    # Mato Grosso
    ("cuiaba", "mt"): (-15.6014, -56.0979),
    
    # Mato Grosso do Sul
    ("campo grande", "ms"): (-20.4697, -54.6201),
    
    # Rondonia
    ("porto velho", "ro"): (-8.7612, -63.9004),
    
    # Acre
    ("rio branco", "ac"): (-9.9754, -67.8249),
    
    # Tocantins
    ("palmas", "to"): (-10.2491, -48.3243),
    
    # Roraima
    ("boa vista", "rr"): (2.8235, -60.6758),
    
    # Amapa
    ("macapa", "ap"): (0.0349, -51.0694),
}

# State capital coordinates as fallback
STATE_CAPITALS = {
    "sp": (-23.5505, -46.6333),  # Sao Paulo
    "rj": (-22.9068, -43.1729),  # Rio de Janeiro
    "mg": (-19.9167, -43.9345),  # Belo Horizonte
    "pr": (-25.4284, -49.2733),  # Curitiba
    "rs": (-30.0346, -51.2177),  # Porto Alegre
    "sc": (-27.5954, -48.5480),  # Florianopolis
    "ba": (-12.9714, -38.5014),  # Salvador
    "pe": (-8.0476, -34.8770),   # Recife
    "ce": (-3.7172, -38.5433),   # Fortaleza
    "go": (-16.6869, -49.2648),  # Goiania
    "df": (-15.7975, -47.8919),  # Brasilia
    "am": (-3.1190, -60.0217),   # Manaus
    "pa": (-1.4558, -48.4902),   # Belem
    "ma": (-2.5307, -44.3068),   # Sao Luis
    "pi": (-5.0892, -42.8019),   # Teresina
    "rn": (-5.7945, -35.2110),   # Natal
    "pb": (-7.1195, -34.8450),   # Joao Pessoa
    "al": (-9.6498, -35.7089),   # Maceio
    "se": (-10.9472, -37.0731),  # Aracaju
    "es": (-20.3155, -40.3128),  # Vitoria
    "mt": (-15.6014, -56.0979),  # Cuiaba
    "ms": (-20.4697, -54.6201),  # Campo Grande
    "ro": (-8.7612, -63.9004),   # Porto Velho
    "ac": (-9.9754, -67.8249),   # Rio Branco
    "to": (-10.2491, -48.3243),  # Palmas
    "rr": (2.8235, -60.6758),    # Boa Vista
    "ap": (0.0349, -51.0694),    # Macapa
}


def normalize_city_name(city: str) -> str:
    """Normalize city name for lookup."""
    import unicodedata
    # Remove accents
    normalized = unicodedata.normalize('NFD', city.lower())
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return normalized.strip()


def get_coordinates(city: str, state: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a city/state combination.
    Returns (latitude, longitude) or None if not found.
    """
    normalized_city = normalize_city_name(city)
    normalized_state = state.lower().strip()
    
    # Try exact city match
    key = (normalized_city, normalized_state)
    if key in CITY_COORDINATES:
        return CITY_COORDINATES[key]
    
    # Try partial city match
    for (city_name, state_code), coords in CITY_COORDINATES.items():
        if state_code == normalized_state and normalized_city in city_name:
            return coords
        if state_code == normalized_state and city_name in normalized_city:
            return coords
    
    # Fallback to state capital
    if normalized_state in STATE_CAPITALS:
        logger.info(f"Using state capital coordinates for {city}, {state}")
        return STATE_CAPITALS[normalized_state]
    
    logger.warning(f"Could not find coordinates for {city}, {state}")
    return None


def add_random_offset(lat: float, lon: float, max_offset: float = 0.01) -> Tuple[float, float]:
    """
    Add a small random offset to coordinates to spread out markers.
    This helps when multiple properties are in the same city.
    """
    import random
    lat_offset = random.uniform(-max_offset, max_offset)
    lon_offset = random.uniform(-max_offset, max_offset)
    return (lat + lat_offset, lon + lon_offset)


class GeocodingService:
    """Service for geocoding addresses."""
    
    def __init__(self):
        self.cache: dict[str, Tuple[float, float]] = {}
    
    def geocode(self, city: str, state: str, add_offset: bool = True) -> Optional[Tuple[float, float]]:
        """
        Geocode a city/state to coordinates.
        
        Args:
            city: City name
            state: State code (e.g., "SP", "RJ")
            add_offset: Whether to add a small random offset (useful for multiple properties in same city)
            
        Returns:
            (latitude, longitude) tuple or None if not found
        """
        cache_key = f"{city.lower()}_{state.lower()}"
        
        if cache_key in self.cache:
            coords = self.cache[cache_key]
        else:
            coords = get_coordinates(city, state)
            if coords:
                self.cache[cache_key] = coords
        
        if coords and add_offset:
            return add_random_offset(coords[0], coords[1])
        
        return coords
    
    def geocode_property(self, property_data: dict) -> Optional[Tuple[float, float]]:
        """
        Geocode a property based on its address information.
        
        Args:
            property_data: Dictionary with 'city' and 'state' keys
            
        Returns:
            (latitude, longitude) tuple or None if not found
        """
        city = property_data.get('city', '')
        state = property_data.get('state', '')
        
        if not city or not state:
            return None
        
        return self.geocode(city, state)


# Global instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get the global geocoding service instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
