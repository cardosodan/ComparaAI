# Prompt para Claude Code — Comparador de Preços de Eletrodomésticos

> Copie este documento inteiro e cole no Claude Code para iniciar o projeto.

---

## 1. Contexto e Visão do Produto

Quero construir um **comparador de preços de eletrodomésticos**, começando por geladeiras, que resolve o seguinte problema: quem quer comprar um eletrodoméstico perde muito tempo abrindo vários sites (Electrolux, Bemol, Amazon, Magazine Luiza, lojas físicas locais, etc.) para comparar preços manualmente.

O produto deve permitir que o usuário:
- Pesquise por categoria genérica ("geladeira") ou por modelo específico
- Veja, numa única tela, todas as opções disponíveis com preço, loja e link direto de compra
- Compare especificações lado a lado
- Acompanhe histórico de preço de um produto

**Visão de longo prazo (não implementar agora, só ter em mente na arquitetura):**
- Parcerias com lojas físicas da cidade para atualização manual/API de preços (não apenas e-commerce)
- Expansão para outras categorias além de linha branca
- Sistema de alertas de preço ("avise quando baixar de R$X")

**Nome do projeto:** [DEFINA_O_NOME] — use um placeholder tipo `ComparaAI` até decidirmos o nome final.

---

## 2. Escopo do MVP (Fase 1)

Foco: **UMA categoria (geladeiras)**, com **dados mockados/seed** (sem scraping real ainda), rodando localmente, com o fluxo completo de busca → comparação → detalhe do produto funcionando de ponta a ponta e com um visual premium.

Não incluir na Fase 1: scraping ao vivo, login de usuário, sistema de alertas, painel de parceiros físicos. Deixe a arquitetura pronta para esses recursos, mas não os implemente ainda.

---

## 3. Stack Técnica

- **Backend:** Python + Flask + SQLAlchemy (ORM)
- **Banco de dados:** SQLite na Fase 1 (fácil de trocar por PostgreSQL depois — usar SQLAlchemy para abstrair isso)
- **Frontend:** Jinja2 (templates do Flask) + TailwindCSS + Alpine.js (para interatividade leve: filtros, dropdowns, transições) + HTMX (para busca dinâmica sem recarregar página)
- **Gráficos:** Chart.js (para histórico de preço)
- **Ícones:** Lucide Icons (via CDN)
- **Fontes:** Google Fonts — sugestão: uma sans-serif moderna para corpo de texto (ex: Inter ou Manrope) + uma display mais expressiva para títulos (ex: Space Grotesk)

Justificativa: mantém tudo em um único codebase Python, fácil de deployar numa VPS, sem precisar gerenciar um frontend separado em Node — mas ainda assim entrega interatividade e visual moderno via HTMX/Alpine.

---

## 4. Estrutura de Pastas Sugerida

```
comparador/
├── app/
│   ├── __init__.py
│   ├── models.py          # Product, Store, Price, PriceHistory, Category
│   ├── routes/
│   │   ├── main.py        # home, busca, resultado
│   │   ├── product.py     # página de detalhe do produto
│   │   └── admin.py       # (fase futura) CRUD de lojas parceiras
│   ├── services/
│   │   ├── search.py      # lógica de busca/matching de produtos
│   │   └── seed_data.py   # gera dados mockados
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── resultados.html
│       ├── produto.html
│       └── components/    # cards, navbar, footer, filtros (partials reutilizáveis)
├── seed.py                 # script para popular o banco com dados de exemplo
├── config.py
├── requirements.txt
└── run.py
```

---

## 5. Modelagem de Dados

```python
Category
- id, name, slug (ex: "geladeiras"), icon

Product
- id, name, brand, model, category_id
- specs (JSON: capacidade em litros, frost free, cor, voltagem, dimensões, consumo kWh/mês)
- image_url
- slug

Store
- id, name, logo_url, website_url
- type (enum: "online" | "fisica")
- city (nullable, para lojas físicas)
- trust_score (opcional, futuro)

Price
- id, product_id (FK), store_id (FK)
- price (decimal)
- url (link direto do produto na loja)
- in_stock (boolean)
- last_updated (datetime)

PriceHistory
- id, product_id (FK), store_id (FK)
- price (decimal)
- recorded_at (datetime)
```

No `seed.py`, gere pelo menos 8-10 produtos de geladeira variados (marcas: Electrolux, Brastemp, Consul, Samsung, LG) com 3-5 preços cada, de lojas diferentes (misture "online" tipo Amazon/Magalu/site da marca com pelo menos uma loja "física" fictícia de Manaus, tipo Bemol), e gere histórico de preço fake dos últimos 30 dias (com pequenas variações) para alimentar o gráfico.

---

