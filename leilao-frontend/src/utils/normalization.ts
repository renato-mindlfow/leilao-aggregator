/**
 * UTILITÁRIOS DE NORMALIZAÇÃO
 * Corrige problemas de formatação de estados e cidades
 */

// Lista de estados brasileiros válidos
export const BRAZILIAN_STATES: Record<string, string> = {
  'AC': 'AC', 'Ac': 'AC', 'ac': 'AC',
  'AL': 'AL', 'Al': 'AL', 'al': 'AL',
  'AP': 'AP', 'Ap': 'AP', 'ap': 'AP',
  'AM': 'AM', 'Am': 'AM', 'am': 'AM',
  'BA': 'BA', 'Ba': 'BA', 'ba': 'BA',
  'CE': 'CE', 'Ce': 'CE', 'ce': 'CE',
  'DF': 'DF', 'Df': 'DF', 'df': 'DF',
  'ES': 'ES', 'Es': 'ES', 'es': 'ES',
  'GO': 'GO', 'Go': 'GO', 'go': 'GO',
  'MA': 'MA', 'Ma': 'MA', 'ma': 'MA',
  'MT': 'MT', 'Mt': 'MT', 'mt': 'MT',
  'MS': 'MS', 'Ms': 'MS', 'ms': 'MS',
  'MG': 'MG', 'Mg': 'MG', 'mg': 'MG',
  'PA': 'PA', 'Pa': 'PA', 'pa': 'PA',
  'PB': 'PB', 'Pb': 'PB', 'pb': 'PB',
  'PR': 'PR', 'Pr': 'PR', 'pr': 'PR',
  'PE': 'PE', 'Pe': 'PE', 'pe': 'PE',
  'PI': 'PI', 'Pi': 'PI', 'pi': 'PI',
  'RJ': 'RJ', 'Rj': 'RJ', 'rj': 'RJ',
  'RN': 'RN', 'Rn': 'RN', 'rn': 'RN',
  'RS': 'RS', 'Rs': 'RS', 'rs': 'RS',
  'RO': 'RO', 'Ro': 'RO', 'ro': 'RO',
  'RR': 'RR', 'Rr': 'RR', 'rr': 'RR',
  'SC': 'SC', 'Sc': 'SC', 'sc': 'SC',
  'SP': 'SP', 'Sp': 'SP', 'sp': 'SP',
  'SE': 'SE', 'Se': 'SE', 'se': 'SE',
  'TO': 'TO', 'To': 'TO', 'to': 'TO',
  'XX': 'XX', // Estado não identificado
};

/**
 * Normaliza sigla de estado para uppercase
 */
export const normalizeState = (state: string | null | undefined): string => {
  if (!state) return 'XX';
  const trimmed = state.trim();
  const normalized = BRAZILIAN_STATES[trimmed];
  if (normalized) return normalized;
  // Se não encontrou, tentar uppercase dos primeiros 2 caracteres
  return trimmed.length >= 2 ? trimmed.substring(0, 2).toUpperCase() : 'XX';
};

/**
 * Normaliza nome de cidade
 * - Remove sufixo de estado (ex: "Açailândia - Ma" -> "Açailândia")
 * - Aplica Title Case
 * - Remove espaços extras
 */
export const normalizeCity = (city: string | null | undefined): string => {
  if (!city) return 'Não informada';
  
  let normalized = city.trim();
  
  // Remover sufixo de estado (ex: " - Ma", " - SP", "/SP", " -Ma", "-SP")
  normalized = normalized.replace(/\s*[-\/]\s*[A-Za-z]{2}\s*$/i, '');
  
  // Title Case
  normalized = normalized
    .toLowerCase()
    .split(' ')
    .map((word, index) => {
      // Palavras que não devem ser capitalizadas (exceto no início)
      const lowercase = ['de', 'da', 'do', 'das', 'dos', 'e'];
      if (index > 0 && lowercase.includes(word)) return word;
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(' ');
  
  // Primeira letra sempre maiúscula
  if (normalized.length > 0) {
    normalized = normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }
  
  return normalized;
};

/**
 * Formata data para exibição (DD/MM/YYYY)
 */
export const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return '-';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '-';
    
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return '-';
  }
};

/**
 * Formata valor monetário
 */
export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-';
  
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

/**
 * Calcula desconto percentual
 */
export const calculateDiscount = (
  evaluationValue: number | null | undefined,
  auctionValue: number | null | undefined
): number | null => {
  if (!evaluationValue || !auctionValue || evaluationValue <= 0) return null;
  
  const discount = ((evaluationValue - auctionValue) / evaluationValue) * 100;
  return Math.round(discount);
};

