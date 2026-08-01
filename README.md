# ComparaAI

Comparador de preços de eletrodomésticos — Fase 1 (MVP): geladeiras, dados
mockados, rodando localmente. Nome provisório (placeholder), ver seção
"Nome do projeto" do brief original.

**Status: Passo 5 concluído** (página de resultados + filtros + ordenação).
Próximo passo: página de produto (tabela comparativa + gráfico de histórico).

## Stack

- Backend: Python + Flask + Flask-SQLAlchemy + Flask-Migrate
- Banco: SQLite em desenvolvimento (troca pra Postgres via `DATABASE_URL`,
  sem tocar em código — abstração do SQLAlchemy)
- CSS: Tailwind CSS v4, via **CLI standalone** (`tools/tailwindcss.exe`,
  binário baixado direto do GitHub releases) — **sem Node.js/npm**, de
  propósito, pra manter tudo num codebase Python só (mesma justificativa do
  brief original: fácil de deployar numa VPS sem gerenciar frontend
  separado).
- Interatividade: HTMX + Alpine.js, via CDN (carregados em `base.html` desde
  o Passo 3 — menu mobile do navbar já usa Alpine; busca dinâmica com HTMX
  vem no Passo 4/5).

## Como rodar

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# baixe o Tailwind CLI standalone (~110MB, não versionado no git — ver .gitignore)
Invoke-WebRequest -Uri "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe" -OutFile "tools\tailwindcss.exe"

python run.py
```

Acesse http://127.0.0.1:5100/ — **porta 5100** (não 5000/5050/8080) de
propósito, pra não conflitar com outros projetos locais (BreakTest já usa
5050 nesta máquina).

## Rebuildar o CSS depois de mexer em `app/static/css/input.css`

```powershell
.\tools\tailwindcss.exe -i app\static\css\input.css -o app\static\css\tailwind.css
```

Adicione `--watch` durante desenvolvimento pra recompilar sozinho a cada
mudança de template/CSS.

## Paleta e tipografia (definidas em `app/static/css/input.css`, bloco `@theme`)

Tailwind v4 usa config **CSS-first** (sem `tailwind.config.js`) — os tokens
customizados (`--color-base`, `--color-accent`, etc.) ficam direto no
`@theme` do `input.css` e geram as classes utilitárias automaticamente
(`bg-accent`, `text-ink-muted`, `font-display`...).

- **Base escura/sofisticada** (grafite azulado, tipo Linear.app):
  `--color-base` / `--color-surface` / `--color-elevated`.
- **Um acento vibrante só** (verde-lima, "economia/oferta"):
  `--color-accent` — usado em CTAs e badge de "melhor preço".
- **Contraste verificado** (fórmula de luminância relativa WCAG) antes de
  fechar os tons — ver comentário no próprio `input.css`.
- Fontes: **Space Grotesk** (`font-display`, títulos) + **Inter**
  (`font-body`, corpo de texto), via Google Fonts.

## Banco de dados e seed

Modelos em `app/models.py`: `Category` → `Product` → `Price` (preço ATUAL
por par produto+loja) + `PriceHistory` (série temporal, independente de
`Price` — alimenta o gráfico mesmo se uma loja parar de vender o produto).
Migrations via Flask-Migrate (`migrations/`), banco SQLite versionado
localmente (`comparaai.db`, gitignored).

```powershell
flask db upgrade      # aplica as migrations (cria as tabelas)
python seed.py        # zera e repopula com dados mockados
```

`seed.py` gera (dados em `app/services/seed_data.py`, preços calculados
por código a partir de um preço-base + variação por loja, não digitados um
a um):
- 4 categorias (só **Geladeiras** ativa; Fogões/Lava-louças/Micro-ondas
  como "em breve", sem produtos)
- 6 lojas: 4 online (Amazon, Magazine Luiza, Casas Bahia, Loja Oficial da
  Marca) + 2 físicas em Manaus (Bemol, Eletro Norte)
- 10 geladeiras (Electrolux, Brastemp, Consul, Samsung, LG), cada uma com
  3-5 ofertas de lojas diferentes — **todo produto tem garantidamente
  pelo menos 1 opção física**, o diferencial central do produto
- Histórico de preço: 31 pontos (últimos 30 dias + hoje) por oferta
  produto+loja, caminho aleatório suave com leve tendência de queda —
  bom material pro gráfico do Passo 6

## Layout base (navbar, footer, tipografia)

`app/templates/base.html` é o shell de toda página (título/meta description
por `{% block %}`, pensando em SEO — brief seção 8). Inclui
`components/navbar.html` e `components/footer.html`, os dois **data-driven**
(consultam `Category` de verdade via um `context_processor` em
`app/__init__.py` — `categorias_nav` — em vez de ter "Geladeiras/Fogões/..."
hardcoded nos templates; categoria nova no banco aparece sozinha).

- Navbar: sticky, categoria ativa (Geladeiras) clicável, as "em breve" com
  selo e sem link. Mobile: menu hamburguer com Alpine.js (`x-data`/`x-show`,
  sem nenhum JS próprio escrito à mão).
- Footer: marca, lista de categorias, texto "sobre", ano dinâmico.
- `_setup_check.html` (temporário) agora estende `base.html` e demonstra a
  escala de cor/tipografia (cartão de produto, badges, hierarquia de texto)
  — some no Passo 4 quando a home de verdade entrar.

## Home page + busca (Passo 4)

- **Hero + busca central** com autocomplete via HTMX (`/busca/sugestoes`,
  `app/services/search.py`): digita 2+ letras, aparece dropdown com
  produtos batendo — sem recarregar a página.
- **Busca funciona por nome genérico ("geladeira") E por marca/modelo
  específico** ("Samsung", "RT46") — o brief pede isso explicitamente
  (seção 6.2). Achado um bug real testando: "geladeira" não aparece em
  NENHUM `Product.name/brand/model` (é nome da categoria, não do
  produto) — corrigido com um `join(Category)` na busca.
- **Categorias em destaque**: Geladeiras clicável (leva pra busca),
  Fogões/Lava-louças/Micro-ondas com selo "em breve" — ícones via Lucide
  (CDN, `<i data-lucide="...">` + `lucide.createIcons()`, também
  re-chamado depois de todo swap do HTMX pra ícone injetado dinamicamente
  não ficar sem renderizar).
- **"Mais buscados"**: grid de cards de produto (`components/
  product_card.html`, macro Jinja reutilizável — mesmo card volta no
  Passo 5). Sem foto de produto real ainda (Fase 1) — ícone genérico de
  geladeira no lugar de `<img>` quebrada.
- **3 blocos de proposta de valor**, como pedido.
- **Stubs temporários** `/busca` e `/produto/<slug>` — só pra clicar em
  qualquer busca/card da home não cair num 404 antes dos Passos 5/6
  existirem de verdade. Ficam óbvios (dizem "Em construção — Passo X").

## Página de resultados + filtros (Passo 5)

`/busca` deixou de ser stub — filtros de verdade em `app/services/search.py`
(`filtrar_produtos`): marca, faixa de preço, capacidade (litros), frost
free, tipo de loja (online/física) + ordenação (mais relevante/menor
preço/maior preço), tudo combinável ao mesmo tempo.

- **Um `<form>` só** (`resultados.html`) envolve filtros E ordenação —
  qualquer mudança (`hx-trigger="change"`) dispara `hx-get` pro HTMX, que
  troca só `#resultados-conteudo` (contador + grid), sem recarregar
  navbar/footer. `hx-push-url="true"` mantém a URL compartilhável/com
  botão voltar funcionando.