## 6. Funcionalidades e Telas

### 6.1 Home
- Hero section com headline forte + barra de busca central e grande (com autocomplete via HTMX, sugerindo produtos conforme digita)
- Categorias em destaque (mesmo que só "Geladeiras" esteja ativa, mostre outras como "em breve": fogões, lava-louças, micro-ondas)
- Seção "Mais buscados" com cards de produtos
- Seção explicando a proposta de valor (3 blocos: "Compare em segundos", "Preço real, sem enganação", "Loja online ou física, você escolhe")

### 6.2 Busca / Resultados
- Busca funciona tanto por nome genérico ("geladeira") quanto por marca/modelo específico
- Grid de cards de produtos, cada card mostrando: imagem, nome, faixa de preço (menor–maior encontrado), badge "Melhor preço" na loja mais barata
- Filtros laterais (ou top bar no mobile): marca, faixa de preço, capacidade (litros), frost free (sim/não), tipo de loja (online/física)
- Ordenação: menor preço, maior preço, mais relevante
- Estado vazio bem cuidado (nenhum resultado encontrado, com sugestão de busca similar)

### 6.3 Página de Produto
- Galeria/imagem do produto
- Especificações completas em tabela
- **Tabela comparativa de preços**: uma linha por loja, com logo da loja, preço, frete estimado (pode ser placeholder "consulte o site"), botão "Ver oferta" (linka pro site da loja), e badge de "atualizado há X horas"
- Gráfico de histórico de preço (Chart.js) dos últimos 30 dias, por loja ou média
- Produtos similares no rodapé

### 6.4 Painel Admin (estrutura básica, não precisa de auth ainda)
- Rota simples `/admin/precos` listando produtos e permitindo editar preço/loja manualmente — isso simula o fluxo que futuramente será usado pelas lojas físicas parceiras para atualizar preço

---

## 7. Diretrizes de Design (visual premium — isso é prioridade)

O site precisa parecer um produto de tecnologia sério, não um projeto de faculdade. Referências de nível: Booking.com (clareza de comparação), Linear.app (polimento visual), Kayak (UX de comparação de preços).

**Paleta:** escolha uma paleta escura/sofisticada como base (ex: tons de azul-petróleo ou grafite profundo) com UM tom de destaque vibrante para CTAs e badges de "melhor preço" (ex: verde-lima ou laranja vibrante, que remete a "economia"/"oferta"). Evite paleta genérica de tons pastéis de template pronto.

**Tipografia:** hierarquia clara, títulos grandes e confiantes, bom espaçamento (não amontoar). Números de preço em destaque, com peso de fonte forte.

**Componentes:**
- Cards de produto com leve sombra, hover com micro-elevação (translateY + shadow), transição suave (150-200ms)
- Skeleton loading nos cards enquanto HTMX busca resultados (não deixar tela em branco)
- Badge "Melhor preço" com destaque visual real, não um texto qualquer
- Barra de busca com foco visual bonito (ring de cor ao focar, ícone de busca animado)

**Responsividade:** mobile-first de verdade — a maioria dos usuários brasileiros vai acessar pelo celular. Teste os breakpoints principais.

**Dark mode:** se der tempo, ótimo, mas não é bloqueante pro MVP.

Use o skill de frontend-design se disponível para gerar tokens de design consistentes antes de codar os templates.

---

## 8. Considerações Técnicas Importantes

- **SEO:** páginas de produto devem ter title/meta description dinâmicos e URLs amigáveis (slug), pensando em tráfego orgânico de busca por "preço geladeira X" no futuro
- **Performance:** otimizar imagens, lazy loading nos cards fora da viewport
- **Sobre coleta de preço real (fase futura, não implementar agora):** ao migrar de dados mockados para preços reais, verifique os termos de uso e `robots.txt` de cada site antes de fazer scraping automatizado — muitos e-commerces proíbem isso explicitamente. Vale avaliar programas de afiliados oficiais (Amazon Associates, Awin, Lomadee) como fonte de dados mais estável e sem risco legal, complementando com parcerias diretas para lojas físicas (que é o diferencial real do produto).

---

## 9. Ordem de Implementação Sugerida

1. Setup do projeto Flask + estrutura de pastas + config do Tailwind
2. Modelos de banco (models.py) + script de seed com dados mockados
3. Layout base (base.html) com navbar, footer, sistema de cores/tipografia
4. Home page com busca
5. Rota e template de resultados de busca + filtros
6. Página de produto com tabela comparativa e gráfico de histórico
7. Ajustes finos de responsividade e microinterações
8. Painel admin simples de edição manual de preços

Comece pelo passo 1 e vá me mostrando o progresso a cada etapa antes de avançar para a próxima.
