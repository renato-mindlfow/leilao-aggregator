/**
 * Serviço de integração com API Caixa Scraper
 * Base URL: https://caixa-scraper.fly.dev
 * Documentação: https://caixa-scraper.fly.dev/docs
 */

const API_BASE_URL = 'https://caixa-scraper.fly.dev';

// ==================== INTERFACES ====================

export interface CaixaImovel {
  numero_imovel: string;
  leiloeiro_nome: string;
  url: string;
  endereco: string;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  cidade: string;
  estado: string;
  categoria: string;
  modalidade: string;
  tipo_leilao: string;
  valor_primeira_praca: number; // em centavos
  valor_avaliacao: number; // em centavos
  desconto_percentual: number | null;
  area_total: number | null;
  area_construida: number | null;
  area_terreno: number | null;
  hash_unico: string;
  timestamp_scraping: string;
  versao_scraper: string;
  fonte: string;
}

export interface CaixaListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: CaixaImovel[];
}

export interface CaixaEstado {
  sigla: string;
  nome: string;
  total_imoveis: number;
}

export interface CaixaEstadosResponse {
  total: number;
  estados: CaixaEstado[];
}

export interface CaixaCidade {
  nome: string;
  total_imoveis: number;
}

export interface CaixaCidadesResponse {
  total: number;
  estado: string;
  cidades: CaixaCidade[];
}

export interface CaixaStats {
  total_imoveis: number;
  completude: number;
  por_estado: Record<string, number>;
  por_categoria: Record<string, number>;
  por_modalidade: Record<string, number>;
  faixa_precos: Record<string, number>;
  last_update: string;
}

export interface BuscarImoveisParams {
  estado?: string;
  cidade?: string;
  categoria?: string;
  valor_min?: number; // em centavos
  valor_max?: number; // em centavos
  page?: number;
  page_size?: number;
}

// ==================== FUNÇÕES ====================

/**
 * Trata erros de requisição
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Erro HTTP: ${response.status}`);
  }
  return response.json();
}

/**
 * Busca lista de imóveis com filtros
 * 
 * @param filtros - Filtros de busca
 * @returns Lista de imóveis com metadados de paginação
 * 
 * @example
 * const resultado = await buscarImoveis({ 
 *   estado: 'RJ', 
 *   categoria: 'Apartamento',
 *   page: 1,
 *   page_size: 20
 * });
 */
export async function buscarImoveis(
  filtros: BuscarImoveisParams = {}
): Promise<CaixaListResponse> {
  const params = new URLSearchParams();
  
  // Adicionar filtros opcionais
  if (filtros.estado) params.append('estado', filtros.estado);
  if (filtros.cidade) params.append('cidade', filtros.cidade);
  if (filtros.categoria) params.append('categoria', filtros.categoria);
  if (filtros.valor_min) params.append('valor_min', filtros.valor_min.toString());
  if (filtros.valor_max) params.append('valor_max', filtros.valor_max.toString());
  
  // Paginação
  params.append('page', (filtros.page || 1).toString());
  params.append('page_size', (filtros.page_size || 20).toString());
  
  const response = await fetch(`${API_BASE_URL}/imoveis?${params}`);
  return handleResponse<CaixaListResponse>(response);
}

/**
 * Busca detalhes de um imóvel específico
 * 
 * @param numeroImovel - Número do imóvel
 * @returns Dados completos do imóvel
 * 
 * @example
 * const imovel = await buscarImovelDetalhes('1444419970935');
 */
export async function buscarImovelDetalhes(
  numeroImovel: string
): Promise<CaixaImovel> {
  const response = await fetch(`${API_BASE_URL}/imoveis/${numeroImovel}`);
  return handleResponse<CaixaImovel>(response);
}

/**
 * Lista todos os estados disponíveis
 * 
 * @returns Lista de estados com contagem de imóveis
 * 
 * @example
 * const estados = await listarEstados();
 */
export async function listarEstados(): Promise<CaixaEstadosResponse> {
  const response = await fetch(`${API_BASE_URL}/estados`);
  return handleResponse<CaixaEstadosResponse>(response);
}

/**
 * Lista cidades de um estado específico
 * 
 * @param estado - Sigla do estado (ex: 'RJ')
 * @returns Lista de cidades com contagem de imóveis
 * 
 * @example
 * const cidades = await listarCidades('RJ');
 */
export async function listarCidades(
  estado: string
): Promise<CaixaCidadesResponse> {
  const params = new URLSearchParams({ estado });
  const response = await fetch(`${API_BASE_URL}/cidades?${params}`);
  return handleResponse<CaixaCidadesResponse>(response);
}

/**
 * Busca estatísticas gerais da API
 * 
 * @returns Estatísticas por estado, categoria, faixa de preço
 * 
 * @example
 * const stats = await buscarEstatisticas();
 */
export async function buscarEstatisticas(): Promise<CaixaStats> {
  const response = await fetch(`${API_BASE_URL}/stats`);
  return handleResponse<CaixaStats>(response);
}

/**
 * Exporta dados em formato JSON ou CSV
 * 
 * @param formato - 'json' ou 'csv'
 * @param filtros - Mesmos filtros de buscarImoveis
 * @returns Dados exportados ou sucesso do download
 * 
 * @example
 * await exportarDados('csv', { estado: 'RJ' });
 */
export async function exportarDados(
  formato: 'json' | 'csv' = 'json',
  filtros: BuscarImoveisParams = {}
): Promise<CaixaListResponse | { success: boolean }> {
  const params = new URLSearchParams({ 
    formato, 
    ...Object.fromEntries(
      Object.entries(filtros).map(([k, v]) => [k, String(v)])
    )
  });
  
  const response = await fetch(`${API_BASE_URL}/export?${params}`);
  
  if (formato === 'csv') {
    const blob = await response.blob();
    // Criar download automático
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `caixa_imoveis_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    return { success: true };
  }
  
  return handleResponse<CaixaListResponse>(response);
}

/**
 * Verifica saúde da API
 * 
 * @returns Status da API
 * 
 * @example
 * const health = await verificarHealth();
 */
export async function verificarHealth(): Promise<{
  status: string;
  timestamp: string;
  version: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return handleResponse(response);
}
