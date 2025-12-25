import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowUpDown } from 'lucide-react';

export type SortOption = 
  | 'recent'
  | 'price_desc' 
  | 'price_asc' 
  | 'date_asc' 
  | 'date_desc' 
  | 'discount_desc';

interface PropertySortProps {
  value: SortOption;
  onChange: (value: SortOption) => void;
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'recent', label: 'Inclusão Recente' },
  { value: 'price_desc', label: 'Maior Valor' },
  { value: 'price_asc', label: 'Menor Valor' },
  { value: 'date_asc', label: 'Data Mais Próxima' },
  { value: 'date_desc', label: 'Data Mais Distante' },
  { value: 'discount_desc', label: 'Maior Desconto' },
];

export function PropertySort({ value, onChange }: PropertySortProps) {
  return (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
      <Select value={value} onValueChange={(v) => onChange(v as SortOption)}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Ordenar por" />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

