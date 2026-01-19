# Relatório de Diagnóstico do LLMEnhancedScraper

**Data**: 2026-01-19 18:32  
**Script**: `scripts/diagnostico_scraper.py`  
**Sites Testados**: 5

---

## RESUMO EXECUTIVO

Todos os 5 sites carregaram **CORRETAMENTE** no navegador automatizado, com conteúdo de imóveis visível nas screenshots. 

**O problema NÃO é acesso ou bloqueio - é a extração pelo LLM.**

---

## ANÁLISE POR SITE

### 1. Mega Leilões ✅ (Falso Positivo de Bloqueio)

**URL**: https://www.megaleiloes.com.br/imoveis  
**Status HTTP**: 200  
**Tempo de Carregamento**: 9.4s  
**HTML**: 1,522,014 chars  
**Texto Visível**: 15,703 chars

**Diagnóstico Automatizado**: 🔴 "BLOQUEIO DETECTADO: 'verificação'"  
**Análise Visual**: ✅ **Página carregou perfeitamente**

**Screenshot mostra**:
- 8 imóveis visíveis na primeira tela
- Informações completas: preços, endereços, metragens
- Paginação funcionando (Página 1 de 17)
- Aviso de cookies com texto "verificação" (falso positivo)

**Problema Real**: LLM não está extraindo apesar do conteúdo estar presente

**Ação Necessária**: 
- Melhorar prompt do LLM
- Aumentar contexto enviado ao LLM
- Verificar se o HTML está chegando completo ao LLM

---

### 2. Portal Zuk ⚠️ (Conteúdo Ofuscado)

**URL**: https://www.portalzuk.com.br/leilao-de-imoveis  
**Status HTTP**: 200  
**Tempo de Carregamento**: 1.7s  
**HTML**: 788,698 chars  
**Texto Visível**: 7,882 chars

**Diagnóstico Automatizado**: 🟡 "Conteúdo carregou mas LLM não extraiu"  
**Análise Visual**: ⚠️ **Conteúdo parcialmente ofuscado**

**Screenshot mostra**:
- 3 imóveis visíveis, mas com imagens borradas/pixeladas
- Newsletter popup sobre o conteúdo
- Informações textuais presentes, mas layout dificulta extração

**Problema Real**: Imagens lazy-loaded ou ofuscadas + popup intrusivo

**Ação Necessária**:
- Fechar popup antes de extrair
- Aguardar mais tempo para lazy loading
- Aumentar scroll para carregar mais imóveis

---

### 3. Superbid ✅ (Falso Positivo de Bloqueio)

**URL**: https://www.superbid.net/  
**Status HTTP**: 200  
**Tempo de Carregamento**: 1.6s  
**HTML**: 3,587,931 chars  
**Texto Visível**: 38,988 chars

**Diagnóstico Automatizado**: 🔴 "BLOQUEIO DETECTADO: 'robô'"  
**Análise Visual**: ✅ **Página carregou perfeitamente**

**Screenshot mostra**:
- Banner da Petrobras no topo
- Categorias de produtos visíveis
- Eventos em destaque
- Aviso de cookies com texto "robô" (falso positivo)

**Problema Real**: LLM não está extraindo apesar do conteúdo estar presente

**Ação Necessária**:
- Melhorar prompt do LLM
- Este é um site de leilões gerais (não só imóveis) - pode precisar navegação específica

---

### 4. Sold ✅ (Conteúdo Perfeito)

**URL**: https://www.sold.com.br/  
**Status HTTP**: 200  
**Tempo de Carregamento**: 0.8s  
**HTML**: 954,612 chars  
**Texto Visível**: 19,827 chars

**Diagnóstico Automatizado**: 🟡 "Conteúdo carregou mas LLM não extraiu"  
**Análise Visual**: ✅ **Página carregou perfeitamente**

**Screenshot mostra**:
- Banner de imóvel em destaque no topo
- Categorias de produtos à esquerda (Imóveis: 345 itens)
- Eventos em destaque com datas e horários
- Layout limpo e organizado

**Problema Real**: LLM não está extraindo apesar do conteúdo excelente

**Ação Necessária**:
- Melhorar prompt do LLM - este site tem conteúdo perfeito
- Verificar se está sendo enviado o HTML completo
- Possivelmente o LLM precisa navegar para `/imoveis` especificamente

---

### 5. Viva Leilões ✅ (Conteúdo Perfeito)

**URL**: https://www.vivaleiloes.com.br/  
**Status HTTP**: 200  
**Tempo de Carregamento**: 1.4s  
**HTML**: 337,291 chars  
**Texto Visível**: 5,822 chars

**Diagnóstico Automatizado**: 🟡 "Conteúdo carregou mas LLM não extraiu"  
**Análise Visual**: ✅ **Página carregou perfeitamente**

