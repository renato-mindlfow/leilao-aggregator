/**
 * Utilitários de formatação para exibição de dados
 * Específicos para dados da API Caixa que vêm em centavos
 */

/**
 * Converte valor em centavos para reais formatado
 * 
 * @param centavos - Valor em centavos (ex: 8395740)
 * @returns Valor formatado (ex: "R$ 83.957,40")
 * 
 * @example
 * centavosParaReais(8395740) // "R$ 83.957,40"
 * centavosParaReais(25000000) // "R$ 250.000,00"
 * centavosParaReais(null) // "N/A"
 */
export function centavosParaReais(centavos: number | null | undefined): string {
  if (centavos === null || centavos === undefined) return 'N/A';
  
  const reais = centavos / 100;
  
  return reais.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

/**
 * Converte reais para centavos (para filtros)
 * 
 * @param reais - Valor em reais (ex: 250000)
 * @returns Valor em centavos (ex: 25000000)
 * 
 * @example
 * reaisParaCentavos(250000) // 25000000
 * reaisParaCentavos(83957.40) // 8395740
 */
export function reaisParaCentavos(reais: number | null | undefined): number | null {
  if (reais === null || reais === undefined) return null;
  return Math.round(reais * 100);
}

/**
 * Formata área em m²
 * 
 * @param area - Área em metros quadrados
 * @returns Área formatada (ex: "85,50 m²")
 * 
 * @example
 * formatarArea(85.5) // "85,50 m²"
 * formatarArea(null) // "N/A"
 */
export function formatarArea(area: number | null | undefined): string {
  if (area === null || area === undefined) return 'N/A';
  
  return `${area.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })} m²`;
}

/**
 * Formata endereço completo a partir de partes
 * 
 * @param endereco - Objeto com partes do endereço
 * @returns Endereço formatado
 * 
 * @example
 * formatarEndereco({
 *   logradouro: 'Rua Exemplo',
 *   numero: '123',
 *   bairro: 'Centro'
 * }) // "Rua Exemplo, 123 - Centro"
 */
export function formatarEndereco(endereco: {
  logradouro?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
}): string {
  const partes: string[] = [];
  
  if (endereco.logradouro) partes.push(endereco.logradouro);
  if (endereco.numero) partes.push(endereco.numero);
  if (endereco.complemento) partes.push(endereco.complemento);
  if (endereco.bairro) partes.push(`- ${endereco.bairro}`);
  
  return partes.join(', ') || 'Endereço não disponível';
}

/**
 * Formata data/timestamp ISO
 * 
 * @param timestamp - ISO timestamp
 * @returns Data formatada (ex: "12/12/2025 09:32")
 * 
 * @example
 * formatarData('2025-12-12T09:32:39.123456') // "12/12/2025 09:32"
 * formatarData(null) // "N/A"
 */
export function formatarData(timestamp: string | null | undefined): string {
  if (!timestamp) return 'N/A';
  
  const data = new Date(timestamp);
  
  return data.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Formata percentual de desconto
 * 
 * @param percentual - Percentual (ex: 30)
 * @returns Percentual formatado (ex: "30%")
 * 
 * @example
 * formatarDesconto(30) // "30%"
 * formatarDesconto(null) // "N/A"
 */
export function formatarDesconto(percentual: number | null | undefined): string {
  if (percentual === null || percentual === undefined) return 'N/A';
  return `${percentual}%`;
}

/**
 * Trunca texto com reticências
 * 
 * @param texto - Texto a truncar
 * @param tamanho - Tamanho máximo (default: 100)
 * @returns Texto truncado
 * 
 * @example
 * truncarTexto('Texto muito longo...', 10) // "Texto muit..."
 */
export function truncarTexto(texto: string | null | undefined, tamanho = 100): string {
  if (!texto) return '';
  if (texto.length <= tamanho) return texto;
  return `${texto.substring(0, tamanho)}...`;
}

/**
 * Formata número para exibição compacta
 * 
 * @param numero - Número a formatar
 * @returns Número formatado (ex: "28,1k" ou "1,2M")
 * 
 * @example
 * formatarNumeroCompacto(28183) // "28,2k"
 * formatarNumeroCompacto(1500000) // "1,5M"
 */
export function formatarNumeroCompacto(numero: number | null | undefined): string {
  if (numero === null || numero === undefined) return 'N/A';
  
  if (numero >= 1000000) {
    return `${(numero / 1000000).toFixed(1)}M`;
  }
  if (numero >= 1000) {
    return `${(numero / 1000).toFixed(1)}k`;
  }
  return numero.toString();
}
