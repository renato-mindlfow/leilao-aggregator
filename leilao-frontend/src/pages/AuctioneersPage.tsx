import { useState, useEffect } from 'react';

interface Auctioneer {
  id: string;
  name: string;
  url: string | null;
  total_properties: number;
  active_properties: number;
  last_update: string | null;
}

interface AuctioneersStats {
  summary: {
    total_auctioneers: number;
    total_properties: number;
    active_properties: number;
  };
  auctioneers: Auctioneer[];
}

const API_URL = import.meta.env.VITE_API_URL || 'https://leilao-backend-solitary-haze-9882.fly.dev';

export default function AuctioneersPage() {
  const [data, setData] = useState<AuctioneersStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchAuctioneers();
  }, []);

  const fetchAuctioneers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/auctioneers/stats`);
      if (!response.ok) throw new Error('Erro ao carregar leiloeiros');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  const filteredAuctioneers = data?.auctioneers.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.id.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-red-600 text-center">
          <p className="text-xl font-semibold">Erro</p>
          <p>{error}</p>
          <button
            onClick={fetchAuctioneers}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Leiloeiros Integrados
          </h1>
          <p className="text-gray-600">
            Visualize todos os leiloeiros e a quantidade de imoveis de cada um
          </p>
        </div>

        {/* Summary Cards */}
        {data && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500 uppercase tracking-wide">
                Total de Leiloeiros
              </div>
              <div className="text-3xl font-bold text-blue-600">
                {data.summary.total_auctioneers}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500 uppercase tracking-wide">
                Total de Imoveis
              </div>
              <div className="text-3xl font-bold text-green-600">
                {data.summary.total_properties.toLocaleString('pt-BR')}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-500 uppercase tracking-wide">
                Imoveis Ativos
              </div>
              <div className="text-3xl font-bold text-purple-600">
                {data.summary.active_properties.toLocaleString('pt-BR')}
              </div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Buscar leiloeiro..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    #
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Leiloeiro
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Imoveis
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ativos
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ultima Atualizacao
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acoes
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredAuctioneers.map((auctioneer, index) => (
                  <tr key={auctioneer.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {index + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {auctioneer.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {auctioneer.id}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-semibold text-gray-900">
                      {auctioneer.total_properties.toLocaleString('pt-BR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                      {auctioneer.active_properties.toLocaleString('pt-BR')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(auctioneer.last_update)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                      {auctioneer.url && (
                        <a
                          href={auctioneer.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Ver site
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredAuctioneers.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              Nenhum leiloeiro encontrado
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 text-sm text-gray-500 text-center">
          Mostrando {filteredAuctioneers.length} de {data?.auctioneers.length || 0} leiloeiros
        </div>
      </div>
    </div>
  );
}
