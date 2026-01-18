import { useState, useCallback, useEffect } from 'react';

/**
 * Placeholder SVG components por categoria de imóvel
 * Estilo minimalista em escala de cinza (#9ca3af para desenho, #f3f4f6 para fundo)
 */

interface PlaceholderSVGProps {
  category: string;
}

const PlaceholderSVG = ({ category }: PlaceholderSVGProps) => {
  const normalizedCategory = category?.toLowerCase() || 'default';

  // Apartamento
  if (normalizedCategory.includes('apartamento') || normalizedCategory.includes('apto') || normalizedCategory.includes('flat')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="40" y="60" width="120" height="90" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <line x1="80" y1="60" x2="80" y2="150" stroke="#9ca3af" strokeWidth="2"/>
        <line x2="120" y1="60" x2="120" y2="150" stroke="#9ca3af" strokeWidth="2"/>
        <rect x="85" y="95" width="30" height="40" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Apartamento</text>
      </svg>
    );
  }

  // Casa
  if (normalizedCategory.includes('casa') || normalizedCategory.includes('sobrado') || normalizedCategory.includes('residência')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <polygon points="100,30 150,70 150,120 50,120 50,70" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <rect x="75" y="90" width="50" height="30" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <line x1="100" y1="90" x2="100" y2="120" stroke="#9ca3af" strokeWidth="1.5"/>
        <circle cx="105" cy="105" r="3" fill="#9ca3af"/>
        <text x="100" y="140" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Casa</text>
      </svg>
    );
  }

  // Terreno
  if (normalizedCategory.includes('terreno') || normalizedCategory.includes('lote') || normalizedCategory.includes('área') || normalizedCategory.includes('area')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="50" y="60" width="100" height="60" stroke="#9ca3af" strokeWidth="2" strokeDasharray="5,5" fill="none"/>
        <line x1="60" y1="80" x2="140" y2="80" stroke="#9ca3af" strokeWidth="1.5" strokeDasharray="3,3"/>
        <line x1="60" y1="100" x2="140" y2="100" stroke="#9ca3af" strokeWidth="1.5" strokeDasharray="3,3"/>
        <circle cx="70" cy="95" r="2" fill="#9ca3af"/>
        <circle cx="130" cy="95" r="2" fill="#9ca3af"/>
        <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Terreno</text>
      </svg>
    );
  }

  // Comercial
  if (normalizedCategory.includes('comercial') || normalizedCategory.includes('prédio') || normalizedCategory.includes('predio')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="50" y="40" width="100" height="80" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <line x1="70" y1="40" x2="70" y2="120" stroke="#9ca3af" strokeWidth="2"/>
        <line x1="130" y1="40" x2="130" y2="120" stroke="#9ca3af" strokeWidth="2"/>
        <rect x="75" y="70" width="20" height="25" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <rect x="105" y="70" width="20" height="25" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <rect x="135" y="70" width="15" height="25" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <text x="100" y="140" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Comercial</text>
      </svg>
    );
  }

  // Rural / Fazenda / Chácara
  if (normalizedCategory.includes('rural') || normalizedCategory.includes('fazenda') || normalizedCategory.includes('chácara') || normalizedCategory.includes('chacara') || normalizedCategory.includes('sítio') || normalizedCategory.includes('sitio')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="60" y="70" width="80" height="50" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <polygon points="100,40 120,70 80,70" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <circle cx="70" cy="110" r="8" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <circle cx="85" cy="110" r="6" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <line x1="100" y1="70" x2="100" y2="120" stroke="#9ca3af" strokeWidth="1.5"/>
        <circle cx="105" cy="90" r="2" fill="#9ca3af"/>
        <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Rural</text>
      </svg>
    );
  }

  // Galpão
  if (normalizedCategory.includes('galpão') || normalizedCategory.includes('galpao') || normalizedCategory.includes('armazém') || normalizedCategory.includes('armazem')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="40" y="80" width="120" height="40" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <polygon points="40,80 100,50 160,80" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <rect x="70" y="100" width="30" height="20" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <line x1="85" y1="100" x2="85" y2="120" stroke="#9ca3af" strokeWidth="1.5"/>
        <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Galpão</text>
      </svg>
    );
  }

  // Sala Comercial / Sala
  if (normalizedCategory.includes('sala')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="50" y="60" width="100" height="50" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <line x1="75" y1="60" x2="75" y2="110" stroke="#9ca3af" strokeWidth="1.5"/>
        <line x1="125" y1="60" x2="125" y2="110" stroke="#9ca3af" strokeWidth="1.5"/>
        <rect x="80" y="80" width="25" height="20" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <rect x="110" y="80" width="25" height="20" stroke="#9ca3af" strokeWidth="1.5" fill="none"/>
        <text x="100" y="130" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Sala</text>
      </svg>
    );
  }

  // Loja
  if (normalizedCategory.includes('loja')) {
    return (
      <svg width="100%" height="100%" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
        <rect width="200" height="150" fill="#f3f4f6"/>
        <rect x="40" y="70" width="120" height="50" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <rect x="50" y="90" width="100" height="20" stroke="#9ca3af" strokeWidth="2" fill="none"/>
        <line x1="100" y1="90" x2="100" y2="110" stroke="#9ca3af" strokeWidth="1.5"/>
        <rect x="55" y="95" width="20" height="10" stroke="#9ca3af" strokeWidth="1" fill="none"/>
        <rect x="125" y="95" width="20" height="10" stroke="#9ca3af" strokeWidth="1" fill="none"/>
        <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Loja</text>
      </svg>
    );
  }

  // Default / Outro
  return (
    <svg width="200" height="150" viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="150" fill="#f3f4f6"/>
      <rect x="50" y="60" width="100" height="60" stroke="#9ca3af" strokeWidth="2" fill="none"/>
      <line x1="60" y1="75" x2="140" y2="75" stroke="#9ca3af" strokeWidth="1.5"/>
      <line x1="60" y1="90" x2="140" y2="90" stroke="#9ca3af" strokeWidth="1.5"/>
      <line x1="60" y1="105" x2="140" y2="105" stroke="#9ca3af" strokeWidth="1.5"/>
      <text x="100" y="135" textAnchor="middle" fill="#9ca3af" fontSize="12" fontFamily="Arial, sans-serif">Imóvel</text>
    </svg>
  );
};

