import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ModalityPieChartProps {
  data: Record<string, number>;
  loading?: boolean;
}

const MODALITY_COLORS: Record<string, string> = {
  'Judicial': '#DC2626',      // red-600
  'Extrajudicial': '#EA580C', // orange-600
  'Venda Direta': '#16A34A',  // green-600
  'Leilão SFI': '#2563EB',    // blue-600
  'Outros': '#6B7280',        // gray-500
};

export function ModalityPieChart({ data, loading }: ModalityPieChartProps) {
  if (loading) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-lg">Imóveis por Modalidade</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-80">
          <div className="animate-pulse">
            <div className="w-48 h-48 bg-muted rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || Object.keys(data).length === 0) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="text-lg">Imóveis por Modalidade</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-80">
          <p className="text-muted-foreground">Sem dados disponíveis</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value,
    color: MODALITY_COLORS[name] || '#6B7280',
  }));

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      const percentage = ((item.value / total) * 100).toFixed(1);
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border">
          <p className="font-semibold">{item.name}</p>
          <p className="text-sm text-muted-foreground">
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
        className="text-sm font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">Imóveis por Modalidade</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              formatter={(value: string) => {
                const item = chartData.find(d => d.name === value);
                if (!item) return value;
                const percentage = ((item.value / total) * 100).toFixed(1);
                return `${value}: ${item.value.toLocaleString('pt-BR')} (${percentage}%)`;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

