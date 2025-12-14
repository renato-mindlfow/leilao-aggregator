"""
Sample data for demonstration purposes.
This will be loaded when the server starts.
"""

from datetime import datetime, timedelta
import random
from app.models.property import PropertyCreate, PropertyCategory, AuctionType


def generate_sample_properties(auctioneers: dict) -> list[PropertyCreate]:
    """Generate sample properties for demonstration."""
    
    # Brazilian states and cities
    locations = [
        {"state": "SP", "city": "São Paulo", "neighborhoods": ["Moema", "Pinheiros", "Vila Mariana", "Itaim Bibi", "Jardins"]},
        {"state": "SP", "city": "Campinas", "neighborhoods": ["Cambuí", "Taquaral", "Barão Geraldo"]},
        {"state": "RJ", "city": "Rio de Janeiro", "neighborhoods": ["Copacabana", "Ipanema", "Leblon", "Botafogo", "Tijuca"]},
        {"state": "MG", "city": "Belo Horizonte", "neighborhoods": ["Savassi", "Lourdes", "Funcionários", "Buritis"]},
        {"state": "PR", "city": "Curitiba", "neighborhoods": ["Batel", "Água Verde", "Centro Cívico", "Ecoville"]},
        {"state": "PR", "city": "Maringá", "neighborhoods": ["Zona 7", "Zona 5", "Centro"]},
        {"state": "RS", "city": "Porto Alegre", "neighborhoods": ["Moinhos de Vento", "Bela Vista", "Petrópolis"]},
        {"state": "SC", "city": "Florianópolis", "neighborhoods": ["Centro", "Trindade", "Lagoa da Conceição"]},
        {"state": "BA", "city": "Salvador", "neighborhoods": ["Barra", "Pituba", "Ondina"]},
        {"state": "PE", "city": "Recife", "neighborhoods": ["Boa Viagem", "Casa Forte", "Espinheiro"]},
        {"state": "CE", "city": "Fortaleza", "neighborhoods": ["Meireles", "Aldeota", "Cocó"]},
        {"state": "GO", "city": "Goiânia", "neighborhoods": ["Setor Bueno", "Setor Marista", "Jardim Goiás"]},
        {"state": "DF", "city": "Brasília", "neighborhoods": ["Asa Sul", "Asa Norte", "Lago Sul", "Sudoeste"]},
    ]
    
    # Property templates
    templates = {
        PropertyCategory.APARTAMENTO: {
            "titles": [
                "Apartamento {beds} quartos - {neighborhood}",
                "Apto {beds} dorms com suíte - {neighborhood}",
                "Apartamento de luxo - {neighborhood}",
                "Cobertura duplex - {neighborhood}",
            ],
            "areas": [(45, 80), (60, 120), (100, 200), (150, 350)],
            "values": [(150000, 400000), (300000, 800000), (500000, 1500000), (1000000, 3000000)],
        },
        PropertyCategory.CASA: {
            "titles": [
                "Casa {beds} quartos - {neighborhood}",
                "Sobrado {beds} dorms - {neighborhood}",
                "Casa em condomínio - {neighborhood}",
                "Casa térrea - {neighborhood}",
            ],
            "areas": [(80, 150), (120, 250), (200, 400), (300, 600)],
            "values": [(200000, 500000), (400000, 1000000), (800000, 2000000), (1500000, 4000000)],
        },
        PropertyCategory.COMERCIAL: {
            "titles": [
                "Sala comercial - {neighborhood}",
                "Loja - {neighborhood}",
                "Galpão industrial - {neighborhood}",
                "Prédio comercial - {neighborhood}",
            ],
            "areas": [(30, 80), (50, 200), (500, 2000), (1000, 5000)],
            "values": [(100000, 300000), (200000, 600000), (500000, 2000000), (1000000, 5000000)],
        },
        PropertyCategory.TERRENO: {
            "titles": [
                "Terreno {area}m² - {neighborhood}",
                "Lote em condomínio - {neighborhood}",
                "Área para incorporação - {neighborhood}",
            ],
            "areas": [(200, 500), (500, 1000), (1000, 5000)],
            "values": [(80000, 200000), (150000, 500000), (300000, 1500000)],
        },
        PropertyCategory.ESTACIONAMENTO: {
            "titles": [
                "Vaga de garagem - {neighborhood}",
                "Box de estacionamento - {neighborhood}",
            ],
            "areas": [(12, 20), (15, 30)],
            "values": [(30000, 80000), (50000, 150000)],
        },
    }
    
    auction_types = list(AuctionType)
    auctioneer_ids = list(auctioneers.keys())
    
    properties = []
    
    # Generate properties for each location
    for location in locations:
        state = location["state"]
        city = location["city"]
        neighborhoods = location["neighborhoods"]
        
        # Generate 5-15 properties per city
        num_properties = random.randint(5, 15)
        
        for _ in range(num_properties):
            # Random category with weighted distribution
            category = random.choices(
                [PropertyCategory.APARTAMENTO, PropertyCategory.CASA, PropertyCategory.COMERCIAL, 
                 PropertyCategory.TERRENO, PropertyCategory.ESTACIONAMENTO],
                weights=[40, 35, 10, 10, 5]
            )[0]
            
            template = templates[category]
            neighborhood = random.choice(neighborhoods)
            beds = random.randint(1, 4)
            
            # Select area and value ranges
            area_range = random.choice(template["areas"])
            value_range = random.choice(template["values"])
            
            area = random.randint(area_range[0], area_range[1])
            evaluation_value = random.randint(value_range[0], value_range[1])
            
            # Calculate auction values with discounts
            first_auction_value = evaluation_value * random.uniform(0.7, 0.9)
            second_auction_value = first_auction_value * random.uniform(0.5, 0.8)
            discount = round((1 - second_auction_value / evaluation_value) * 100, 1)
            
            # Generate dates
            first_date = datetime.now() + timedelta(days=random.randint(5, 30))
            second_date = first_date + timedelta(days=random.randint(7, 21))
            
            # Generate title
            title_template = random.choice(template["titles"])
            title = title_template.format(
                beds=beds,
                neighborhood=neighborhood,
                area=area
            )
            
            # Generate address
            street_names = ["Rua das Flores", "Av. Brasil", "Rua São Paulo", "Av. Paulista", 
                          "Rua XV de Novembro", "Av. Atlântica", "Rua Augusta", "Av. Rio Branco"]
            address = f"{random.choice(street_names)}, {random.randint(1, 2000)} - {neighborhood}"
            
            # Random auction type
            auction_type = random.choice(auction_types)
            
            # Random auctioneer
            auctioneer_id = random.choice(auctioneer_ids)
            
            # Generate source URL
            auctioneer = auctioneers[auctioneer_id]
            source_url = f"{auctioneer.website}/imovel/{random.randint(10000, 99999)}"
            
            # Random financing options
            accepts_financing = random.choice([True, False, None])
            accepts_fgts = random.choice([True, False, None]) if category in [PropertyCategory.APARTAMENTO, PropertyCategory.CASA] else None
            accepts_installments = random.choice([True, False, None])
            
            property_data = PropertyCreate(
                title=title,
                category=category,
                auction_type=auction_type,
                state=state,
                city=city,
                neighborhood=neighborhood,
                address=address,
                description=f"Excelente {category.value.lower()} localizado em {neighborhood}, {city}/{state}. "
                           f"Área de {area}m². Ótima oportunidade de investimento com desconto de {discount}%.",
                area_total=float(area),
                area_privativa=float(area * 0.85) if category in [PropertyCategory.APARTAMENTO, PropertyCategory.CASA] else None,
                evaluation_value=float(evaluation_value),
                first_auction_value=round(first_auction_value, 2),
                first_auction_date=first_date,
                second_auction_value=round(second_auction_value, 2),
                second_auction_date=second_date,
                discount_percentage=discount,
                image_url=f"https://picsum.photos/seed/{random.randint(1, 1000)}/400/300",
                auctioneer_id=auctioneer_id,
                source_url=source_url,
                accepts_financing=accepts_financing,
                accepts_fgts=accepts_fgts,
                accepts_installments=accepts_installments,
                occupation_status=random.choice(["Desocupado", "Ocupado", "Não informado", None]),
                pending_debts=random.choice(["Sem débitos", "IPTU em aberto", "Condomínio em aberto", "Não informado", None]),
            )
            
            properties.append(property_data)
    
    # Add some duplicate properties to demonstrate deduplication
    num_duplicates = min(20, len(properties) // 5)
    for _ in range(num_duplicates):
        original = random.choice(properties)
        # Create a duplicate with slightly different auctioneer
        duplicate_auctioneer = random.choice([a for a in auctioneer_ids if a != original.auctioneer_id])
        duplicate = PropertyCreate(
            **{**original.model_dump(), "auctioneer_id": duplicate_auctioneer, 
               "source_url": f"{auctioneers[duplicate_auctioneer].website}/imovel/{random.randint(10000, 99999)}"}
        )
        properties.append(duplicate)
    
    return properties


def load_sample_data(db):
    """Load sample data into the database."""
    from app.services.deduplication import DeduplicationService
    
    # Generate sample properties
    properties = generate_sample_properties(db.auctioneers)
    
    # Add properties to database
    for prop_data in properties:
        db.create_property(prop_data)
    
    # Run deduplication
    dedup_service = DeduplicationService()
    dedup_service.mark_duplicates(db.properties)
    
    return len(properties)
