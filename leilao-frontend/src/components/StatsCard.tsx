import { Stats } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Building2, Users, Copy, TrendingUp } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

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

const normalizeCategory = (category: string): string => {
  const mappings: Record<string, string> = {
    'Estacionamento': 'Garagem',
    'Galpão': 'Comercial',
    'Prédio': 'Comercial',
    'GALPAO': 'Comercial',
    'PREDIO': 'Comercial',
  };
  return mappings[category] || category;
};

// Cores das categorias
const categoryColors: Record<string, string> = {
  'Apartamento': '#2563EB',    // Azul
  'Casa': '#16A34A',           // Verde
  'Terreno': '#CA8A04',        // Amarelo/Mostarda
  'Comercial': '#9333EA',      // Roxo
  'Garagem': '#475569',        // Cinza escuro
  'Rural': '#059669',          // Verde escuro
  'Área': '#DC2626',           // Vermelho
  'Outro': '#EA580C',          // Laranja
  'Outros': '#EA580C',
  'Estacionamento': '#475569',
  'Galpão': '#9333EA',
  'Prédio': '#9333EA',
};

// Paleta para modalidades - Opção C Vibrante Equilibrada
const MODALITY_COLORS: Record<string, string> = {
  'Extrajudicial': '#2563EB',  // Azul
  'Judicial': '#10B981',        // Verde
  'Venda Direta': '#F97316',    // Laranja
  'Leilão SFI': '#8B5CF6',      // Roxo
  'Outros': '#6B7280',          // Cinza
};

interface CategoryStatsProps {
  stats: Stats | null;
  modalityData?: Record<string, number>;
  modalityLoading?: boolean;
}

export function CategoryStats({ stats, modalityData, modalityLoading }: CategoryStatsProps) {
  if (!stats || Object.keys(stats.category_counts).length === 0) return null;

  // Agrupar categorias normalizadas
  const normalizedCounts: Record<string, number> = {};
  Object.entries(stats.category_counts).forEach(([category, count]) => {
    const normalized = normalizeCategory(category);
    normalizedCounts[normalized] = (normalizedCounts[normalized] || 0) + count;
  });

  const totalCategories = Object.values(normalizedCounts).reduce((a, b) => a + b, 0);

  // Ordenar categorias do maior para menor
  const sortedCategories = Object.entries(normalizedCounts).sort((a, b) => b[1] - a[1]);

  // Preparar dados do gráfico de modalidades (ordenados do maior para menor)
  const chartData = modalityData 
    ? Object.entries(modalityData)
        .map(([name, value]) => ({
          name,
          value,
          color: MODALITY_COLORS[name] || '#6B7280',
        }))
        .sort((a, b) => b.value - a.value)
    : [];

  const totalModality = chartData.reduce((sum, item) => sum + item.value, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      const percentage = ((item.value / totalModality) * 100).toFixed(1);
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border">
          <p className="font-semibold">{item.name}</p>
          <p className="text-sm text-gray-600">
            {item.value.toLocaleString('pt-BR')} imóveis ({percentage}%)
          </p>
        </div>
      );
    }
    return null;
  };

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        className="text-sm font-bold"
      >
        {`${(percent * 100).toFixed(1)}%`}
      </text>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      {/* Coluna Esquerda: Imóveis por Categoria */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Imóveis por Categoria</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Grid de 2 colunas para as categorias */}
          <div className="grid grid-cols-2 gap-3">
            {sortedCategories.map(([category, count]) => (
              <div
                key={category}
                className="flex items-center gap-2"
              >
                <div 
                  className="w-3 h-3 rounded-full flex-shrink-0" 
                  style={{ backgroundColor: categoryColors[category] || '#64748B' }}
                />
                <span className="font-medium text-sm">{category}</span>
                <span className="text-muted-foreground text-sm">
                  {count.toLocaleString('pt-BR')} ({((count / totalCategories) * 100).toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Coluna Direita: Imóveis por Modalidade (Gráfico Pizza 3D) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Imóveis por Modalidade</CardTitle>
        </CardHeader>
        <CardContent>
          {modalityLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-pulse">
                <div className="w-40 h-40 bg-muted rounded-full" />
              </div>
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-muted-foreground">Sem dados disponíveis</p>
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row items-center gap-4">
              {/* Gráfico 3D */}
              <div className="w-full lg:w-1/2 relative">
                {/* Sombra para efeito 3D */}
                <div 
                  className="absolute left-1/2 top-1/2 w-40 h-40 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    background: 'rgba(0,0,0,0.1)',
                    transform: 'translate(-50%, -45%) scale(1, 0.3)',
                    filter: 'blur(8px)',
                  }}
                />
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <defs>
                      {/* Gradientes para efeito 3D */}
                      {chartData.map((entry, index) => (
                        <linearGradient key={`gradient-${index}`} id={`gradient-${index}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
                          <stop offset="100%" stopColor={entry.color} stopOpacity={0.7} />
                        </linearGradient>
                      ))}
                    </defs>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={renderCustomLabel}
                      outerRadius={80}
                      innerRadius={0}
                      fill="#8884d8"
                      dataKey="value"
                      paddingAngle={2}
                      stroke="#fff"
                      strokeWidth={2}
                      startAngle={90}
                      endAngle={-270}
                    >
                      {chartData.map((_entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={`url(#gradient-${index})`}
                          style={{
                            filter: 'drop-shadow(2px 4px 3px rgba(0,0,0,0.2))',
                          }}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legenda */}
              <div className="w-full lg:w-1/2 space-y-2">
                {chartData.map((item) => {
                  const percentage = ((item.value / totalModality) * 100).toFixed(1);
                  return (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-sm text-gray-700">{item.name}</span>
                      </div>
                      <span className="text-sm text-gray-600">
                        {item.value.toLocaleString('pt-BR')} ({percentage}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
