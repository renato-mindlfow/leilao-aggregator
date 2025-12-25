import { Property, formatCurrency, formatDate, formatArea } from '@/lib/api';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MapPin, Calendar, Ruler, ExternalLink, Home } from 'lucide-react';

interface PropertyCardProps {
  property: Property;
  onViewDetails?: (property: Property) => void;
}

// Placeholders fixos por categoria (imagens do Unsplash em grayscale)
const CATEGORY_PLACEHOLDERS: Record<string, string> = {
  'Apartamento': 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=400&h=300&fit=crop&sat=-100',
  'Casa': 'https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=400&h=300&fit=crop&sat=-100',
  'Terreno': 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=400&h=300&fit=crop&sat=-100',
  'Comercial': 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=400&h=300&fit=crop&sat=-100',
  'Rural': 'https://images.unsplash.com/photo-1500076656116-558758c991c1?w=400&h=300&fit=crop&sat=-100',
  'Garagem': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop&sat=-100',
  'Área': 'https://images.unsplash.com/photo-1628624747186-a941c476b7ef?w=400&h=300&fit=crop&sat=-100',
  'Galpão': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=400&h=300&fit=crop&sat=-100',
  'Prédio': 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=400&h=300&fit=crop&sat=-100',
  'Outro': 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=300&fit=crop&sat=-100',
  'Outros': 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=300&fit=crop&sat=-100',
};

// Placeholder padrão caso categoria não encontrada
const DEFAULT_PLACEHOLDER = 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=300&fit=crop&sat=-100';

const normalizeCategory = (category: string): string => {
  const mappings: Record<string, string> = {
    'Estacionamento': 'Garagem',
    'Galpão': 'Comercial',
    'Prédio': 'Comercial',
    'GALPAO': 'Comercial',
    'PREDIO': 'Comercial',
    'APARTAMENTO': 'Apartamento',
    'CASA': 'Casa',
    'TERRENO': 'Terreno',
    'COMERCIAL': 'Comercial',
    'RURAL': 'Rural',
    'ÁREA': 'Área',
    'AREA': 'Área',
    'OUTRO': 'Outro',
    'OUTROS': 'Outros',
  };
  return mappings[category] || category;
};

// Função para obter imagem (real ou placeholder)
const getPropertyImage = (property: Property): string => {
  // Se tem imagem válida, usa ela
  if (property.image_url && property.image_url.trim() !== '') {
    return property.image_url;
  }
  
  // Senão, usa placeholder baseado na categoria
  const normalizedCategory = normalizeCategory(property.category);
  return CATEGORY_PLACEHOLDERS[normalizedCategory] || DEFAULT_PLACEHOLDER;
};

export function PropertyCard({ property, onViewDetails }: PropertyCardProps) {
  const getCategoryColor = (category: string) => {
    const normalizedCategory = normalizeCategory(category);
    const colors: Record<string, string> = {
      'Apartamento': 'bg-blue-600',
      'Casa': 'bg-green-600',
      'Terreno': 'bg-yellow-600',
      'Comercial': 'bg-purple-600',
      'Garagem': 'bg-slate-600',
      'Rural': 'bg-emerald-600',
      'Área': 'bg-red-600',
      'Outro': 'bg-orange-600',
      'Outros': 'bg-orange-600',
    };
    return colors[normalizedCategory] || 'bg-slate-500';
  };

  const getAuctionTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'Judicial': 'bg-red-100 text-red-800',
      'Extrajudicial': 'bg-orange-100 text-orange-800',
      'Venda Direta': 'bg-green-100 text-green-800',
      'Leilão SFI': 'bg-blue-100 text-blue-800',
      'Outros': 'bg-gray-100 text-gray-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const displayCategory = normalizeCategory(property.category);
  const imageUrl = getPropertyImage(property);
  const isPlaceholder = !property.image_url || property.image_url.trim() === '';

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow duration-300 flex flex-col h-full">
      <div className="relative">
        <img
          src={imageUrl}
          alt={property.title}
          className={`w-full h-48 object-cover ${isPlaceholder ? 'grayscale' : ''}`}
          onError={(e) => {
            // Fallback para placeholder da categoria se imagem falhar
            const target = e.target as HTMLImageElement;
            const fallback = CATEGORY_PLACEHOLDERS[displayCategory] || DEFAULT_PLACEHOLDER;
            if (target.src !== fallback) {
              target.src = fallback;
              target.classList.add('grayscale');
            }
          }}
        />
        {/* Overlay indicando que é placeholder */}
        {isPlaceholder && (
          <div className="absolute bottom-2 right-2">
            <Badge variant="secondary" className="bg-black/50 text-white text-xs">
              Imagem ilustrativa
            </Badge>
          </div>
        )}
        <div className="absolute top-2 left-2 flex gap-1">
          <Badge className={`${getCategoryColor(property.category)} text-white`}>
            {displayCategory}
          </Badge>
        </div>
        {property.discount_percentage && property.discount_percentage > 0 && (
          <div className="absolute top-2 right-2">
            <Badge className="bg-red-600 text-white font-bold">
              -{property.discount_percentage.toFixed(0)}%
            </Badge>
          </div>
        )}
        <div className="absolute bottom-2 left-2">
          <Badge className={getAuctionTypeColor(property.auction_type)}>
            {property.auction_type}
          </Badge>
        </div>
      </div>

      <CardHeader className="pb-2">
        <h3 className="font-semibold text-lg line-clamp-2 min-h-14">
          {property.title}
        </h3>
        <div className="flex items-center text-sm text-muted-foreground">
          <MapPin className="w-4 h-4 mr-1" />
          {property.city}, {property.state}
        </div>
      </CardHeader>

      <CardContent className="flex-grow pb-2">
        <div className="space-y-2 text-sm">
          {property.area_total && (
            <div className="flex items-center text-muted-foreground">
              <Ruler className="w-4 h-4 mr-2" />
              {formatArea(property.area_total)}
            </div>
          )}

          <div className="border-t pt-2 mt-2">
            {property.evaluation_value && (
              <div className="flex justify-between text-muted-foreground">
                <span>Avaliação:</span>
                <span className="line-through">{formatCurrency(property.evaluation_value)}</span>
              </div>
            )}

            {property.second_auction_value && (
              <div className="flex justify-between font-semibold text-green-600 text-lg mt-1">
                <span>2º Leilão:</span>
                <span>{formatCurrency(property.second_auction_value)}</span>
              </div>
            )}

            {property.second_auction_date && (
              <div className="flex items-center text-xs text-muted-foreground mt-1">
                <Calendar className="w-3 h-3 mr-1" />
                {formatDate(property.second_auction_date)}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-1 mt-2">
            {property.accepts_financing && (
              <Badge variant="outline" className="text-xs">Financiamento</Badge>
            )}
            {property.accepts_fgts && (
              <Badge variant="outline" className="text-xs">FGTS</Badge>
            )}
            {property.accepts_installments && (
              <Badge variant="outline" className="text-xs">Parcelamento</Badge>
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-2 gap-2">
        <Button
          variant="outline"
          className="flex-1"
          onClick={() => onViewDetails?.(property)}
        >
          <Home className="w-4 h-4 mr-1" />
          Detalhes
        </Button>
        {property.source_url && (
          <Button
            variant="default"
            className="flex-1"
            onClick={() => window.open(property.source_url, '_blank')}
          >
            <ExternalLink className="w-4 h-4 mr-1" />
            Ver Leilão
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
