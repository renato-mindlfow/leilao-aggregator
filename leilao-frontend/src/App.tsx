import { useState, useEffect, useCallback } from 'react';
import {
  getProperties,
  getStats,
  getProperty,
  getModalityStats,
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
import { PropertySort, SortOption } from '@/components/PropertySort';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { RefreshCw, List, Map, Home, User, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginModal } from './components/auth/LoginModal';
import { PricingModal } from './components/auth/PricingModal';
import { TrialBanner } from './components/auth/TrialBanner';
import { AdminPanel } from './components/admin/AdminPanel';

function AppContent() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [modalityData, setModalityData] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [modalityLoading, setModalityLoading] = useState(true);
  const [sortOption, setSortOption] = useState<SortOption>('recent');
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
  const [showAdminPanel, setShowAdminPanel] = useState(false);

  const { 
    user, 
    canViewProperty, 
    setShowLoginModal, 
    setShowPricingModal, 
    incrementView,
    isAdmin,
    signOut 
  } = useAuth();

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

  const loadModalityStats = useCallback(async () => {
    try {
      setModalityLoading(true);
      const data = await getModalityStats();
      setModalityData(data);
    } catch (error) {
      console.error('Error loading modality stats:', error);
    } finally {
      setModalityLoading(false);
    }
  }, []);

  const loadProperties = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getProperties({ ...filters, sort: sortOption });
      setProperties(data?.items || []);
      setPagination({
        total: data?.total || 0,
        totalPages: data?.total_pages || 0,
        hasNext: data?.has_next || false,
        hasPrev: data?.has_prev || false,
      });
    } catch (error) {
      console.error('Error loading properties:', error);
      toast.error('Erro ao carregar imóveis');
      setProperties([]);
    } finally {
      setLoading(false);
    }
  }, [filters, sortOption]);

  useEffect(() => {
    loadStats();
    loadModalityStats();
  }, [loadStats, loadModalityStats]);

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

  const handleSortChange = (sort: SortOption) => {
    setSortOption(sort);
    setFilters({ ...filters, page: 1 });
  };

  const handleViewDetails = async (property: Property) => {
    // Se não está logado, mostrar modal de login
    if (!user) {
      setShowLoginModal(true);
      return;
    }

    // Se não pode ver (trial expirado), mostrar modal de preços
    if (!canViewProperty()) {
      setShowPricingModal(true);
      return;
    }

    // Incrementar view e abrir detalhes
    await incrementView(property.id);
    setSelectedProperty(property);
    setDetailsOpen(true);
  };

  const handleRefresh = () => {
    loadStats();
    loadProperties();
    loadModalityStats();
    toast.success('Dados atualizados');
  };

  const handleMapPropertySelect = async (propertyId: string) => {
    try {
      // Verificar acesso antes de carregar
      if (!user) {
        setShowLoginModal(true);
        return;
      }
      
      if (!canViewProperty()) {
        setShowPricingModal(true);
        return;
      }

      const property = await getProperty(propertyId);
      await incrementView(propertyId);
      setSelectedProperty(property);
      setDetailsOpen(true);
    } catch (error) {
      console.error('Error loading property details:', error);
      toast.error('Erro ao carregar detalhes do imóvel');
    }
  };

  // Se é admin e quer ver o painel
  if (showAdminPanel && isAdmin()) {
    return (
      <>
        <div className="min-h-screen bg-gray-100">
          <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
            <h1 className="text-xl font-bold">Painel Admin</h1>
            <Button onClick={() => setShowAdminPanel(false)} variant="outline">
              Voltar ao Site
            </Button>
          </div>
          <AdminPanel />
        </div>
        <LoginModal />
        <PricingModal />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <TrialBanner />
      
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
            <div className="flex items-center gap-2">
              {user ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled
                    className="bg-white/10 border-white/30 text-white hover:bg-white/20 hover:text-white font-medium cursor-default"
                  >
                    <User className="w-4 h-4 mr-2" />
                    {user.email}
                  </Button>
                  {isAdmin() && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAdminPanel(true)}
                      className="bg-purple-600 border-purple-600 text-white hover:bg-purple-700 hover:border-purple-700 font-medium"
                    >
                      Admin
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={signOut}
                    className="bg-white/10 border-white/30 text-white hover:bg-white/20 hover:text-white font-medium"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sair
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="default"
                  onClick={() => setShowLoginModal(true)}
                  className="bg-white/10 border-white/30 text-white hover:bg-white/20 hover:text-white font-medium"
                >
                  <User className="w-4 h-4 mr-2" />
                  Entrar
                </Button>
              )}
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
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* Cards de estatísticas */}
        <StatsCard stats={stats} loading={statsLoading} />

        {/* Categorias (esquerda) + Gráfico Modalidades (direita) */}
        <CategoryStats 
          stats={stats} 
          modalityData={modalityData}
          modalityLoading={modalityLoading}
        />

        {/* Filtros */}
        <PropertyFilters
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onSearch={handleSearch}
        />

        {/* Contador, ordenação e botões de visualização */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <p className="text-muted-foreground">
            {pagination.total.toLocaleString('pt-BR')} imóveis encontrados
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <PropertySort value={sortOption} onChange={handleSortChange} />
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
        </div>

        {/* Lista de imóveis ou Mapa */}
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
        ) : (
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

      <LoginModal />
      <PricingModal />

      <Toaster position="top-right" />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
