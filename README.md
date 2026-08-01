# ComparaAI

Comparador de preços de eletrodomésticos — Fase 1 (MVP): geladeiras, dados
mockados, rodando localmente. Nome provisório (placeholder), ver seção
"Nome do projeto" do brief original.

**Status: MVP completo (Passos 1-8 do brief original) + Fase 2 iniciada**
(atualização automática de preços) — busca com autocomplete, resultados
com filtros, página de produto com comparação de preços e histórico,
painel admin, microinterações e skeleton loading, e um pipeline real de
atualização automática de preço (JSON-LD + Groq como fallback), já
testado contra uma página real de e-commerce.

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

## Página de produto (Passo 6)

`/produto/<slug>` deixou de ser stub — `app/services/pricing.py` (novo,
separado de `search.py` de propósito: search.py acha produtos, pricing.py
formata preço/histórico de UM produto já achado):

- **Especificações**: `formatar_especificacoes()` traduz o JSON livre de
  `Product.specs` em rótulos em português — mapeamento fixo pra geladeira
  (Fase 1); categoria nova vai precisar do próprio mapeamento.
- **Tabela comparativa de preços**: uma linha por loja (mais barata
  primeiro, esgotadas por último), com ícone de loja física/online,
  "frete" honesto ("Retirada na loja" pra física, "Consulte o site" pra
  online — não inventa valor de frete que não existe), badge "Melhor" na
  oferta mais barata em estoque, "atualizado há X horas/dias"
  (`tempo_relativo()`, calculado em Python — não deixei conta de data
  solta no Jinja), e "Esgotado" no lugar do botão pra ofertas fora de
  estoque.
- **Gráfico de histórico** (Chart.js, `unpkg.com/chart.js@4`): uma linha
  por loja + uma linha "Média" mais grossa — o brief pede "por loja OU
  média" (seção 6.3); em vez de um toggle customizado, deixei tudo no
  mesmo gráfico e a legenda nativa do Chart.js já resolve isso (clica pra
  esconder/mostrar linha, inclusive dá pra isolar só a Média). Cores dos
  eixos/legenda lidas via `getComputedStyle` das CSS custom properties em
  vez de hex duplicado no JS — muda a paleta, o gráfico acompanha sozinho.
- **Produtos similares**: `produtos_similares()` em `search.py` — mesma
  categoria, ordenado por proximidade de preço (não é uma similaridade de
  especificação de verdade, documentado como aproximação).

Testado com curl + parse do JSON embutido no HTML (não só visual):
especificações renderizam com rótulo certo, "Esgotado" aparece na oferta
certa (Casas Bahia, um dos 4 casos esgotados do seed), badge "Melhor"
aparece exatamente 1 vez por página, produtos similares NUNCA incluem o
próprio produto, e os dados do gráfico têm 31 pontos (30 dias + hoje), 1
série por loja + a série de média com valores decrescentes (bate com a
narrativa "preço caindo" do seed).

## Microinterações e responsividade (Passo 7)

- **Botões**: hover levanta 1px, active "pressiona" (scale 0.97) — regra
  global em `input.css`, não repetida por componente. Cards de produto
  mantêm o próprio hover (mais forte: translateY maior + sombra), sem
  conflito com essa regra mais sutil.
