# SISTEMA DE ALERTAS LEILOHUB

## Alertas Criticos

1. **Nenhum scraper funcionando**
   - Condicao: 0 scrapers com status=success ha 24h
   - Acao: Notificar imediatamente

2. **Banco de dados inacessivel**
   - Condicao: Erro de conexao
   - Acao: Notificar imediatamente

3. **Queda brusca de imoveis**
   - Condicao: Reducao maior que 50 porcento em 24h
   - Acao: Notificar para investigacao

## Alertas de Aviso

1. **Taxa de erro alta**
   - Condicao: Mais de 50 porcento dos scrapers com erro
   - Acao: Notificar diariamente

2. **Scrapers desatualizados**
   - Condicao: Nao rodaram ha 7+ dias
   - Acao: Notificar semanalmente

3. **Qualidade baixa**
   - Condicao: Menos de 90 porcento dos imoveis com dados completos
   - Acao: Notificar semanalmente

## Implementacao

### Email
- Usar SendGrid ou similar
- Configurar em secrets: SENDGRID_API_KEY, ALERT_EMAIL

### Webhook
- Enviar para Slack/Discord
- Configurar em secrets: WEBHOOK_URL

### Exemplo de uso

```python
from app.services.alerts import send_alert

await send_alert(
    level='critical',
    title='Nenhum scraper funcionando',
    message='0 scrapers com success nas ultimas 24h',
    data={'last_check': datetime.now()}
)
```
