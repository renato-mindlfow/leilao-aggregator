/**
 * PALETA DE CORES PARA CATEGORIAS
 * Cores consistentes entre legenda e badges dos cards
 */

export const CATEGORY_COLORS: Record<string, { bg: string; text: string; bullet: string }> = {
  'Apartamento': {
    bg: 'bg-blue-500',
    text: 'text-white',
    bullet: '#3B82F6', // blue-500
  },
  'Casa': {
    bg: 'bg-green-500',
    text: 'text-white',
    bullet: '#22C55E', // green-500
  },
  'Terreno': {
    bg: 'bg-amber-500',
    text: 'text-white',
    bullet: '#F59E0B', // amber-500
  },
  'Comercial': {
    bg: 'bg-purple-500',
    text: 'text-white',
    bullet: '#A855F7', // purple-500
  },
  'Rural': {
    bg: 'bg-emerald-600',
    text: 'text-white',
    bullet: '#059669', // emerald-600
  },
  'Outro': {
    bg: 'bg-orange-500',
    text: 'text-white',
    bullet: '#F97316', // orange-500
  },
  'Outros': {
    bg: 'bg-orange-500',
    text: 'text-white',
    bullet: '#F97316', // orange-500
  },
  'Garagem': {
    bg: 'bg-gray-500',
    text: 'text-white',
    bullet: '#6B7280', // gray-500
  },
  'Estacionamento': {
    bg: 'bg-gray-500',
    text: 'text-white',
    bullet: '#6B7280', // gray-500
  },
  'Loja': {
    bg: 'bg-pink-500',
    text: 'text-white',
    bullet: '#EC4899', // pink-500
  },
  'Área': {
    bg: 'bg-red-500',
    text: 'text-white',
    bullet: '#EF4444', // red-500
  },
  'Sala Comercial': {
    bg: 'bg-indigo-500',
    text: 'text-white',
    bullet: '#6366F1', // indigo-500
  },
  'Fazenda': {
    bg: 'bg-lime-600',
    text: 'text-white',
    bullet: '#65A30D', // lime-600
  },
  'Chácara': {
    bg: 'bg-teal-500',
    text: 'text-white',
    bullet: '#14B8A6', // teal-500
  },
  'Galpão': {
    bg: 'bg-purple-500',
    text: 'text-white',
    bullet: '#A855F7', // purple-500
  },
  'Prédio': {
    bg: 'bg-purple-500',
    text: 'text-white',
    bullet: '#A855F7', // purple-500
  },
};

export const getCategoryColor = (category: string) => {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS['Outro'];
};

/**
 * CORES PARA MODALIDADE DE LEILÃO
 */
export const AUCTION_TYPE_COLORS: Record<string, { bg: string; text: string; bullet: string }> = {
  'Extrajudicial': {
    bg: 'bg-blue-500',
    text: 'text-white',
    bullet: '#3B82F6',
  },
  'Judicial': {
    bg: 'bg-green-500',
    text: 'text-white',
    bullet: '#22C55E',
  },
  'Outros': {
    bg: 'bg-gray-500',
    text: 'text-white',
    bullet: '#6B7280',
  },
  'Venda Direta': {
    bg: 'bg-red-500',
    text: 'text-white',
    bullet: '#EF4444',
  },
  'Venda Direta Online': {
    bg: 'bg-red-500',
    text: 'text-white',
    bullet: '#EF4444',
  },
  'Leilão SFI': {
    bg: 'bg-purple-500',
    text: 'text-white',
    bullet: '#A855F7',
  },
  'Venda Online': {
    bg: 'bg-orange-500',
    text: 'text-white',
    bullet: '#F97316',
  },
};

export const getAuctionTypeColor = (type: string) => {
  return AUCTION_TYPE_COLORS[type] || AUCTION_TYPE_COLORS['Outros'];
};