- **Skeleton loading nos resultados** (brief seção 7: "não deixar tela em
  branco"): grid de cards cinza pulsando (`animate-pulse`) sobreposto
  (overlay absoluto, não empurra o layout) enquanto o HTMX busca —
  aparece/some via a classe `.htmx-request` que o próprio HTMX alterna
  (`hx-indicator`), sem JS escrito à mão.
- **Ícone de busca animado** (brief seção 7): lupa parada vira spinner
  girando enquanto o autocomplete busca. Achado real ao implementar: usar
  Alpine escutando `@htmx:beforeRequest` NÃO funciona — atributo HTML é
  sempre lowercased pelo parser do navegador, então nunca bate com o nome
  real do evento (`htmx:beforeRequest`, case-sensitive). Resolvido com CSS
  puro por cima da classe `.htmx-request` (mesmo mecanismo do skeleton),
  sem essa armadilha.
- `prefers-reduced-motion` desliga toda transição/animação pra quem
  configurou isso no SO/navegador.

## Painel admin (Passo 8)

`/admin/precos` — **sem autenticação de propósito** (brief seção 6.4 é
explícito: "não precisa de auth ainda"), simula o fluxo que uma loja
física parceira vai usar no futuro pra atualizar o próprio preço. Um
`<form>` por oferta (produto+loja), preço + em-estoque editáveis, "Salvar"
individual. Aceita preço digitado com vírgula OU ponto decimal
(`2799,90` ou `2799.90`) — usuário de loja física não deveria precisar
pensar em formato. Preço inválido mostra erro e não salva nada (testado).

**Limitação conhecida, documentada de propósito**: sem login, esta rota
fica acessível a qualquer um que souber a URL — aceitável só porque é
Fase 1/dado mockado; autenticação de verdade é pré-requisito antes de
qualquer dado real entrar aqui.

Testado de ponta a ponta com curl + sessão de cookies (não só assumido):
POST editando preço + desmarcando estoque → banco realmente atualizado
(`2629.90` → `2599.50`, `in_stock` True → False, `last_updated` com
timestamp novo); POST com preço inválido → flash de erro, banco
**intocado** (confirmado consultando o registro depois). Achado e
corrigido no caminho: `Model.query.get_or_404()` é API legada do
SQLAlchemy 2.0 (gera warning) — trocado por `db.get_or_404(Model, id)`,
o helper atual do Flask-SQLAlchemy 3.x.

## Atualização automática de preços (Fase 2, pedido explícito do usuário)

Decisão de produto do usuário, no meio da Fase 1: o painel admin (Passo 8)
deve ser só um recurso de **emergência**, não a fonte principal de preço —
preço e foto de verdade devem vir automaticamente das próprias lojas que o
site linka. `app/services/atualizacao_precos.py` implementa isso com uma
estratégia em 2 camadas:

1. **Dados estruturados (JSON-LD/schema.org) primeiro** — muita loja já
   publica um bloco `<script type="application/ld+json">` com
   `@type: Product` (preço, disponibilidade, imagem) pra SEO. Quando existe,
   é sempre preferível: instantâneo, de graça, sem IA nenhuma envolvida.
2. **Groq (LLM) como fallback**, só quando o site não publica esse schema.
   **Importante ser honesto sobre o que isso é**: a Groq sozinha NÃO navega
   na internet — é uma API de inferência sobre um modelo já treinado, sem
   acesso à web ao vivo por conta própria. O fluxo real é: este módulo busca
   a página via HTTP (`requests`, respeitando `robots.txt` antes de
   qualquer tentativa) e só DEPOIS manda o texto extraído pra Groq, que
   funciona como um "parser inteligente" — mais resistente a mudança de
   layout do site que um scraper de seletor CSS fixo, mas não substitui a
   busca em si.

### Testado contra uma página REAL (não só teoria)

Antes de escrever qualquer scraper "no escuro", chequei `robots.txt` das 6
lojas do seed:

| Loja | Resultado |
|---|---|
| Amazon | Permite (`/dp/...`) |
| Bemol | Permite (cita `ClaudeBot` explicitamente como bot permitido; bloqueia nomeadamente o `Amazonbot`) |
| Magazine Luiza | **Bloqueia até o próprio `robots.txt`** (403, proteção anti-bot Akamai) |
| Casas Bahia | **Bloqueia até o próprio `robots.txt`** (403) |

Com isso confirmado, testei o pipeline inteiro contra uma página REAL da
Bemol (achada via sitemap público:
`bemol.com.br/geladeira-consul-frost-free-300-litros-freezer-supercapacidade-branca-crb36ab/p`):

- Extração via JSON-LD funcionou de primeira — preço exato (R$ 2.449),
  sem precisar de nenhuma chamada à Groq.
- **Bug real encontrado e corrigido no processo**: a disponibilidade
  (`availability`) mora dentro da oferta INDIVIDUAL (`offers.offers[0]`),
  não no nível agregado (`AggregateOffer`) — minha primeira versão lia do
  nível errado e todo produto aparecia "em estoque" mesmo quando a página
  dizia `OutOfStock`. Confirmado comparando duas leituras da mesma página
  ao vivo antes de fechar o fix.
- Depois do fix: `atualizar_oferta()` rodou contra a URL real, gravou
  `Price.price = 2449.00` e `Price.in_stock = False` (batendo exatamente
  com o que a página real mostrava), e criou um novo ponto em
  `PriceHistory` — confirmado consultando o banco depois, banco resetado
  pro estado limpo do seed em seguida.

### Como rodar

```powershell
# .env precisa ter GROQ_API_KEY preenchida (grátis em console.groq.com)
venv\Scripts\python.exe atualizar_precos.py
```

Pensado pra rodar 1x/dia via **Agendador de Tarefas do Windows**: Criar
Tarefa Básica → Diariamente → Ação "Iniciar um programa" → Programa:
`C:\caminho\pra\ComparaAI\venv\Scripts\python.exe` → Argumentos:
`atualizar_precos.py` → "Iniciar em": `C:\caminho\pra\ComparaAI`.

### Limitação importante, honesta

**As URLs do seed (`Price.url`) são placeholders fictícios** (ex:
`amazon.com.br/produto/<slug>`, que não existe de verdade) — o pipeline
não vai achar nada útil rodando contra o banco de demonstração como está.
Pra virar útil de verdade, `Price.url` de cada oferta precisa apontar pra
uma página REAL de produto na loja certa (manual, uma vez por produto/
loja — não tem como automatizar ESSA parte, é decisão de negócio "qual
produto de qual loja corresponde a qual produto nosso").

Continua valendo o que já dizia o brief original: scraping esbarra em
Termos de Uso de muitos e-commerces (Magazine Luiza/Casas Bahia bloqueiam
ativamente, confirmado acima); a fonte mais estável e sem risco legal pra
escalar isso de verdade continua sendo um programa de afiliados oficial
(Amazon Associates, Awin, Lomadee) — esse pipeline aqui é o caminho pra
lojas que não tiverem isso disponível (ex: Bemol/lojas físicas locais
com site próprio).

## Estrutura

Ver `prompt-claude-code-comparador-precos.md` (brief original) pra escopo
completo, modelagem de dados e ordem de implementação. Resumo da estrutura
de pastas:

```
app/
├── routes/       # blueprints: main (home/busca), product (detalhe), admin (edição manual)
├── services/     # search (busca/filtros/similares), pricing (specs/histórico/tempo relativo),
│                 # seed_data (dados mockados), atualizacao_precos (Fase 2: JSON-LD + Groq)
├── static/       # css (input.css fonte, tailwind.css compilado), js, img
├── templates/    # Jinja2 (components/ pra partials reutilizáveis)
├── models.py     # Category, Product, Store, Price, PriceHistory
└── __init__.py   # app factory
migrations/       # Flask-Migrate/Alembic — versionado (é o histórico real do schema)
tools/
└── tailwindcss.exe   # CLI standalone do Tailwind (~110MB, gitignored — ver "Como rodar")
config.py
run.py
seed.py             # popula o banco com dados mockados (Fase 1)
atualizar_precos.py # atualização automática de preço (Fase 2, ver seção acima)
requirements.txt
.env                # GROQ_API_KEY, SECRET_KEY, DATABASE_URL — gitignored, nunca versionado
```

## Passos já feitos / próximos (ver brief original, seção 9)

- [x] 1. Setup do projeto Flask + estrutura de pastas + config do Tailwind
- [x] 2. Modelos de banco (`models.py`) + script de seed com dados mockados
- [x] 3. Layout base (`base.html`) com navbar, footer, sistema de cores/tipografia
- [x] 4. Home page com busca
- [x] 5. Rota e template de resultados de busca + filtros
- [x] 6. Página de produto com tabela comparativa e gráfico de histórico
- [x] 7. Ajustes finos de responsividade e microinterações
- [x] 8. Painel admin simples de edição manual de preços
