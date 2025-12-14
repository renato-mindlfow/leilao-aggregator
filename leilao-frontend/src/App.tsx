import { useState, useEffect, useCallback } from 'react';
import { 
  getProperties, 
  getStats, 
  getProperty,
  Property, 
  Stats, 
  PropertyFilters as Filters 
} from '@/lib/api';
import { PropertyCard } from '@/components/PropertyCard';
import { PropertyFilters } from '@/components/PropertyFilters';
import { PropertyDetails } from '@/components/PropertyDetails';
import { PropertyPagination } from '@/components/PropertyPagination';
import { StatsCard, CategoryStats } from '@/components/StatsCard';
import { PropertyMap } from '@/components/PropertyMap';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { RefreshCw, List, Map, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

function App() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [filters, setFilters] = useState<Filters>({
    page: 1,
    limit: 18,
  });
  const [pagination, setPagination] = useState({
    total: 0,
    totalPages: 0,
    hasNext: false,
    hasPrev: false,
  });
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');

  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const data = await getStats();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
      toast.error('Erro ao carregar estatísticas');
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadProperties = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getProperties(filters);
      setProperties(data.items);
      setPagination({
        total: data.total,
        totalPages: data.total_pages,
        hasNext: data.has_next,
        hasPrev: data.has_prev,
      });
    } catch (error) {
      console.error('Error loading properties:', error);
      toast.error('Erro ao carregar imóveis');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  const handleFiltersChange = (newFilters: Filters) => {
    setFilters({ ...newFilters, page: 1 });
  };

  const handleSearch = () => {
    setFilters({ ...filters, page: 1 });
    loadProperties();
  };

  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleViewDetails = (property: Property) => {
    setSelectedProperty(property);
    setDetailsOpen(true);
  };

  const handleRefresh = () => {
    loadStats();
    loadProperties();
    toast.success('Dados atualizados');
  };

  const handleMapPropertySelect = async (propertyId: string) => {
    try {
      const property = await getProperty(propertyId);
      setSelectedProperty(property);
      setDetailsOpen(true);
    } catch (error) {
      console.error('Error loading property details:', error);
      toast.error('Erro ao carregar detalhes do imóvel');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="w-full shadow-sm" style={{ background: 'linear-gradient(135deg, #1a4a7a 0%, #2d6aa0 50%, #1a4a7a 100%)' }}>
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center overflow-hidden" style={{ height: '60px' }}>
              <img 
                src="/leilohub-logo.png" 
                alt="LeiloHub" 
                className="object-contain"
                style={{ height: '160px', width: 'auto' }}
              />
            </div>
            <Button 
              variant="outline" 
              size="default" 
              onClick={handleRefresh}
              className="bg-white/10 border-white/30 text-white hover:bg-white/20 hover:text-white font-medium"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Atualizar
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <StatsCard stats={stats} loading={statsLoading} />
        
        <CategoryStats stats={stats} />

        <PropertyFilters
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onSearch={handleSearch}
        />

        <div className="flex items-center justify-between mb-4">
          <p className="text-muted-foreground">
            {pagination.total.toLocaleString('pt-BR')} imóveis encontrados
          </p>
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="w-4 h-4 mr-2" />
              Lista
            </Button>
            <Button
              variant={viewMode === 'map' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('map')}
            >
              <Map className="w-4 h-4 mr-2" />
              Mapa
            </Button>
          </div>
        </div>

        {viewMode === 'map' ? (
          <PropertyMap
            onPropertySelect={handleMapPropertySelect}
            filters={{
              state: filters.state,
              city: filters.city,
              category: filters.category,
            }}
          />
        ) : loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="bg-muted h-48 rounded-t-lg" />
                <div className="p-4 space-y-3">
                  <div className="h-6 bg-muted rounded w-3/4" />
                  <div className="h-4 bg-muted rounded w-1/2" />
                  <div className="h-4 bg-muted rounded w-full" />
                  <div className="h-10 bg-muted rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : properties.length === 0 ? (
          <div className="text-center py-12">
            <Home className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Nenhum imóvel encontrado</h2>
            <p className="text-muted-foreground">
              Tente ajustar os filtros de busca para encontrar mais resultados.
            </p>
          </div>
        ): (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {properties.map((property) => (
                <PropertyCard
                  key={property.id}
                  property={property}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>

            <PropertyPagination
              currentPage={filters.page || 1}
              totalPages={pagination.totalPages}
              total={pagination.total}
              limit={filters.limit || 18}
              onPageChange={handlePageChange}
            />
          </>
        )}
      </main>

      <footer className="border-t mt-12 bg-[#1e3a5f]">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <img src="/leilohub-logo.png" alt="LeiloHub" className="h-8 object-contain" />
              <p className="text-sm text-white">
                Agregador de Imóveis de Leilão
              </p>
            </div>
            <p className="text-sm text-white/80">
              Dados de {stats?.total_auctioneers || 0} leiloeiros
            </p>
          </div>
        </div>
      </footer>

      <PropertyDetails
        property={selectedProperty}
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
      />

      <Toaster position="top-right" />
    </div>
  );
}

export default App
