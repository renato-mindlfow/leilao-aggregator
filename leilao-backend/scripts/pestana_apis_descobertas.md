# APIs Descobertas - Pestana Leilões

## Resumo do Monitoramento de Rede

Durante o monitoramento das requisições de rede do site Pestana Leilões, foram identificadas as seguintes APIs e endpoints:

### APIs Identificadas

1. **API Principal**: `https://api.pestanaleiloes.com.br/sgl/v1/`
   - Base URL da API do Pestana Leilões

2. **Endpoints Encontrados**:
   - `GET https://api.pestanaleiloes.com.br/sgl/v1//leiloes/privados/ambientes/0`
     - Status: Requisição feita durante navegação
     - Observação: Retorna 404 quando acessado diretamente (pode requerer autenticação/cookies)
   
   - `GET https://api.pestanaleiloes.com.br/sgl/v1//enderecos/estados`
     - Status: Funcional (retorna lista de estados)
     - Content-Type: application/json
   
   - `GET https://api.pestanaleiloes.com.br/sgl/v1//arrematantes/cadastros/configuracoes`
     - Status: Funcional
     - Content-Type: application/json
   
   - `GET https://api.pestanaleiloes.com.br/sgl/v1//cadastros/tipo-comprovante-endereco`
     - Status: Funcional
     - Content-Type: application/json

3. **SignalR (WebSockets)**:
   - `GET https://api.pestanaleiloes.com.br/sgl/v1/signalr/signalr/negotiate`
     - Protocolo: SignalR 1.5
     - Hubs: `leilaohub`, `timehub`
     - Observação: **Os dados podem ser carregados via WebSocket em vez de REST API**

### Headers Necessários

Para acessar as APIs, os seguintes headers são necessários:

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: application/json, text/plain, */*
Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7
Referer: https://www.pestanaleiloes.com.br/procurar-bens?tipoBem=462&lotePage=1&loteQty=50
Origin: https://www.pestanaleiloes.com.br
```

### Observações Importantes

1. **Autenticação/Cookies**: As APIs que retornam dados de leilões podem requerer:
   - Cookies de sessão
   - Tokens de autenticação
   - Headers específicos de autenticação

2. **WebSockets**: O site usa SignalR, o que indica que os dados podem ser carregados dinamicamente via WebSocket após a conexão inicial.

3. **Endpoint de Leilões**: O endpoint `/leiloes/privados/ambientes/0` foi chamado durante a navegação, mas retorna 404 quando acessado diretamente. Isso sugere que:
   - Requer parâmetros adicionais
   - Requer autenticação/cookies de sessão
   - Pode ser acessado apenas após estabelecer conexão SignalR

### Recomendações

1. **Usar Playwright/Selenium**: Como os dados são carregados via JavaScript e possivelmente WebSockets, a melhor abordagem é usar um navegador real (já implementado no `PestanaScraper`).

2. **Interceptar WebSocket**: Se quiser acessar diretamente, seria necessário:
   - Estabelecer conexão SignalR
   - Interceptar mensagens WebSocket
   - Parsear dados recebidos

3. **Analisar JavaScript**: O arquivo `lotes.bf5c80a994cbb39326f7.chunk.js` contém a lógica de carregamento de dados. Analisar este arquivo pode revelar os endpoints exatos.

### Conclusão

**Não foi encontrada uma API REST pública que retorne JSON com dados de leilões diretamente.** O site usa:
- JavaScript para renderizar conteúdo
- Possivelmente WebSockets (SignalR) para carregar dados dinamicamente
- Autenticação/cookies para proteger endpoints

**A solução recomendada é usar o `PestanaScraper` com Playwright** (já implementado), que renderiza o JavaScript e captura os dados após o carregamento completo da página.