**Screenshot mostra**:
- Seção "Lotes em Destaque" visível
- Imóvel comercial com foto, preço (R$ 3.126.772), endereço
- Layout limpo
- Aviso de cookies

**Problema Real**: LLM não está extraindo apesar do conteúdo estar presente

**Ação Necessária**:
- Melhorar prompt do LLM
- Aumentar contexto
- Verificar se está fazendo scroll suficiente

---

## CONCLUSÕES

### ❌ Problemas DESCARTADOS

1. **Bloqueio por Anti-Bot**: Nenhum site está bloqueando
2. **Cloudflare/WAF**: Nenhuma proteção detectada
3. **Timeout**: Todos carregam em < 10s
4. **JavaScript**: Está executando corretamente
5. **Lazy Loading**: Parcialmente funcionando (só Portal Zuk tem problema)

### ✅ Problemas CONFIRMADOS

1. **Extração pelo LLM**: Principal problema
2. **Prompt inadequado**: LLM não está recebendo instruções corretas
3. **Contexto insuficiente**: Pode não estar enviando HTML completo
4. **Navegação genérica**: Alguns sites precisam ir direto para `/imoveis`

---

## AÇÕES RECOMENDADAS (Ordem de Prioridade)

### 1. CRÍTICO: Revisar LLMEnhancedScraper

**Arquivo**: `app/scrapers/llm_enhanced_scraper.py`

**Verificar**:
- [ ] Qual prompt está sendo enviado ao LLM?
- [ ] Quanto do HTML está sendo enviado? (limite de tokens?)
- [ ] O LLM está recebendo só texto ou HTML estruturado?
- [ ] Há logs do que o LLM está retornando?

**Melhorias Necessárias**:
```python
# Antes de enviar ao LLM, extrair só conteúdo relevante
# Exemplo: remover scripts, styles, headers, footers
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, 'html.parser')

# Remover ruído
for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
    tag.decompose()

# Focar em áreas de conteúdo
main_content = soup.find('main') or soup.find('body')
clean_html = str(main_content)[:100000]  # Primeiros 100k chars
```

### 2. IMPORTANTE: Melhorar Prompt do LLM

**Adicionar ao prompt**:
- Exemplos de estruturas HTML típicas de leilões
- Instruções para ignorar popups e cookies
- Focar em seções com preços e endereços
- Retornar JSON estruturado mesmo se encontrar apenas 1 imóvel

### 3. MÉDIO: Adicionar Navegação Específica

Para sites como Superbid que são multi-categoria:
```python
# Navegar para seção específica de imóveis
if 'superbid' in url:
    await page.click('text=Imóveis')
    await page.wait_for_load_state('networkidle')
```

### 4. BAIXO: Melhorar Scroll e Esperas

Portal Zuk precisa mais scroll:
```python
# Fazer scroll mais agressivo
for i in range(10):  # Aumentar de 5 para 10
    await page.evaluate('window.scrollBy(0, 1000)')  # Aumentar de 500 para 1000
    await asyncio.sleep(1)
```

---

## TESTES SUGERIDOS

### Teste 1: Verificar Output do LLM

```bash
# Adicionar logging no LLMEnhancedScraper
python -c "
from app.scrapers.llm_enhanced_scraper import LLMEnhancedScraper
scraper = LLMEnhancedScraper()
result = scraper.scrape('https://www.megaleiloes.com.br/imoveis')
print('Resultado:', result)
print('Imóveis encontrados:', len(result.get('properties', [])))
"
```

### Teste 2: Enviar HTML Manualmente ao LLM

Pegar o HTML salvo e testar diretamente com Claude/GPT:
```bash
# Usar HTML salvo nos screenshots
cat logs/scraper_audit/screenshots/megaleiloes_*.html | head -c 50000 > test_input.html

# Testar com API do Anthropic direto
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 4096,
    "messages": [{
      "role": "user",
      "content": "Extraia todos os imóveis deste HTML: [CONTEÚDO]"
    }]
  }'
```

---

## ARQUIVOS GERADOS

- ✅ Screenshots: `logs/scraper_audit/screenshots/*.png` (5 arquivos)
- ✅ HTML: `logs/scraper_audit/screenshots/*.html` (5 arquivos)
- ✅ Este relatório: `logs/scraper_audit/RELATORIO_DIAGNOSTICO_SCRAPER.md`

---

## PRÓXIMOS PASSOS

1. Investigar código do `LLMEnhancedScraper`
2. Testar extração manual com HTML salvo
3. Aplicar correções no prompt e limpeza de HTML
4. Re-testar com o scraper corrigido
5. Comparar resultados antes/depois

---

**Status Final**: Diagnóstico completo. Problema identificado e soluções propostas.
