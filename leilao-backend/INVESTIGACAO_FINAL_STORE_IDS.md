# INVESTIGAÇÃO FINAL: Sites têm inventário próprio ou são agregadores?

## Análise Realizada

### 1. Lance no Leilão (lancenoleilao.com.br)
- **URL /imoveis:** Retorna 404
- **HTML:** Não encontrou indicadores de API Superbid no HTML estático
- **Conclusão:** Site parece ser um sistema próprio (não usa Superbid diretamente no HTML)

### 2. Freitas Leiloeiro (freitasleiloeiro.com.br)
- **Estrutura:** Site próprio com menu (Agenda, Organização)
- **Análise:** Requer investigação mais profunda das requisições de rede

## Descoberta Importante

Todos os 9 sites testados retornam:
- **store.id: 1161** na API Superbid
- **11.475 imóveis** (filtrado de 46.903 totais)

## Hipóteses

### Hipótese 1: Agregadores/White-label
- Sites são white-label da Superbid
- Todos compartilham o mesmo catálogo (store.id: 1161)
- Não têm inventário próprio, apenas exibem catálogo agregado

### Hipótese 2: Store Compartilhado
- store.id: 1161 é um store genérico/compartilhado
- Agrega múltiplos leiloeiros
- Cada leiloeiro pode ter seu próprio store.id, mas não está sendo usado

### Hipótese 3: Sites Próprios
- Alguns sites têm sistema próprio
- Não usam API Superbid diretamente
- Requerem scraping HTML tradicional

## Recomendação

**OPÇÃO A: Scraper Genérico Superbid**
- Se todos são agregadores, criar 1 scraper para store.id: 1161
- Configurar 1 site "superbid_aggregado" ao invés de 30 individuais
- Mais eficiente e menos manutenção

**OPÇÃO B: Investigação Manual Profunda**
- Acessar cada site manualmente
- Navegar até página de imóveis
- Monitorar requisições de rede em tempo real
- Capturar store.id específico (se existir)

## Próximos Passos

1. ✅ Confirmar se store.id: 1161 é compartilhado ou específico
2. ⏳ Verificar se sites têm páginas próprias de imóveis
3. ⏳ Monitorar requisições de rede ao navegar em imóveis
4. ⏳ Decidir: 1 scraper genérico ou 30 individuais?

