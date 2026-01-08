import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface Auctioneer {
  id: string;
  name: string;
  website: string | null;
  is_active: boolean;
  property_count: number;
  scrape_status: string | null;
  scrape_error: string | null;
  last_scrape: string | null;
}

type StatusFilter = 'all' | 'green' | 'yellow' | 'red';

const API_URL = import.meta.env.VITE_API_URL || 'https://leilao-backend-solitary-haze-9882.fly.dev';

export default function AdminDashboard() {
  const { isAdmin } = useAuth();
  const [auctioneers, setAuctioneers] = useState<Auctioneer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [search, setSearch] = useState('');
  const [stats, setStats] = useState({ total: 0, green: 0, yellow: 0, red: 0, totalProperties: 0 });
  const [sortColumn, setSortColumn] = useState<string>('property_count');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    if (isAdmin()) {
      fetchAuctioneers();
    }
  }, [isAdmin]);

  const fetchAuctioneers = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auctioneers`);
      if (!response.ok) throw new Error('Erro ao buscar leiloeiros');
      const data = await response.json();
      setAuctioneers(data);
      calculateStats(data);
    } catch (error) {
      console.error('Erro:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (data: Auctioneer[]) => {
    const stats = { total: data.length, green: 0, yellow: 0, red: 0, totalProperties: 0 };
    data.forEach(auc => {
      stats.totalProperties += auc.property_count || 0;
      const status = getStatus(auc);
      if (status === 'green') stats.green++;
      else if (status === 'yellow') stats.yellow++;
      else stats.red++;
    });
    setStats(stats);
  };

  const getStatus = (auc: Auctioneer): 'green' | 'yellow' | 'red' => {
    if (!auc.is_active) return 'red';
    if (auc.scrape_status === 'error') return 'red';
    if (auc.property_count > 0) {
      if (auc.last_scrape) {
        const days = (Date.now() - new Date(auc.last_scrape).getTime()) / (1000 * 60 * 60 * 24);
        return days <= 7 ? 'green' : 'yellow';
      }
      return 'yellow';
    }
    return 'red';
  };

  const getStatusIcon = (status: 'green' | 'yellow' | 'red') => {
    return status === 'green' ? '🟢' : status === 'yellow' ? '🟡' : '🔴';
  };

  const formatDate = (date: string | null) => {
    if (!date) return 'Nunca';
    return new Date(date).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const filtered = auctioneers.filter(auc => {
    const status = getStatus(auc);
    const matchFilter = filter === 'all' || status === filter;
    const matchSearch = !search || 
      auc.name.toLowerCase().includes(search.toLowerCase()) ||
      auc.id.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const sortedAuctioneers = [...filtered].sort((a, b) => {
    let aVal = a[sortColumn as keyof Auctioneer];
    let bVal = b[sortColumn as keyof Auctioneer];
    
    // Tratar nulls - para datas, nulls vão para o final
    if (sortColumn === 'last_scrape') {
      if (!aVal && !bVal) return 0;
      if (!aVal) return 1; // null vai para o final
      if (!bVal) return -1; // null vai para o final
      const aDate = new Date(aVal as string).getTime();
      const bDate = new Date(bVal as string).getTime();
      return sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
    }
    
    // Tratar nulls para outros campos
    if (aVal === null || aVal === undefined) aVal = '';
    if (bVal === null || bVal === undefined) bVal = '';
    
    // Comparar números
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    // Comparar strings
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === 'asc' 
      ? aStr.localeCompare(bStr) 
      : bStr.localeCompare(aStr);
  });

  if (!isAdmin()) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Acesso Negado</h2>
          <p className="text-gray-600">Você precisa ser administrador para acessar esta página.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-800">🏛️ Monitoramento de Leiloeiros</h2>
          <p className="text-gray-600 mt-1 text-sm">Status de integração e faróis de sistema</p>
        </div>

        {/* Cards de estatísticas */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
            <div className="text-sm text-gray-500">Total Leiloeiros</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="text-2xl font-bold text-green-600">{stats.green}</div>
            <div className="text-sm text-gray-500">🟢 Integrados</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
            <div className="text-2xl font-bold text-yellow-600">{stats.yellow}</div>
            <div className="text-sm text-gray-500">🟡 Parciais</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="text-2xl font-bold text-red-600">{stats.red}</div>
            <div className="text-sm text-gray-500">🔴 Não integrados</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="text-2xl font-bold text-blue-600">{stats.totalProperties.toLocaleString()}</div>
            <div className="text-sm text-gray-500">📊 Total Imóveis</div>
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <input
              type="text"
              placeholder="Buscar leiloeiro..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 border rounded-lg px-4 py-2"
            />
            <div className="flex gap-2">
              {(['all', 'green', 'yellow', 'red'] as StatusFilter[]).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    filter === f 
                      ? f === 'green' ? 'bg-green-500 text-white'
                        : f === 'yellow' ? 'bg-yellow-500 text-white'
                        : f === 'red' ? 'bg-red-500 text-white'
                        : 'bg-blue-500 text-white'
                      : 'bg-gray-200 hover:bg-gray-300'
                  }`}
                >
                  {f === 'all' ? `Todos (${stats.total})` : 
                   f === 'green' ? `🟢 (${stats.green})` :
                   f === 'yellow' ? `🟡 (${stats.yellow})` : `🔴 (${stats.red})`}
                </button>
              ))}
            </div>
            <button
              onClick={fetchAuctioneers}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              🔄 Atualizar
            </button>
          </div>
        </div>

        {/* Tabela */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('name')}
                >
                  Leiloeiro {sortColumn === 'name' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Website</th>
                <th 
                  className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('property_count')}
                >
                  Imóveis {sortColumn === 'property_count' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('scrape_status')}
                >
                  Scrape {sortColumn === 'scrape_status' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('last_scrape')}
                >
                  Última Extração {sortColumn === 'last_scrape' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedAuctioneers.map(auc => {
                const status = getStatus(auc);
                return (
                  <tr key={auc.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xl">{getStatusIcon(status)}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{auc.name}</div>
                      <div className="text-sm text-gray-500">{auc.id}</div>
                    </td>
                    <td className="px-4 py-3">
                      {auc.website ? (
                        <a href={auc.website} target="_blank" rel="noopener noreferrer"
                           className="text-blue-500 hover:text-blue-700 text-sm truncate block max-w-xs">
                          {auc.website.replace(/https?:\/\//, '')}
                        </a>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={auc.property_count > 0 ? 'text-green-600 font-medium' : 'text-gray-400'}>
                        {auc.property_count?.toLocaleString() || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        auc.scrape_status === 'success' ? 'bg-green-100 text-green-800' :
                        auc.scrape_status === 'error' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {auc.scrape_status || 'pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDate(auc.last_scrape)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="bg-gray-50 px-4 py-3 border-t text-sm text-gray-500">
            Mostrando {filtered.length} de {auctioneers.length} leiloeiros
          </div>
        </div>

        {/* Legenda */}
        <div className="mt-6 bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold mb-3">Legenda</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span>🟢</span>
              <span><strong>Integrado:</strong> Ativo, com imóveis, scrape recente (≤7 dias)</span>
            </div>
            <div className="flex items-center gap-2">
              <span>🟡</span>
              <span><strong>Parcial:</strong> Ativo mas sem imóveis ou scrape antigo</span>
            </div>
            <div className="flex items-center gap-2">
              <span>🔴</span>
              <span><strong>Não integrado:</strong> Inativo, erro ou nunca executou</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

