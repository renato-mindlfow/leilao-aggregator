/**
 * Adapter que converte dados da API Caixa para o formato da API atual
 * Permite integração sem modificar componentes existentes
 */

import { 
  CaixaImovel, 
  CaixaListResponse, 
  CaixaStats,
  CaixaEstadosResponse,
  CaixaCidadesResponse
} from './caixaApiService';

import { Property, PropertiesResponse, Stats } from './api';

/**
 * Converte imóvel da API Caixa para formato Property
 */
export function adaptCaixaImovelToProperty(caixaImovel: CaixaImovel): Property {
  return {
    // IDs e identificação
    id: caixaImovel.numero_imovel,
    title: caixaImovel.endereco,
    
    // Localização
    state: caixaImovel.estado,
    city: caixaImovel.cidade,
    neighborhood: caixaImovel.bairro,
    address: caixaImovel.endereco,
    
    // Categoria e tipo
    category: caixaImovel.categoria,
    auction_type: caixaImovel.tipo_leilao,
    
    // Valores (converter de CENTAVOS para REAIS)
    evaluation_value: caixaImovel.valor_avaliacao 
      ? caixaImovel.valor_avaliacao / 100 
      : null,
    
    first_auction_value: caixaImovel.valor_primeira_praca 
      ? caixaImovel.valor_primeira_praca / 100 
      : null,
    
    // Segundo leilão (Caixa não tem, usar valor_primeira_praca)
    second_auction_value: caixaImovel.valor_primeira_praca 
      ? caixaImovel.valor_primeira_praca / 100 
      : null,
    
    // Datas (Caixa não tem datas de leilão)
    first_auction_date: null,
    second_auction_date: null,
    
    // Desconto
    discount_percentage: caixaImovel.desconto_percentual,
    
    // Áreas
    area_total: caixaImovel.area_total,
    area_privativa: caixaImovel.area_construida,
    
    // URLs e imagens
    source_url: caixaImovel.url,
    image_url: null, // Caixa não fornece imagens
    
    // Leiloeiro
    auctioneer_id: 'caixa',
    
    // Descrição
    description: null,
    
    // Opções de pagamento (Caixa não fornece, assumir padrões)
    accepts_financing: true, // Caixa geralmente aceita
    accepts_fgts: true, // Caixa geralmente aceita
    accepts_installments: false,
    
    // Status
    occupation_status: null,
    pending_debts: null,
    
    // Duplicatas
    is_duplicate: false,
    original_id: null,
  };
}

/**
 * Converte lista de imóveis da API Caixa para PropertiesResponse
 */
export function adaptCaixaListToPropertiesResponse(
  caixaResponse: CaixaListResponse
): PropertiesResponse {
  return {
    items: caixaResponse.items.map(adaptCaixaImovelToProperty),
    total: caixaResponse.total,
    page: caixaResponse.page,
    total_pages: caixaResponse.total_pages,
    limit: caixaResponse.page_size,
    has_next: caixaResponse.page < caixaResponse.total_pages,
    has_prev: caixaResponse.page > 1,
  };
}

/**
 * Converte estatísticas da API Caixa para Stats
 */
export function adaptCaixaStatsToStats(caixaStats: CaixaStats): Stats {
  return {
    total_properties: caixaStats.total_imoveis,
    unique_properties: caixaStats.total_imoveis, // Caixa não tem duplicatas
    duplicate_properties: 0,
    total_auctioneers: 1, // Apenas Caixa
    active_auctioneers: 1,
    category_counts: caixaStats.por_categoria,
    state_counts: caixaStats.por_estado,
  };
}

/**
 * Converte estados da API Caixa para array de strings
 */
export function adaptCaixaEstadosToStrings(
  caixaEstados: CaixaEstadosResponse
): string[] {
  return caixaEstados.estados.map(e => e.sigla);
}

/**
 * Converte cidades da API Caixa para array de strings
 */
export function adaptCaixaCidadesToStrings(
  caixaCidades: CaixaCidadesResponse
): string[] {
  return caixaCidades.cidades.map(c => c.nome);
}

/**
 * Converte filtros do formato atual para formato API Caixa
 */
export function adaptFiltersToKaixaParams(filters: {
  state?: string;
  city?: string;
  category?: string;
  auction_type?: string;
  min_value?: number;
  max_value?: number;
  page?: number;
  limit?: number;
}) {
  return {
    estado: filters.state,
    cidade: filters.city,
    categoria: filters.category,
    // tipo_leilao não tem equivalente direto, ignorar auction_type
    valor_min: filters.min_value ? filters.min_value * 100 : undefined, // REAIS → CENTAVOS
    valor_max: filters.max_value ? filters.max_value * 100 : undefined, // REAIS → CENTAVOS
    page: filters.page,
    page_size: filters.limit,
  };
}