- **A mesma rota serve dois formatos**: página inteira (`resultados.html`)
  em navegação direta, ou só o fragmento (`components/
  _resultados_conteudo.html`) quando detecta o header `HX-Request` —
  clássico padrão de progressive enhancement do HTMX, testado nos dois
  casos (fragmento confirmado sem nenhum `<nav>`/`<html>`/`<footer>`
  vazando).
- Marca/tipo de loja filtram no banco (colunas reais); capacidade/frost
  free filtram em Python depois de buscar — `specs` é JSON, e extrair
  isso via SQL muda de sintaxe entre SQLite/Postgres (o projeto quer
  trocar de banco sem dor de cabeça, ver `config.py`).
- Filtro de marca é **data-driven** (`listar_marcas_disponiveis()`), não
  hardcoded — mesmo princípio já usado nas categorias do navbar.
- Card de produto reaproveitado do Passo 4 (`components/product_card.html`)
  sem nenhuma mudança — o brief pede exatamente a mesma informação nos
  dois lugares (imagem, nome, faixa de preço, badge "Melhor preço").
- Estado vazio cuidado: mensagem clara + link "Ver todas as geladeiras".

Testado com curl (não só assumido): 10 resultados pra "geladeira" (bate
com o total seedado), filtro por marca isola só os produtos certos,
`frost_free=nao` corretamente vazio (todo o seed é frost-free), 6
produtos com capacidade ≥450L (conferido a mão contra os specs), e
`ordenar=menor_preco` traz primeiro o produto realmente mais barato
(Consul CRB39, R$2.299 de base — o menor preço-base de todo o catálogo).

## Estrutura

Ver `prompt-claude-code-comparador-precos.md` (brief original) pra escopo
completo, modelagem de dados e ordem de implementação. Resumo da estrutura
de pastas:

```
app/
├── routes/       # blueprints (main, product, admin — este último ainda não existe)
├── services/     # lógica de busca/matching, seed de dados
├── static/       # css (input.css fonte, tailwind.css compilado), js, img
├── templates/    # Jinja2 (components/ pra partials reutilizáveis)
├── models.py     # Category, Product, Store, Price, PriceHistory (Passo 2)
└── __init__.py   # app factory
tools/
└── tailwindcss.exe   # CLI standalone do Tailwind (~110MB, gitignored — ver "Como rodar")
config.py
run.py
requirements.txt
```

## Passos já feitos / próximos (ver brief original, seção 9)

- [x] 1. Setup do projeto Flask + estrutura de pastas + config do Tailwind
- [x] 2. Modelos de banco (`models.py`) + script de seed com dados mockados
- [x] 3. Layout base (`base.html`) com navbar, footer, sistema de cores/tipografia
- [x] 4. Home page com busca
- [x] 5. Rota e template de resultados de busca + filtros
- [ ] 6. Página de produto com tabela comparativa e gráfico de histórico
- [ ] 7. Ajustes finos de responsividade e microinterações
- [ ] 8. Painel admin simples de edição manual de preços
