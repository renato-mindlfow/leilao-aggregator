from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AuctioneerBase(BaseModel):
    name: str = Field(..., description="Nome do leiloeiro")
    website: str = Field(..., description="URL do site do leiloeiro")
    logo_url: Optional[str] = Field(None, description="URL do logo")
    is_active: bool = Field(default=True, description="Se o scraper está ativo")
    scraper_type: Optional[str] = Field(None, description="Tipo de scraper usado")


class AuctioneerCreate(AuctioneerBase):
    pass


class Auctioneer(AuctioneerBase):
    id: str = Field(..., description="ID único do leiloeiro")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_scrape: Optional[datetime] = Field(None, description="Última vez que foi feito scraping")
    property_count: int = Field(default=0, description="Quantidade de imóveis")
    scrape_status: str = Field(default="pending", description="Status do último scraping")
    scrape_error: Optional[str] = Field(None, description="Erro do último scraping")

    class Config:
        from_attributes = True
