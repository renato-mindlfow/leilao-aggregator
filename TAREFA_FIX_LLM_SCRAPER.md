# TAREFA: Corrigir Bugs no LLMEnhancedScraper

## CONTEXTO
O teste do LLMEnhancedScraper revelou 2 problemas:
1. Timeout em sites pesados (Mega Leilões)
2. AttributeError quando LLM retorna `null` em campos

## EXECUÇÃO AUTÔNOMA
Execute TODAS as correções sem parar para perguntar.

---

## FASE 1: Corrigir Tratamento de None no _normalize_property

Abrir `app/services/llm_enhanced_scraper.py` e corrigir o método `_normalize_property`:

**PROBLEMA:**
```python
'address': raw.get('endereco', '').strip(),  # Falha se retornar None
```

**SOLUÇÃO:**
Criar função helper para tratar None:

```python
def _safe_str(self, value: any, default: str = '') -> str:
    """Converte valor para string de forma segura, tratando None."""
    if value is None:
        return default
    return str(value).strip()

def _safe_float(self, value: any) -> Optional[float]:
    """Converte valor para float de forma segura."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            # Limpar formatação brasileira
            value = value.replace('.', '').replace(',', '.').replace('R$', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return None
```

Depois atualizar `_normalize_property` para usar essas funções:

```python
def _normalize_property(self, raw: Dict, url: str, auctioneer_id: str, auctioneer_name: str) -> Dict:
    """Normaliza dados extraídos para formato do banco."""
    
    # Normalizar categoria
    tipo = self._safe_str(raw.get('tipo_imovel')).lower()
    category_map = {
        'apartamento': 'Apartamento',
        'casa': 'Casa',
        'terreno': 'Terreno',
        'comercial': 'Comercial',
        'rural': 'Rural',
        'galpão': 'Comercial',
        'galpao': 'Comercial',
        'sala': 'Comercial',
        'loja': 'Comercial',
        'prédio': 'Comercial',
        'predio': 'Comercial',
    }
    category = category_map.get(tipo, 'Outro')
    
    # Normalizar estado
    state = self._safe_str(raw.get('estado')).upper()
    if len(state) != 2:
        state = 'XX'
    
    # Normalizar cidade (Title Case)
    city = self._safe_str(raw.get('cidade'))
    if city:
        city = city.title()
    
    # Normalizar título
    title = self._safe_str(raw.get('titulo'))
    if title:
        title = title.title()
    
    return {
        'title': title,
        'address': self._safe_str(raw.get('endereco')),
        'city': city,
        'state': state,
        'category': category,
        'area_total': self._safe_float(raw.get('area_m2')),
        'evaluation_value': self._safe_float(raw.get('valor_avaliacao')),
        'first_auction_value': self._safe_float(raw.get('valor_minimo')),
        'second_auction_value': self._safe_float(raw.get('valor_minimo')),
        'discount_percentage': self._safe_float(raw.get('desconto_percentual')),
        'first_auction_date': self._safe_str(raw.get('data_leilao')) or None,
        'auction_type': self._safe_str(raw.get('modalidade')) or 'Extrajudicial',
        'source_url': self._safe_str(raw.get('url_detalhes')) or url,
        'image_url': self._safe_str(raw.get('url_imagem')) or None,
        'auctioneer_id': auctioneer_id,
        'auctioneer_name': auctioneer_name,
        'source': 'llm_enhanced_scraper',
    }
```

---

## FASE 2: Aumentar Timeout e Melhorar Resiliência

Ajustar método `_fetch_page` para:
1. Aumentar timeout para 90 segundos
2. Usar 'domcontentloaded' ao invés de 'networkidle' (mais rápido)
3. Adicionar retry

```python
async def _fetch_page(self, url: str, wait_for_js: bool = True) -> str:
    """
    Busca página usando Playwright.
    Renderiza JavaScript e retorna HTML.
    """
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Usar domcontentloaded para ser mais rápido
            await self.page.goto(url, wait_until='domcontentloaded', timeout=90000)
            
            if wait_for_js:
                # Aguardar um pouco mais para JS carregar
                await asyncio.sleep(5)
                
                # Scroll para carregar lazy content
                try:
                    await self.page.evaluate("""
                        async () => {
                            await new Promise((resolve) => {
                                let totalHeight = 0;
                                const distance = 300;
                                const timer = setInterval(() => {
                                    window.scrollBy(0, distance);
                                    totalHeight += distance;
                                    if (totalHeight >= document.body.scrollHeight || totalHeight > 5000) {
                                        clearInterval(timer);
                                        resolve();
                                    }
                                }, 100);
                                setTimeout(resolve, 3000);  // Max 3s scroll
                            });
                        }
                    """)
                except Exception as e:
                    logger.debug(f"Erro no scroll: {e}")
                    
                await asyncio.sleep(2)
            
            html = await self.page.content()
            
            if html and len(html) > 500:
                return html
            
            logger.warning(f"Tentativa {attempt+1}: HTML muito pequeno ({len(html)} chars)")
            
        except Exception as e:
            logger.warning(f"Tentativa {attempt+1} falhou: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
    
    return ""
```

---

## FASE 3: Ajustar Lista de Teste

Alguns sites são muito pesados. Ajustar `scripts/testar_llm_enhanced.py` para usar URLs mais leves:

```python
LEILOEIROS_TESTE = [
    # Sites mais leves primeiro
    {"url": "https://www.portalzukerman.com.br/busca?categoriaId=1", "id": "portalzuk", "name": "Portal Zukerman"},
    {"url": "https://www.sold.com.br/leiloes?categoria=imoveis", "id": "sold", "name": "Sold Leilões"},
    {"url": "https://www.flexleiloes.com.br/auctions?property_type=imovel", "id": "flexleiloes", "name": "Flex Leilões"},
    {"url": "https://www.vivaleiloes.com.br/busca?tipoBem=1", "id": "vivaleiloes", "name": "Viva Leilões"},
    {"url": "https://www.lancejudicial.com.br/busca?tipo=imovel", "id": "lancejudicial", "name": "Lance Judicial"},
]
```

---

## FASE 4: Executar Teste Novamente

```bash
cd C:\LeiloHub\leilao-aggregator-git\leilao-backend
python scripts/testar_llm_enhanced.py
```

---

## FASE 5: Commit das Correções

```bash
git add app/services/llm_enhanced_scraper.py
git add scripts/testar_llm_enhanced.py
git commit -m "fix: Corrigir tratamento de None e timeout no LLMEnhancedScraper

- Adicionar _safe_str e _safe_float para tratar valores null do LLM
- Aumentar timeout para 90s
- Usar domcontentloaded ao invés de networkidle (mais rápido)
- Adicionar retry em caso de falha
- Ajustar lista de leiloeiros de teste"
git push
```

---

## CRITÉRIOS DE SUCESSO

- [ ] Nenhum AttributeError no teste
- [ ] Pelo menos 3/5 leiloeiros extraídos com sucesso
- [ ] Commit e push realizados