/**
 * Hook para gerenciar imagem de propriedade com fallback para placeholder
 */
export function usePropertyImage(imageUrl: string | null | undefined, category: string | null | undefined = 'Outro') {
  const [hasError, setHasError] = useState(false);
  const [shouldUsePlaceholder, setShouldUsePlaceholder] = useState(!imageUrl);

  const handleError = useCallback(() => {
    setHasError(true);
    setShouldUsePlaceholder(true);
  }, []);

  // Reset quando imageUrl muda
  useEffect(() => {
    if (imageUrl) {
      setHasError(false);
      setShouldUsePlaceholder(false);
    } else {
      setShouldUsePlaceholder(true);
    }
  }, [imageUrl]);

  const src = shouldUsePlaceholder ? null : imageUrl || null;

  return {
    src,
    hasError,
    shouldUsePlaceholder,
    onError: handleError,
    category: category || 'Outro',
  };
}

/**
 * Função para obter placeholder SVG como data URL
 */
export function getPlaceholderUrl(category: string | null | undefined = 'Outro'): string {
  // Retorna uma string vazia - o componente será renderizado diretamente
  // O placeholder será renderizado como SVG inline, não como URL
  return '';
}

/**
 * Componente de Placeholder para ser usado diretamente
 */
export function PropertyPlaceholder({ category }: PlaceholderSVGProps) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-100">
      <PlaceholderSVG category={category || 'Outro'} />
    </div>
  );
}

export default PropertyPlaceholder;
