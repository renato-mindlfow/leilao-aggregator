# Screenshots da Landing Page

Esta pasta contém os screenshots usados na landing page.

## Screenshots necessários:

1. **property-cards.png** - Screenshot da listagem de imóveis (cards)
   - Tamanho recomendado: 1920x1080px ou similar
   - Deve mostrar os cards de imóveis da plataforma

2. **hero-desktop.png** - Screenshot do hero da plataforma
   - Tamanho recomendado: 1920x1080px ou similar
   - Deve mostrar a interface principal

3. **admin-dashboard.png** - Screenshot do painel admin (opcional)
   - Tamanho recomendado: 1920x1080px ou similar

## Como adicionar:

1. Capturar screenshots da plataforma em https://leilohub.com.br
2. Salvar os arquivos nesta pasta (`public/landing/`)
3. Atualizar o componente `Landing.tsx` para usar as imagens reais

## Uso no código:

No arquivo `src/pages/Landing.tsx`, descomente as linhas que usam as imagens:

```tsx
<img 
  src="/landing/property-cards.png" 
  alt="LeiloHub - Listagem de Imóveis"
  className="w-full h-full object-cover"
/>
```

