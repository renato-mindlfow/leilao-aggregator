import { Property, formatCurrency, formatDate, formatArea } from '@/lib/api';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MapPin, Calendar, Ruler, ExternalLink, Home } from 'lucide-react';

interface PropertyCardProps {
  property: Property;
  onViewDetails?: (property: Property) => void;
}

export function PropertyCard({ property, onViewDetails }: PropertyCardProps) {
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      'Apartamento': 'bg-blue-500',
      'Casa': 'bg-green-500',
      'Comercial': 'bg-purple-500',
      'Terreno': 'bg-amber-500',
      'Estacionamento': 'bg-gray-500',
      'Área': 'bg-teal-500',
      'Outros': 'bg-slate-500',
    };
    return colors[category] || 'bg-slate-500';
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

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow duration-300 flex flex-col h-full">
      <div className="relative">
        <img
          src={property.image_url || 'https://picsum.photos/400/300?grayscale'}
          alt={property.title}
          className="w-full h-48 object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).src = 'https://picsum.photos/400/300?grayscale';
          }}
        />
        <div className="absolute top-2 left-2 flex gap-1">
          <Badge className={`${getCategoryColor(property.category)} text-white`}>
            {property.category}
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
