import { MapPin, Home, ExternalLink } from 'lucide-react';
import { Property, formatCurrency } from '@/lib/api';

interface PropertyCardProps {
  property: Property;
  onViewDetails?: (property: Property) => void;
}

export function PropertyCard({ property, onViewDetails }: PropertyCardProps) {
  const {
    category,
    auction_type,
    state,
    city,
    evaluation_value,
    first_auction_value,
    second_auction_value,
    discount_percentage,
    image_url,
    source_url,
  } = property;

  // Calcular desconto se não existir
  const discount = discount_percentage && discount_percentage > 0 
    ? Math.round(discount_percentage) 
    : null;

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-xl transition-shadow duration-300 flex flex-col">
      
      {/* ===== IMAGEM ===== */}
      <div className="relative h-52 bg-gray-100">
        {image_url ? (
          <img 
            src={image_url} 
            alt={`${category} em ${city}`}
            className="w-full h-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
            <Home className="w-16 h-16 text-gray-300" />
          </div>
        )}
        
        {/* Badge Categoria (topo esquerdo) */}
        <span className="absolute top-3 left-3 bg-emerald-500 text-white px-3 py-1 rounded-md text-sm font-medium shadow">
          {category || 'Imóvel'}
        </span>
        
        {/* Badge Desconto (topo direito) */}
        {discount && (
          <span className="absolute top-3 right-3 bg-red-500 text-white px-3 py-1 rounded-md text-sm font-bold shadow">
            -{discount}%
          </span>
        )}
        
        {/* Badge Tipo de Leilão (inferior esquerdo) */}
        {auction_type && (
          <span className="absolute bottom-3 left-3 bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-medium">
            {auction_type}
          </span>
        )}
      </div>

      {/* ===== CONTEÚDO ===== */}
      <div className="p-4 flex-1 flex flex-col">
        
        {/* Localização */}
        <div className="flex items-center text-gray-700 mb-4">
          <MapPin className="w-4 h-4 mr-1.5 text-gray-400 flex-shrink-0" />
          <span className="font-medium">{city}, {state}</span>
        </div>

        {/* Valores */}
        <div className="space-y-2 text-sm flex-1">
          
          {/* Avaliação */}
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Valor de avaliação:</span>
            {evaluation_value ? (
              <span className="text-gray-400 line-through">{formatCurrency(evaluation_value)}</span>
            ) : (
              <span className="text-gray-300">-</span>
            )}
          </div>

          {/* 1º Leilão */}
          <div className="flex justify-between items-center">
            <span className="text-gray-600">1º Leilão:</span>
            {first_auction_value ? (
              <span className="text-gray-700 font-medium">{formatCurrency(first_auction_value)}</span>
            ) : (
              <span className="text-gray-400 text-xs">Informação indisponível</span>
            )}
          </div>

          {/* 2º Leilão */}
          <div className="flex justify-between items-center">
            <span className="text-emerald-600 font-medium">2º Leilão:</span>
            {second_auction_value ? (
              <span className="text-emerald-600 font-bold text-base">{formatCurrency(second_auction_value)}</span>
            ) : (
              <span className="text-gray-400 text-xs">Informação indisponível</span>
            )}
          </div>
        </div>
      </div>

      {/* ===== BOTÕES ===== */}
      <div className="border-t border-gray-100 grid grid-cols-2">
        <button 
          className="py-3 text-gray-600 font-medium text-sm hover:bg-gray-50 transition flex items-center justify-center gap-1.5 border-r border-gray-100"
          onClick={() => onViewDetails?.(property)}
        >
          <Home className="w-4 h-4" />
          Detalhes
        </button>
        <a
          href={source_url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="py-3 text-emerald-600 font-medium text-sm hover:bg-emerald-50 transition flex items-center justify-center gap-1.5"
        >
          <ExternalLink className="w-4 h-4" />
          Ver Leilão
        </a>
      </div>
    </div>
  );
}

export default PropertyCard;
