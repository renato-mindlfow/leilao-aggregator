# CONCLUSÃO DA INVESTIGAÇÃO: Sites têm inventário próprio ou são agregadores?

## Análise Realizada

### 1. Lance no Leilão (lancenoleilao.com.br)
- **URL /imoveis:** Retorna 404
- **HTML:** Não encontrou indicadores de API Superbid no HTML estático
- **Sistema:** Parece ser sistema próprio (PHP - pesquisa.php)
- **Conclusão:** Sistema próprio, mas pode ser white-label

### 2. Freitas Leiloeiro (freitasleiloeiro.com.br)
- **Sistema:** Próprio (ASP.NET MVC)
- **API própria:** `/Leiloes/ListarLeiloes`, `/Leiloes/PesquisarDestaques`
- **Carousel de imóveis:** `_CarouselImoveis.html` (carrega via XHR)
- **Conclusão:** Sistema próprio com inventário próprio

## Descoberta Crítica

### Todos os 9 sites testados retornam:
- **store.id: 1161** na API Superbid
- **11.475 imóveis** (filtrado de 46.903 totais)

### Mas:
- **Freitas Leiloeiro** NÃO usa API Superbid - tem sistema próprio
- **Lance no Leilão** também parece ter sistema próprio

## Hipóteses Finais

### Hipótese 1: MISTO
- Alguns sites são agregadores (usam store.id: 1161)
- Outros têm sistema próprio (Freitas, Lance no Leilão)
- Precisam ser configurados individualmente

### Hipótese 2: White-label com API própria
- Sites podem ser white-label mas com APIs próprias
- store.id: 1161 pode ser um catálogo agregado compartilhado
- Cada site pode ter seu próprio store.id, mas não está sendo usado na busca

## Recomendação Final

**OPÇÃO RECOMENDADA: Configuração Híbrida**

1. **Sites com API Superbid (store.id: 1161):**
   - Configurar como agregadores
   - Usar 1 scraper genérico para store.id: 1161
   - Sites: Superbid, LUT, Big Leilão, Via Leilões, etc.

2. **Sites com sistema próprio:**
   - Configurar individualmente
   - Usar scraping HTML ou API própria
   - Sites: Freitas Leiloeiro, Lance no Leilão (e outros que não usam Superbid)

3. **Validação necessária:**
   - Testar cada site individualmente
   - Verificar se realmente têm inventário próprio
   - Ou se são apenas agregadores com store.id: 1161

## Próximos Passos

1. ✅ Confirmar que store.id: 1161 é compartilhado
2. ⏳ Identificar quais sites têm sistema próprio
3. ⏳ Para sites próprios: descobrir como acessar imóveis
4. ⏳ Decidir: scraper genérico ou individuais?

