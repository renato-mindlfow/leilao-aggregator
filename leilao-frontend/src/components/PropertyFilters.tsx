import React, { useState, useEffect, useRef } from 'react';
import { PropertyFilters as Filters, getStates, getCities, getCategories, getAuctionTypes } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Search, Filter, X, ChevronDown } from 'lucide-react';
import { normalizeState, normalizeCity } from '@/utils/normalization';

interface PropertyFiltersProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onSearch: () => void;
}

// Componente de dropdown com seleção múltipla
interface MultiSelectDropdownProps {
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
  placeholder: string;
  normalize?: (value: string) => string;
}

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options,
  selected,
  onToggle,
  placeholder,
  normalize,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Normalizar e ordenar opções
  const normalizedOptions = [...new Set(options.map(opt => normalize ? normalize(opt) : opt))]
    .filter(opt => opt && opt.trim() !== '' && opt !== 'XX' && opt !== 'Não informada')
    .sort();

  const filteredOptions = normalizedOptions.filter(opt =>
    opt.toLowerCase().includes(search.toLowerCase())
  );

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full border rounded-lg px-3 py-2 text-left flex justify-between items-center focus:ring-2 focus:ring-blue-500 focus:outline-none bg-background hover:bg-accent"
      >
        <span className={selected.length ? 'text-foreground' : 'text-muted-foreground'}>
          {selected.length ? `${selected.length} selecionado(s)` : placeholder}
        </span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-popover border rounded-lg shadow-lg max-h-60 overflow-hidden">
          {/* Busca */}
          <div className="p-2 border-b">
            <Input
              type="text"
              placeholder="Buscar..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8"
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          {/* Opções */}
          <div className="max-h-48 overflow-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-muted-foreground text-center">
                Nenhuma opção encontrada
              </div>
            ) : (
              filteredOptions.map(option => (
                <label
                  key={option}
                  className="flex items-center px-3 py-2 hover:bg-accent cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(option)}
                    onChange={() => onToggle(option)}
                    className="mr-2"
                  />
                  <span className="text-sm">{option}</span>
                </label>
              ))
            )}
          </div>

          {/* Botão fechar */}
          <div className="p-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsOpen(false)}
              className="w-full"
            >
              Fechar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export function PropertyFilters({ filters, onFiltersChange, onSearch }: PropertyFiltersProps) {
  const [states, setStates] = useState<string[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [auctionTypes, setAuctionTypes] = useState<string[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);

  // Estados e cidades selecionados (arrays)
  const selectedStates = filters.states || (filters.state ? [filters.state] : []);
  const selectedCities = filters.cities || (filters.city ? [filters.city] : []);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    // Se há estados selecionados, carregar cidades desses estados
    if (selectedStates.length > 0) {
      // Carregar cidades para todos os estados selecionados
      Promise.all(selectedStates.map(state => getCities(state)))
        .then(citiesArrays => {
          const allCities = citiesArrays.flat();
          setCities([...new Set(allCities)]);
        });
    } else {
      getCities().then(setCities);
    }
  }, [selectedStates]);

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

  const handleStateToggle = (state: string) => {
    const normalizedState = normalizeState(state);
    const newStates = selectedStates.includes(normalizedState)
      ? selectedStates.filter(s => s !== normalizedState)
      : [...selectedStates, normalizedState];
    
    const newFilters: Filters = {
      ...filters,
      states: newStates.length > 0 ? newStates : undefined,
      state: undefined, // Limpar filtro antigo
      cities: undefined, // Limpar cidades quando mudar estados
      city: undefined,
    };
    
    onFiltersChange(newFilters);
  };

  const handleCityToggle = (city: string) => {
    const normalizedCity = normalizeCity(city);
    const newCities = selectedCities.includes(normalizedCity)
      ? selectedCities.filter(c => c !== normalizedCity)
      : [...selectedCities, normalizedCity];
    
    const newFilters: Filters = {
      ...filters,
      cities: newCities.length > 0 ? newCities : undefined,
      city: undefined, // Limpar filtro antigo
    };
    
    onFiltersChange(newFilters);
  };

  const handleFilterChange = (key: keyof Filters, value: string | number | undefined) => {
    const newFilters = { ...filters, [key]: value || undefined };
    
    if (key === 'state') {
      newFilters.city = undefined;
      newFilters.neighborhood = undefined;
      newFilters.states = undefined;
    }
    
    onFiltersChange(newFilters);
  };

  const clearFilters = () => {
    onFiltersChange({
      page: 1,
      limit: filters.limit || 21,
    });
  };

  const hasActiveFilters = Object.entries(filters).some(
    ([key, value]) => {
      if (['page', 'limit'].includes(key)) return false;
      if (Array.isArray(value)) return value.length > 0;
      return value !== undefined && value !== '';
    }
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
            <Label htmlFor="state">Estados</Label>
            <MultiSelectDropdown
              options={states}
              selected={selectedStates}
              onToggle={handleStateToggle}
              placeholder="Selecionar estados"
              normalize={normalizeState}
            />
          </div>

          <div>
            <Label htmlFor="city">Cidades</Label>
            <MultiSelectDropdown
              options={cities}
              selected={selectedCities}
              onToggle={handleCityToggle}
              placeholder="Selecionar cidades"
              normalize={normalizeCity}
            />
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
                {categories.filter(s => s && s.trim() !== "").map((category) => (
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
                {auctionTypes.filter(s => s && s.trim() !== "").map((type) => (
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

        {/* Tags de seleção ativa */}
        {(selectedStates.length > 0 || selectedCities.length > 0) && (
          <div className="mt-4 flex flex-wrap gap-2">
            {selectedStates.map(state => (
              <span
                key={state}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
              >
                {state}
                <button
                  onClick={() => handleStateToggle(state)}
                  className="ml-2 text-blue-600 hover:text-blue-800"
                  type="button"
                >
                  ×
                </button>
              </span>
            ))}
            {selectedCities.map(city => (
              <span
                key={city}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800"
              >
                {city}
                <button
                  onClick={() => handleCityToggle(city)}
                  className="ml-2 text-green-600 hover:text-green-800"
                  type="button"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

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
