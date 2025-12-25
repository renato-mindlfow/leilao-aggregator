import { useState, useEffect } from 'react';
import { PropertyFilters as Filters, getStates, getCities, getCategories, getAuctionTypes } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Search, Filter, X } from 'lucide-react';

interface PropertyFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onSearch: () => void;
}

export function PropertyFilters({ filters, onFiltersChange, onSearch }: PropertyFiltersProps) {
  const [states, setStates] = useState<string[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [auctionTypes, setAuctionTypes] = useState<string[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    if (filters.state) {
      getCities(filters.state).then(setCities);
    } else {
      getCities().then(setCities);
    }
  }, [filters.state]);

  const loadFilterOptions = async () => {
    try {
      const [statesData, citiesData, categoriesData, auctionTypesData] = await Promise.all([
        getStates(),
        getCities(),
        getCategories(),
        getAuctionTypes(),
      ]);
      setStates(statesData);
      setCities(citiesData);
      setCategories(categoriesData);
      setAuctionTypes(auctionTypesData);
    } catch (error) {
      console.error('Error loading filter options:', error);
    }
  };

  const handleFilterChange = (key: keyof Filters, value: string | number | undefined) => {
    const newFilters = { ...filters, [key]: value || undefined };
    
    if (key === 'state') {
      newFilters.city = undefined;
      newFilters.neighborhood = undefined;
    }
    
    onFiltersChange(newFilters);
  };

  const clearFilters = () => {
    onFiltersChange({
      page: 1,
      limit: 18,
    });
  };

  const hasActiveFilters = Object.entries(filters).some(
    ([key, value]) => !['page', 'limit'].includes(key) && value !== undefined && value !== ''
  );

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filtros de Busca
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? 'Menos filtros' : 'Mais filtros'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-2">
            <Label htmlFor="search">Buscar</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                id="search"
                placeholder="Buscar por título, endereço, cidade..."
                value={filters.search || ''}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="pl-10"
                onKeyDown={(e) => e.key === 'Enter' && onSearch()}
              />
            </div>
          </div>

          <div>
            <Label htmlFor="state">Estado</Label>
            <Select
              value={filters.state || 'all'}
              onValueChange={(value) => handleFilterChange('state', value === 'all' ? undefined : value)}
            >
              <SelectTrigger id="state">
                <SelectValue placeholder="Todos os estados" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os estados</SelectItem>
                {states.map((state) => (
                  <SelectItem key={state} value={state}>
                    {state}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="city">Cidade</Label>
            <Select
              value={filters.city || 'all'}
              onValueChange={(value) => handleFilterChange('city', value === 'all' ? undefined : value)}
            >
              <SelectTrigger id="city">
                <SelectValue placeholder="Todas as cidades" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as cidades</SelectItem>
                {cities.map((city) => (
                  <SelectItem key={city} value={city}>
                    {city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="category">Categoria</Label>
            <Select
              value={filters.category || 'all'}
              onValueChange={(value) => handleFilterChange('category', value === 'all' ? undefined : value)}
            >
              <SelectTrigger id="category">
                <SelectValue placeholder="Todas as categorias" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as categorias</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="auction_type">Tipo de Leilão</Label>
            <Select
              value={filters.auction_type || 'all'}
              onValueChange={(value) => handleFilterChange('auction_type', value === 'all' ? undefined : value)}
            >
              <SelectTrigger id="auction_type">
                <SelectValue placeholder="Todos os tipos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os tipos</SelectItem>
                {auctionTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {isExpanded && (
            <>
              <div>
                <Label htmlFor="min_value">Valor Mínimo (R$)</Label>
                <Input
                  id="min_value"
                  type="number"
                  placeholder="0"
                  value={filters.min_value || ''}
                  onChange={(e) => handleFilterChange('min_value', e.target.value ? Number(e.target.value) : undefined)}
                />
              </div>

              <div>
                <Label htmlFor="max_value">Valor Máximo (R$)</Label>
                <Input
                  id="max_value"
                  type="number"
                  placeholder="Sem limite"
                  value={filters.max_value || ''}
                  onChange={(e) => handleFilterChange('max_value', e.target.value ? Number(e.target.value) : undefined)}
                />
              </div>

              <div>
                <Label htmlFor="min_discount">Desconto Mínimo (%)</Label>
                <Input
                  id="min_discount"
                  type="number"
                  placeholder="0"
                  min="0"
                  max="100"
                  value={filters.min_discount || ''}
                  onChange={(e) => handleFilterChange('min_discount', e.target.value ? Number(e.target.value) : undefined)}
                />
              </div>
            </>
          )}
        </div>

        <div className="flex gap-2 mt-4">
          <Button onClick={onSearch} className="flex-1 md:flex-none">
            <Search className="w-4 h-4 mr-2" />
            Buscar
          </Button>
          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              <X className="w-4 h-4 mr-2" />
              Limpar Filtros
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
