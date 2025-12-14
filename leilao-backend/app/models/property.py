from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PropertyCategory(str, Enum):
    APARTAMENTO = "Apartamento"
    CASA = "Casa"
    COMERCIAL = "Comercial"
    TERRENO = "Terreno"
    ESTACIONAMENTO = "Estacionamento"
    AREA = "Área"
    RURAL = "Rural"
    OUTRO = "Outro"
    OUTROS = "Outros"


class AuctionType(str, Enum):
    JUDICIAL = "Judicial"
    EXTRAJUDICIAL = "Extrajudicial"
    VENDA_DIRETA = "Venda Direta"
    LEILAO_SFI = "Leilão SFI"
    OUTROS = "Outros"


class PropertyBase(BaseModel):
    title: str = Field(..., description="Título do imóvel")
    category: PropertyCategory = Field(..., description="Categoria do imóvel")
    auction_type: AuctionType = Field(..., description="Tipo de leilão")
    
    # Location
    state: str = Field(..., description="Estado (UF)")
    city: str = Field(..., description="Cidade")
    neighborhood: Optional[str] = Field(None, description="Bairro")
    address: Optional[str] = Field(None, description="Endereço completo")
    
    # Description
    description: Optional[str] = Field(None, description="Descrição do imóvel")
    area_total: Optional[float] = Field(None, description="Área total em m²")
    area_privativa: Optional[float] = Field(None, description="Área privativa em m²")
    
    # Values
    evaluation_value: Optional[float] = Field(None, description="Valor de avaliação")
    first_auction_value: Optional[float] = Field(None, description="Valor do 1º leilão")
    first_auction_date: Optional[datetime] = Field(None, description="Data do 1º leilão")
    second_auction_value: Optional[float] = Field(None, description="Valor do 2º leilão")
    second_auction_date: Optional[datetime] = Field(None, description="Data do 2º leilão")
    discount_percentage: Optional[float] = Field(None, description="Percentual de desconto")
    
    # Images
    image_url: Optional[str] = Field(None, description="URL da imagem principal")
    
    # Source
    auctioneer_id: str = Field(..., description="ID do leiloeiro")
    source_url: str = Field(..., description="URL original no site do leiloeiro")
    
    # Additional info (campos que o site atual não captura bem)
    accepts_financing: Optional[bool] = Field(None, description="Aceita financiamento")
    accepts_fgts: Optional[bool] = Field(None, description="Aceita FGTS")
    accepts_installments: Optional[bool] = Field(None, description="Aceita parcelamento")
    occupation_status: Optional[str] = Field(None, description="Status de ocupação")
    pending_debts: Optional[str] = Field(None, description="Débitos pendentes")
    
    # Auctioneer info
    auctioneer_name: Optional[str] = Field(None, description="Nome do leiloeiro")
    auctioneer_url: Optional[str] = Field(None, description="URL do imóvel no site do leiloeiro")
    
    # Data source
    source: Optional[str] = Field(None, description="Fonte dos dados: 'caixa' ou nome do leiloeiro")
    
    # Geolocation for Google Maps
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[PropertyCategory] = None
    auction_type: Optional[AuctionType] = None
    state: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    area_total: Optional[float] = None
    area_privativa: Optional[float] = None
    evaluation_value: Optional[float] = None
    first_auction_value: Optional[float] = None
    first_auction_date: Optional[datetime] = None
    second_auction_value: Optional[float] = None
    second_auction_date: Optional[datetime] = None
    discount_percentage: Optional[float] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    accepts_financing: Optional[bool] = None
    accepts_fgts: Optional[bool] = None
    accepts_installments: Optional[bool] = None
    occupation_status: Optional[str] = None
    pending_debts: Optional[str] = None
    auctioneer_name: Optional[str] = None
    auctioneer_url: Optional[str] = None
    source: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Property(PropertyBase):
    id: str = Field(..., description="ID único do imóvel")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Deduplication
    dedup_key: Optional[str] = Field(None, description="Chave de deduplicação")
    is_duplicate: bool = Field(default=False, description="Se é duplicata de outro imóvel")
    original_id: Optional[str] = Field(None, description="ID do imóvel original se for duplicata")
    
    # Property lifecycle
    is_active: bool = Field(default=True, description="Se o imóvel ainda está disponível no leiloeiro")
    last_seen_at: Optional[datetime] = Field(None, description="Última vez que o imóvel foi visto no scraper")
    deactivated_at: Optional[datetime] = Field(None, description="Data em que o imóvel foi marcado como inativo")
    
    # Change tracking
    value_changed_at: Optional[datetime] = Field(None, description="Última vez que o valor foi alterado")
    previous_first_auction_value: Optional[float] = Field(None, description="Valor anterior do 1º leilão")
    previous_second_auction_value: Optional[float] = Field(None, description="Valor anterior do 2º leilão")

    class Config:
        from_attributes = True


class PropertyFilter(BaseModel):
    state: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    category: Optional[PropertyCategory] = None
    auction_type: Optional[AuctionType] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_discount: Optional[float] = None
    auctioneer_id: Optional[str] = None
    search_term: Optional[str] = None
    include_duplicates: bool = False
