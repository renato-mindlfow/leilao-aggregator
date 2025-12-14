import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '@/lib/api';

// Fix for default marker icons in Leaflet with Vite
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapProperty {
  id: string;
  title: string;
  category: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  second_auction_value: number;
  discount_percentage: number;
  image_url: string;
}

interface PropertyMapProps {
  onPropertySelect?: (propertyId: string) => void;
  filters?: {
    state?: string;
    city?: string;
    category?: string;
  };
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
}

function MapBoundsUpdater({ properties }: { properties: MapProperty[] }) {
  const map = useMap();

  useEffect(() => {
    if (properties.length > 0) {
      const bounds = L.latLngBounds(
        properties.map((p) => [p.latitude, p.longitude] as [number, number])
      );
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [properties, map]);

  return null;
}

export function PropertyMap({ onPropertySelect, filters }: PropertyMapProps) {
  const [properties, setProperties] = useState<MapProperty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMapProperties = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (filters?.state) params.append('state', filters.state);
        if (filters?.city) params.append('city', filters.city);
        if (filters?.category) params.append('category', filters.category);
        params.append('limit', '500');

        const response = await api.get<{ properties: MapProperty[]; total: number }>(`/api/map/properties?${params.toString()}`);
        setProperties(response.data.properties);
      } catch (err) {
        console.error('Error fetching map properties:', err);
        setError('Erro ao carregar propriedades do mapa');
      } finally {
        setLoading(false);
      }
    };

    fetchMapProperties();
  }, [filters?.state, filters?.city, filters?.category]);

  if (loading) {
    return (
      <div className="w-full h-96 bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="text-gray-500">Carregando mapa...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-96 bg-gray-100 rounded-lg flex items-center justify-center">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  // Default center (Brazil)
  const defaultCenter: [number, number] = [-14.235, -51.9253];
  const defaultZoom = 4;

  // Calculate center from properties if available
  const center: [number, number] =
    properties.length > 0
      ? [
          properties.reduce((sum, p) => sum + p.latitude, 0) / properties.length,
          properties.reduce((sum, p) => sum + p.longitude, 0) / properties.length,
        ]
      : defaultCenter;

  return (
    <div className="w-full h-96 rounded-lg overflow-hidden border border-gray-200 shadow-sm">
      <MapContainer
        center={center}
        zoom={properties.length > 0 ? 5 : defaultZoom}
        className="w-full h-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {properties.length > 0 && <MapBoundsUpdater properties={properties} />}
        {properties.map((property) => (
          <Marker
            key={property.id}
            position={[property.latitude, property.longitude]}
            eventHandlers={{
              click: () => {
                if (onPropertySelect) {
                  onPropertySelect(property.id);
                }
              },
            }}
          >
            <Popup>
              <div className="min-w-48">
                {property.image_url && (
                  <img
                    src={property.image_url}
                    alt={property.title}
                    className="w-full h-24 object-cover rounded mb-2"
                  />
                )}
                <h3 className="font-semibold text-sm mb-1">{property.title}</h3>
                <p className="text-xs text-gray-600 mb-1">
                  {property.city}, {property.state}
                </p>
                <p className="text-sm font-bold text-green-600">
                  {formatCurrency(property.second_auction_value)}
                </p>
                {property.discount_percentage && (
                  <span className="inline-block bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded mt-1">
                    -{property.discount_percentage.toFixed(0)}%
                  </span>
                )}
                {onPropertySelect && (
                  <button
                    onClick={() => onPropertySelect(property.id)}
                    className="mt-2 w-full bg-blue-600 text-white text-xs py-1 px-2 rounded hover:bg-blue-700"
                  >
                    Ver detalhes
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <div className="bg-gray-50 px-3 py-2 text-xs text-gray-600 border-t">
        {properties.length} imóveis no mapa
      </div>
    </div>
  );
}
