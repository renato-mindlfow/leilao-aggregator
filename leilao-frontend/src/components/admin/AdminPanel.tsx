import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Users, Search, TrendingUp, DollarSign, Calendar } from 'lucide-react';
// import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const API_URL = import.meta.env.VITE_API_URL || 'https://leilao-backend-solitary-haze-9882.fly.dev';

interface AdminStats {
  total_users: number;
  by_status: Record<string, number>;
  searches_today: number;
  views_today: number;
}

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  subscription_status: string;
  subscription_plan?: string;
  trial_views_used?: number;
  trial_views_limit?: number;
  created_at: string;
  last_login?: string;
}

interface SearchAnalytics {
  top_states: Array<{ state: string; count: number }>;
  top_categories: Array<{ category: string; count: number }>;
  price_ranges: Array<{ range: string; count: number }>;
}

export const AdminPanel = () => {
  const { isAdmin } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [searchAnalytics, setSearchAnalytics] = useState<SearchAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAdmin()) {
      fetchData();
    }
  }, []);

  const fetchData = async () => {
    try {
      // Stats
      const statsRes = await fetch(`${API_URL}/api/admin/stats`);
      if (statsRes.ok) setStats(await statsRes.json());

      // Users
      const usersRes = await fetch(`${API_URL}/api/admin/users?limit=50`);
      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users);
      }

      // Search Analytics
      const analyticsRes = await fetch(`${API_URL}/api/admin/search-analytics?days=30`);
      if (analyticsRes.ok) setSearchAnalytics(await analyticsRes.json());

    } catch (error) {
      console.error('Erro ao carregar dados admin:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isAdmin()) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-6">
          Painel Administrativo
        </h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={<Users />}
            label="Total Usuários"
            value={stats?.total_users || 0}
            color="blue"
          />
          <StatCard
            icon={<Calendar />}
            label="Em Trial"
            value={stats?.by_status?.trial || 0}
            color="yellow"
          />
          <StatCard
            icon={<DollarSign />}
            label="Pagantes"
            value={stats?.by_status?.active || 0}
            color="green"
          />
          <StatCard
            icon={<Search />}
            label="Buscas Hoje"
            value={stats?.searches_today || 0}
            color="purple"
          />
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="p-4 border-b">
              <TabsTrigger value="overview">Visão Geral</TabsTrigger>
              <TabsTrigger value="users">Usuários</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
            </TabsList>

            <TabsContent value="users" className="p-4 sm:p-6">
              <UsersTable users={users} />
            </TabsContent>

            <TabsContent value="analytics" className="p-4 sm:p-6">
              <AnalyticsView data={searchAnalytics} />
            </TabsContent>

            <TabsContent value="overview" className="p-4 sm:p-6">
              <OverviewView stats={stats} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: 'blue' | 'yellow' | 'green' | 'purple';
}

const StatCard = ({ icon, label, value, color }: StatCardProps) => {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 sm:p-6">
      <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg ${colors[color]} flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <p className="text-gray-500 text-xs sm:text-sm">{label}</p>
      <p className="text-xl sm:text-2xl font-bold text-gray-800">{value}</p>
    </div>
  );
};

const UsersTable = ({ users }: { users: User[] }) => (
  <div className="overflow-x-auto">
    <table className="w-full min-w-[600px]">
      <thead>
        <tr className="bg-gray-50">
          <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Usuário</th>
          <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
          <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Trial</th>
          <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Cadastro</th>
        </tr>
      </thead>
      <tbody>
        {users.map((user) => (
          <tr key={user.id} className="border-t">
            <td className="px-4 py-3">
              <p className="font-medium text-gray-800">{user.name || 'Sem nome'}</p>
              <p className="text-sm text-gray-500">{user.email}</p>
            </td>
            <td className="px-4 py-3">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                user.subscription_status === 'active' 
                  ? 'bg-green-100 text-green-700'
                  : user.subscription_status === 'trial'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {user.subscription_status}
              </span>
            </td>
            <td className="px-4 py-3 text-sm text-gray-600">
              {user.trial_views_used || 0} / {user.trial_views_limit || 20}
            </td>
            <td className="px-4 py-3 text-sm text-gray-600">
              {new Date(user.created_at).toLocaleDateString('pt-BR')}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const AnalyticsView = ({ data }: { data: SearchAnalytics | null }) => {
  if (!data) return <p className="text-gray-500">Carregando analytics...</p>;

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Top Estados</h3>
        <div className="space-y-2">
          {data.top_states?.map((item, i) => (
            <div key={i} className="flex justify-between items-center bg-gray-50 p-2 rounded">
              <span className="text-gray-700">{item.state}</span>
              <span className="text-gray-500 font-medium">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Top Categorias</h3>
        <div className="space-y-2">
          {data.top_categories?.map((item, i) => (
            <div key={i} className="flex justify-between items-center bg-gray-50 p-2 rounded">
              <span className="text-gray-700">{item.category}</span>
              <span className="text-gray-500 font-medium">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div>
        <h3 className="font-semibold text-gray-800 mb-3">Faixas de Preço</h3>
        <div className="space-y-2">
          {data.price_ranges?.map((item, i) => (
            <div key={i} className="flex justify-between items-center bg-gray-50 p-2 rounded">
              <span className="text-gray-700">{item.range}</span>
              <span className="text-gray-500 font-medium">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const OverviewView = ({ stats }: { stats: AdminStats | null }) => (
  <div className="text-center py-8">
    <TrendingUp size={48} className="mx-auto mb-4 text-gray-300" />
    <p className="text-gray-500">Dashboard com gráficos será implementado aqui</p>
    <p className="text-gray-400 text-sm mt-2">
      Total: {stats?.total_users} usuários • {stats?.views_today || 0} views hoje
    </p>
  </div>
);

export default AdminPanel;

