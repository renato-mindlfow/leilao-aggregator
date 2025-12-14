import { Stats } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Building2, Users, Copy, TrendingUp } from 'lucide-react';

interface StatsCardProps {
  stats: Stats | null;
  loading?: boolean;
}

export function StatsCard({ stats, loading }: StatsCardProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="pt-6">
              <div className="h-8 bg-muted rounded w-16 mb-2" />
              <div className="h-4 bg-muted rounded w-24" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const statItems = [
    {
      title: 'Total de Imóveis',
      value: stats.total_properties,
      icon: Building2,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Imóveis Únicos',
      value: stats.unique_properties,
      icon: TrendingUp,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Duplicatas',
      value: stats.duplicate_properties,
      icon: Copy,
      color: 'text-amber-600',
      bgColor: 'bg-amber-100',
    },
    {
      title: 'Leiloeiros',
      value: stats.total_auctioneers,
      icon: Users,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {statItems.map((item) => (
        <Card key={item.title}>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${item.bgColor}`}>
                <item.icon className={`w-5 h-5 ${item.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold">{item.value.toLocaleString('pt-BR')}</p>
                <p className="text-sm text-muted-foreground">{item.title}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

interface CategoryStatsProps {
  stats: Stats | null;
}

export function CategoryStats({ stats }: CategoryStatsProps) {
  if (!stats || Object.keys(stats.category_counts).length === 0) return null;

  const categoryColors: Record<string, string> = {
    'Apartamento': 'bg-blue-500',
    'Casa': 'bg-green-500',
    'Comercial': 'bg-purple-500',
    'Terreno': 'bg-amber-500',
    'Estacionamento': 'bg-gray-500',
  };

  const total = Object.values(stats.category_counts).reduce((a, b) => a + b, 0);

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-lg">Imóveis por Categoria</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3">
          {Object.entries(stats.category_counts).map(([category, count]) => (
            <div
              key={category}
              className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg"
            >
              <div className={`w-3 h-3 rounded-full ${categoryColors[category] || 'bg-slate-500'}`} />
              <span className="font-medium">{category}</span>
              <span className="text-muted-foreground">
                {count.toLocaleString('pt-BR')} ({((count / total) * 100).toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
