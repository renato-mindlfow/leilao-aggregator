import { Property, formatCurrency, formatDate, formatArea } from '@/lib/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  MapPin, Ruler, TrendingDown, ExternalLink, 
  CreditCard, FileText, AlertCircle 
} from 'lucide-react';

interface PropertyDetailsProps {
  property: Property | null;
  open: boolean;
  onClose: () => void;
}

export function PropertyDetails({ property, open, onClose }: PropertyDetailsProps) {
  if (!property) return null;

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
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">{property.title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="relative">
            <img
              src={property.image_url || 'https://picsum.photos/800/400?grayscale'}
              alt={property.title}
              className="w-full h-64 object-cover rounded-lg"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'https://picsum.photos/800/400?grayscale';
              }}
            />
            <div className="absolute top-3 left-3 flex gap-2">
              <Badge className={`${getCategoryColor(property.category)} text-white`}>
                {property.category}
              </Badge>
              <Badge className={getAuctionTypeColor(property.auction_type)}>
                {property.auction_type}
              </Badge>
            </div>
            {property.discount_percentage && property.discount_percentage > 0 && (
              <div className="absolute top-3 right-3">
                <Badge className="bg-red-600 text-white font-bold text-lg px-3 py-1">
                  -{property.discount_percentage.toFixed(0)}% de desconto
                </Badge>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                  <MapPin className="w-5 h-5" />
                  Localização
                </h3>
                <p className="text-muted-foreground">
                  {property.address && <span className="block">{property.address}</span>}
                  <span>{property.neighborhood && `${property.neighborhood}, `}{property.city} - {property.state}</span>
                </p>
              </div>

              {property.description && (
                <div>
                  <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                    <FileText className="w-5 h-5" />
                    Descrição
                  </h3>
                  <p className="text-muted-foreground">{property.description}</p>
                </div>
              )}

              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                  <Ruler className="w-5 h-5" />
                  Área
                </h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Área Total:</span>
                    <span className="ml-2 font-medium">{formatArea(property.area_total)}</span>
                  </div>
                  {property.area_privativa && (
                    <div>
                      <span className="text-muted-foreground">Área Privativa:</span>
                      <span className="ml-2 font-medium">{formatArea(property.area_privativa)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                  <TrendingDown className="w-5 h-5" />
                  Valores
                </h3>
                <div className="space-y-2 bg-muted p-4 rounded-lg">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Avaliação:</span>
                    <span className="line-through">{formatCurrency(property.evaluation_value)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">1º Leilão:</span>
                    <span className="font-medium">{formatCurrency(property.first_auction_value)}</span>
                  </div>
                  {property.first_auction_date && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Data:</span>
                      <span>{formatDate(property.first_auction_date)}</span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex justify-between text-lg">
                    <span className="font-semibold text-green-600">2º Leilão:</span>
                    <span className="font-bold text-green-600">{formatCurrency(property.second_auction_value)}</span>
                  </div>
                  {property.second_auction_date && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Data:</span>
                      <span className="font-medium">{formatDate(property.second_auction_date)}</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                  <CreditCard className="w-5 h-5" />
                  Formas de Pagamento
                </h3>
                <div className="flex flex-wrap gap-2">
                  {property.accepts_financing !== null && (
                    <Badge variant={property.accepts_financing ? 'default' : 'secondary'}>
                      {property.accepts_financing ? 'Aceita Financiamento' : 'Não aceita Financiamento'}
                    </Badge>
                  )}
                  {property.accepts_fgts !== null && (
                    <Badge variant={property.accepts_fgts ? 'default' : 'secondary'}>
                      {property.accepts_fgts ? 'Aceita FGTS' : 'Não aceita FGTS'}
                    </Badge>
                  )}
                  {property.accepts_installments !== null && (
                    <Badge variant={property.accepts_installments ? 'default' : 'secondary'}>
                      {property.accepts_installments ? 'Aceita Parcelamento' : 'Não aceita Parcelamento'}
                    </Badge>
                  )}
                </div>
              </div>

              {(property.occupation_status || property.pending_debts) && (
                <div>
                  <h3 className="font-semibold text-lg flex items-center gap-2 mb-2">
                    <AlertCircle className="w-5 h-5" />
                    Informações Adicionais
                  </h3>
                  <div className="space-y-1 text-sm">
                    {property.occupation_status && (
                      <div>
                        <span className="text-muted-foreground">Ocupação:</span>
                        <span className="ml-2">{property.occupation_status}</span>
                      </div>
                    )}
                    {property.pending_debts && (
                      <div>
                        <span className="text-muted-foreground">Débitos:</span>
                        <span className="ml-2">{property.pending_debts}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            {property.source_url && (
              <Button
                variant="default"
                className="flex-1"
                onClick={() => window.open(property.source_url, '_blank')}
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Ver no Site do Leiloeiro
              </Button>
            )}
            <Button variant="outline" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
