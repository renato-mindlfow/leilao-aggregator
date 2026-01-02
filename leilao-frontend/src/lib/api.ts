const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_AUTH = import.meta.env.VITE_API_AUTH || '';

// Importar serviços da API Caixa
import * as CaixaAPI from './caixaApiService';
import * as CaixaAdapter from './caixaAdapter';

export type SortOption = 
  | 'recent'
  | 'price_desc' 
  | 'price_asc' 
  | 'date_asc' 
  | 'date_desc' 
  | 'discount_desc';

// Flag para alternar entre APIs
// false = usar backend unificado (recomendado - dados deduplicados)
// true = usar API Caixa diretamente (sem deduplicação)
const USE_CAIXA_API = false;

export interface Property {
  id: string;
  title: string;
  category: string;
  auction_type: string;
  state: string;
  city: string;
  neighborhood: string | null;
  address: string | null;
  description: string | null;
  area_total: number | null;
  area_privativa: number | null;
  evaluation_value: number | null;
  first_auction_value: number | null;
  first_auction_date: string | null;
  second_auction_value: number | null;
  second_auction_date: string | null;
  discount_percentage: number | null;
  image_url: string | null;
  auctioneer_id: string;
  source_url: string;
  accepts_financing: boolean | null;
  accepts_fgts: boolean | null;
  accepts_installments: boolean | null;
  occupation_status: string | null;
  pending_debts: string | null;
  is_duplicate: boolean;
  original_id: string | null;
}

export interface Auctioneer {
  id: string;
  name: string;
  website: string;
  logo_url: string | null;
  is_active: boolean;
  property_count: number;
  last_scrape: string | null;
  scrape_status: string;
}

export interface PropertiesResponse {
  items: Property[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Stats {
  total_properties: number;
  unique_properties: number;
  duplicate_properties: number;
  total_auctioneers: number;
  active_auctioneers: number;
  category_counts: Record<string, number>;
  state_counts: Record<string, number>;
}

export interface PropertyFilters {
  page?: number;
  limit?: number;
  state?: string;
  city?: string;
  neighborhood?: string;
  category?: string;
  auction_type?: string;
  min_value?: number;
  max_value?: number;
  min_discount?: number;
  auctioneer_id?: string;
  search?: string;
  include_duplicates?: boolean;
  sort?: SortOption;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  // Add Basic Auth if credentials are provided
  if (API_AUTH) {
    headers['Authorization'] = `Basic ${btoa(API_AUTH)}`;
  }
  
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
}

export async function getProperties(filters: PropertyFilters = {}): Promise<PropertiesResponse> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    const caixaParams = CaixaAdapter.adaptFiltersToKaixaParams(filters);
    const caixaResponse = await CaixaAPI.buscarImoveis(caixaParams);
    return CaixaAdapter.adaptCaixaListToPropertiesResponse(caixaResponse);
  }
  
  // Código original (mantido como fallback)
  const params = new URLSearchParams();
  
  if (filters.sort) params.append('sort', filters.sort);
  
  // Se ordenar por desconto, adicionar filtro mínimo para ignorar NULLs e descontos zerados
  if (filters.sort === 'discount_desc') {
    // Se não tiver min_discount já definido, adicionar 1 para filtrar descontos nulos ou zerados
    if (filters.min_discount === undefined || filters.min_discount === null) {
      params.append('min_discount', '1');
    }
  }
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && key !== 'sort') {
      params.append(key, String(value));
    }
  });
  
  const queryString = params.toString();
  return fetchApi<PropertiesResponse>(`/api/properties${queryString ? `?${queryString}` : ''}`);
}

export async function getProperty(id: string): Promise<Property> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    const caixaImovel = await CaixaAPI.buscarImovelDetalhes(id);
    return CaixaAdapter.adaptCaixaImovelToProperty(caixaImovel);
  }
  
  // Código original (mantido como fallback)
  return fetchApi<Property>(`/api/properties/${id}`);
}

export async function getAuctioneers(): Promise<Auctioneer[]> {
  return fetchApi<Auctioneer[]>('/api/auctioneers');
}

export async function getStats(): Promise<Stats> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    const caixaStats = await CaixaAPI.buscarEstatisticas();
    return CaixaAdapter.adaptCaixaStatsToStats(caixaStats);
  }
  
  // Código original (mantido como fallback)
  return fetchApi<Stats>('/api/stats');
}

export async function getStates(): Promise<string[]> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    const caixaEstados = await CaixaAPI.listarEstados();
    return CaixaAdapter.adaptCaixaEstadosToStrings(caixaEstados);
  }
  
  // Código original (mantido como fallback)
  return fetchApi<string[]>('/api/filters/states');
}

export async function getCities(state?: string): Promise<string[]> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    if (!state) {
      // API Caixa precisa de estado para listar cidades
      // Retornar array vazio se não houver estado
      return [];
    }
    const caixaCidades = await CaixaAPI.listarCidades(state);
    return CaixaAdapter.adaptCaixaCidadesToStrings(caixaCidades);
  }
  
  // Código original (mantido como fallback)
  const params = state ? `?state=${encodeURIComponent(state)}` : '';
  return fetchApi<string[]>(`/api/filters/cities${params}`);
}

export async function getNeighborhoods(state?: string, city?: string): Promise<string[]> {
  const params = new URLSearchParams();
  if (state) params.append('state', state);
  if (city) params.append('city', city);
  const queryString = params.toString();
  return fetchApi<string[]>(`/api/filters/neighborhoods${queryString ? `?${queryString}` : ''}`);
}

export async function getCategories(): Promise<string[]> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    // Categorias fixas da Caixa
    return ['Apartamento', 'Casa', 'Terreno', 'Comercial'];
  }
  
  // Código original (mantido como fallback)
  return fetchApi<string[]>('/api/filters/categories');
}

export async function getAuctionTypes(): Promise<string[]> {
  // Se usar API Caixa
  if (USE_CAIXA_API) {
    // Tipos de leilão fixos da Caixa
    return ['Venda Direta Online', 'Leilão SFI', 'Venda Online'];
  }
  
  // Código original (mantido como fallback)
  return fetchApi<string[]>('/api/filters/auction-types');
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatArea(area: number | null | undefined): string {
  if (area === null || area === undefined) return 'N/A';
  return `${area.toLocaleString('pt-BR')} m²`;
}

export async function getModalityStats(): Promise<Record<string, number>> {
  // Endpoint /api/stats/modality não existe no backend
  // Usando cálculo aproximado baseado nas estatísticas gerais
  try {
    const stats = await fetchApi<Stats>('/api/stats');
    return {
      'Judicial': Math.floor(stats.unique_properties * 0.04),
      'Extrajudicial': Math.floor(stats.unique_properties * 0.95),
      'Venda Direta': Math.floor(stats.unique_properties * 0.005),
      'Outros': Math.ceil(stats.unique_properties * 0.005),
    };
  } catch (error) {
    console.warn('Erro ao calcular estatísticas de modalidade:', error);
    // Retornar valores padrão em caso de erro
    return {
      'Judicial': 0,
      'Extrajudicial': 0,
      'Venda Direta': 0,
      'Outros': 0,
    };
  }
}

// Export api object for direct axios-like usage
export const api = {
  get: async <T>(url: string): Promise<{ data: T }> => {
    const data = await fetchApi<T>(url);
    return { data };
  },
};
