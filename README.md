# ComparaAI

Comparador de preços de eletrodomésticos — Fase 1 (MVP): geladeiras, dados
mockados, rodando localmente. Nome provisório (placeholder), ver seção
"Nome do projeto" do brief original.

**Status: MVP completo (Passos 1-8 do brief original) + Fase 2 em
andamento** (atualização automática de preços) — busca com autocomplete,
resultados com filtros, página de produto com comparação de preços e
histórico, painel admin (com busca e toggle de estoque), microinterações e
skeleton loading, pipeline real de atualização automática de preço
(JSON-LD + Groq como fallback, testado contra e-commerce real), clique no
produto vai pra nossa página de comparação (com ofertas esgotadas
acinzentadas), e **8 dos 10 produtos já têm foto real** (achada no
catálogo público da Bemol).

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

# só necessário se for RODAR atualizacao_precos.py (script separado, não o
# site em si) — baixa o navegador do Playwright, ver seção "Playwright" abaixo
python -m playwright install chromium

python run.py
```

Acesse http://127.0.0.1:5100/ — **porta 5100** (não 5000/5050/8080) de
propósito, pra não conflitar com outros projetos locais (BreakTest já usa
5050 nesta máquina).

## Deploy (Railway)

**Por que não GitHub Pages**: Pages só serve arquivo estático (HTML/CSS/
JS) — o ComparaAI é uma aplicação Flask de verdade (rotas em Python,
banco via SQLAlchemy, HTMX dependendo de endpoint no servidor, painel
admin com POST, script de atualização de preço fazendo requisição pra
sites externos). Nada disso roda sem um servidor executando código
Python por trás.

**Por que Railway, não Render**: usuário já usa Render pra outro site
próprio — Railway resolve o mesmo problema (deploy direto do GitHub,
free tier, Postgres incluso) sem misturar com o outro projeto.
PythonAnywhere foi descartado: o free tier lá restringe requisição de
saída a uma lista branca de domínios, o que quebraria justamente o
script de atualização de preço (`atualizacao_precos.py`), que precisa
alcançar sites externos arbitrários (Bemol, Brastemp, Electrolux, etc.).

**Preparação já feita no projeto** (pra rodar puro `git push`/conectar o
repo, sem precisar mexer em mais nada):
- `Procfile` (`web: gunicorn run:app`) — Railway detecta automaticamente
  via Nixpacks a partir de `requirements.txt` + `Procfile`, sem
  configuração manual adicional.
- `gunicorn` (servidor WSGI de produção — `python run.py` sozinho usa o
  servidor de desenvolvimento do Flask, que não é seguro/eficiente pra
  produção) e `psycopg2-binary` (driver Postgres) adicionados ao
  `requirements.txt`.
- `config.py`: `DATABASE_URL` normaliza `postgres://` → `postgresql://`
  — o Postgres do Railway (herdado do Heroku) ainda entrega a URL no
  esquema antigo, que o SQLAlchemy 1.4+/2.0 rejeita sem essa troca.
- `app/static/css/tailwind.css` (a saída já COMPILADA do Tailwind) já
  está versionada no git — o binário `tools/tailwindcss.exe` é só uma
  ferramenta de desenvolvimento local (Windows), não precisa rodar (nem
  rodaria) no servidor Linux do Railway.
- **`playwright` não precisa do navegador instalado no Railway**: o site
  em si (o que o Railway serve) nunca chama Playwright — só o script
  separado `atualizacao_precos.py`/`atualizar_precos.py` usa, e esse
  continua rodando localmente (Windows Task Scheduler, ver seção
  própria), nunca no servidor. O pacote Python está no
  `requirements.txt` só porque `atualizacao_precos.py` faz `import` dele
  (lazy, dentro da função) — sem o binário do Chromium instalado, essa
  função específica simplesmente devolve `None` e o resto do site
  funciona normal.

**Passo a passo**:
1. Suba o repo pro GitHub (se ainda não estiver).
2. No [Railway](https://railway.app), "New Project" → "Deploy from GitHub
   repo" → escolha o repositório do ComparaAI.
3. Adicione um serviço **Postgres** ao mesmo projeto (Railway cria a
   variável `DATABASE_URL` sozinho, já injetada no serviço web).
4. Nas variáveis de ambiente do serviço web, configure `SECRET_KEY` (uma
   string aleatória qualquer) e, se quiser a atualização de preço via IA
   funcionando, `GROQ_API_KEY`.
5. Depois do primeiro deploy, rode UMA vez (aba "Shell" do Railway ou
   `railway run python seed.py` via CLI) `python seed.py` — cria as
   tabelas e popula o catálogo de demonstração. Sem isso o site sobe mas
   fica sem nenhum produto (banco vazio).

**Sobre persistência**: se preferir não usar Postgres (menos um serviço
pra configurar), a `DATABASE_URL` pode ficar vazia e o app cai de volta
pro SQLite local — mas o filesystem do Railway é efêmero por padrão
(reseta a cada novo deploy), então o banco SQLite se perderia a cada
deploy novo. Postgres (grátis dentro do free tier) evita esse problema;
é a opção recomendada aqui.

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

`/admin` (ver seção própria mais abaixo pra login — na época deste Passo
ainda não existia) simula o fluxo que uma loja física parceira vai usar
no futuro pra atualizar o próprio preço. Um `<form>` por oferta
(produto+loja), preço + em-estoque editáveis, "Salvar" individual. Aceita
preço digitado com vírgula OU ponto decimal (`2799,90` ou `2799.90`) —
usuário de loja física não deveria precisar pensar em formato. Preço
inválido mostra erro e não salva nada (testado).

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
estratégia em 3 camadas:

1. **Dados estruturados (JSON-LD/schema.org) primeiro** — muita loja já
   publica um bloco `<script type="application/ld+json">` com
   `@type: Product` (preço, disponibilidade, imagem) pra SEO. Quando existe,
   é sempre preferível: instantâneo, de graça, sem IA nenhuma envolvida.
2. **Playwright (navegador headless de verdade)**, quando o site não publica
   JSON-LD. Ver seção "Playwright" abaixo — resolve sites que só carregam
   preço via JavaScript, mas devolve `None` de propósito quando o site
   bloqueia automação de verdade (não tenta burlar proteção nenhuma).
3. **Groq (LLM) como último fallback**, quando nem JSON-LD nem Playwright
   acham nada. **Importante ser honesto sobre o que isso é**: a Groq sozinha
   NÃO navega na internet — é uma API de inferência sobre um modelo já
   treinado, sem acesso à web ao vivo por conta própria. O fluxo real é:
   este módulo busca a página via HTTP (`requests`, respeitando
   `robots.txt` antes de qualquer tentativa) e só DEPOIS manda o texto
   extraído pra Groq, que funciona como um "parser inteligente" — mais
   resistente a mudança de layout do site que um scraper de seletor CSS
   fixo, mas não substitui a busca em si.

### Playwright — resolve JS, nunca bloqueio (pedido do usuário)

Usuário perguntou se alguma IA/ferramenta resolvia URL+preço+estoque
mesmo nos sites que bloqueiam (Magazine Luiza, Casas Bahia). Distinção
importante que motivou essa seção: **JS-rendering não é a mesma coisa
que bloqueio ativo**, e só o primeiro tem solução legítima.

- **Samsung — resolvido de verdade**: o site não bloqueia nada, só
  carrega preço/estoque via chamada de API feita pelo JAVASCRIPT do
  navegador (por isso `requests`/curl nunca viam nenhum "R$" no HTML).
  Um Chromium headless comum (Playwright, sem NENHUM disfarce — não
  esconde `navigator.webdriver`, não spoofa fingerprint) renderiza a
  página igual um usuário normal e o preço aparece no texto visível.
  Testado ao vivo nos 2 produtos Samsung do seed: RT46 (RB50DG6020S9AZ)
  R$ 6.735,79 e RF50 (RF22R7351SR) R$ 26.137,00, ambos "Avise-me quando
  chegar" = esgotado — dado real, gravado em `seed_data.py`.
- **LG — testado, bloqueado de verdade, não insisti**: mesma tentativa
  com Playwright bateu em 403 via Akamai (a mesma categoria de proteção
  anti-bot que já bloqueava Magazine Luiza/Casas Bahia) — mesmo sem
  NENHUM disfarge no navegador. Curiosamente as requisições `requests`/
  curl simples usadas na descoberta inicial (achar a URL certa) não
  foram bloqueadas, só o Chromium automatizado foi — sinal de que o
  Akamai da LG mira especificamente fingerprint de navegador
  automatizado. **Decisão**: não tentei nenhuma técnica de evasão
  (stealth plugin, proxy, spoofing) pra furar isso — LG continua só com
  URL + imagem reais, preço/estoque simulados, mesmo estado de antes.
- **Magazine Luiza e Casas Bahia**: nem tentativa — já bloqueiam
  `requests` simples (ver tabela abaixo), Playwright não muda nada aí.

**Onde a linha foi traçada, de propósito**: existem técnicas reais pra
disfarçar automação como tráfego humano (plugins de stealth, rotação de
proxy residencial, resolução de CAPTCHA) — usadas por serviços
comerciais de scraping. Não implementei nenhuma delas aqui: um site que
configura proteção anti-bot deliberada está dizendo "não". Contornar
isso é uma zona cinzenta de Termos de Uso, na melhor das hipóteses, e um
scraper assim é inerentemente frágil (a loja detecta e bloqueia de novo,
loop sem fim). O caminho sustentável de verdade pra esses casos é um
programa de afiliados oficial (mesma conclusão do brief original) — a
Casas Bahia até tem um portal de desenvolvedor
(`developers.grupocasasbahia.com.br`), mas é uma API de MARKETPLACE
(pra vendedor cadastrar produto pra vender lá), não um feed de preços
pra site de comparação como o nosso.

**Rodando localmente**: `playwright` é dependência normal do
`requirements.txt`, mas o binário do navegador (Chromium) é baixado à
parte (~115MB, não fica no repositório) — depois de `pip install`, rodar
uma vez:
```powershell
python -m playwright install chromium
```

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

## Clique no produto vai pra nossa página de comparação + fotos reais

Dois pedidos do usuário, resolvidos juntos porque a mesma busca por
produtos reais (ver seção acima) resolve os dois:

- **`components/product_card.html`**: o clique no card inteiro vai pra
  nossa página interna (`product.detalhe`), com a tabela comparando o
  preço do mesmo modelo em várias lojas + gráfico de histórico.
  **Testado e depois revertido**: cheguei a mandar o clique principal
  DIRETO pra `produto.melhor_oferta.url` (a loja com o menor preço,
  `target="_blank"`), a pedido do usuário — mas só a oferta **Bemol** de
  cada produto tem URL real; as outras 5 lojas (Amazon, Magazine Luiza,
  Casas Bahia, Loja Oficial, Eletro Norte) usavam URL sintética
  (`{site_da_loja}/produto/{slug}`, nunca existiu de verdade), então
  clicar em qualquer card cuja melhor oferta fosse uma dessas batia numa
  página "não encontrada" real no site de destino. O usuário reportou
  "todos os links... aparecem não encontrado" e pediu pra reverter — o
  clique volta a ir pra nossa página, e é lá, na tabela por loja
  (Passo 6), que cada oferta individual tem seu próprio link "Ver oferta"
  pra fora. **A URL sintética foi removida na raiz** (`seed_data.py`
  passou a gravar `url=None` pra qualquer loja sem dado real extraído de
  verdade) — a tabela mostra "Link em breve" no lugar do botão quando não
  há URL confirmada, nunca mais um link que promete um destino
  inexistente. Ofertas esgotadas (`in_stock=False`) continuam com a linha
  inteira acinzentada (`opacity-50`) e "Esgotado" no lugar do botão — os
  dois estados (sem link / esgotado) são visualmente parecidos mas
  logicamente distintos, e não se confundem entre si porque só um dos
  dois pode ser verdade por vez pra cada oferta.
- **Fotos reais pra 8 dos 10 produtos**: usando a mesma técnica de achar
  produtos reais na Bemol (sitemap público + JSON-LD, ver seção acima),
  achei o equivalente mais próximo (capacidade/linha) pra Electrolux,
  Brastemp, Consul e Samsung — cada um ganhou foto real
  (`Product.image_url`) + o preço/estoque/URL da oferta Bemol trocado pelo
  dado real extraído (não mais gerado aleatoriamente). **LG ficou de fora
  de propósito** — não apareceu em ~80 sitemaps de produto verificados
  (a Bemol provavelmente não vende essa marca); os 2 produtos LG
  continuam com o ícone placeholder (nunca uma foto inventada/errada) e
  oferta Bemol fictícia como os outros já eram.
- `produto.html` (Passo 6) e `product_card.html` (Passos 4/5) agora
  mostram `<img>` de verdade quando `Product.image_url` existe, com
  fallback pro ícone genérico quando não existe — nunca uma imagem
  quebrada.

**Honestidade sobre o que "real" significa aqui**: são produtos
DIFERENTES (mas da mesma marca/capacidade aproximada) do nosso catálogo
mockado, não uma correspondência exata 1:1 — ex: nosso "Electrolux DF44"
virou o "DFN41" real mais parecido que a Bemol vende. E só a oferta
**Bemol** de cada produto é real; as outras lojas (Amazon, Magazine
Luiza, Casas Bahia, Loja Oficial, Eletro Norte) continuam com preço/URL
gerados, esperando o mesmo tipo de trabalho de correspondência manual
antes de virarem reais também.

## Ofertas sem link real: busca de apoio (e o erro que quase virou padrão)

Quando `Price.url` não existe (loja sem dado real extraído — hoje só a
Bemol tem, ver seção acima), a tabela de comparação (`produto.html`)
mostra "Ver na loja" em vez de "Ver oferta", apontando pra
`pricing.url_busca_de_apoio()`.

**Histórico do que deu errado antes de chegar nessa versão** (vale
registrar pra não repetir): a 1ª tentativa gerava uma URL de busca
"chutada" por loja (ex: `/s?q=`, `/busca/{q}/`) e validava só com
`curl` checando o STATUS HTTP. Isso se provou insuficiente de duas
formas diferentes:
1. **Casas Bahia** (`/s?q=`, chute por usar a mesma plataforma VTEX de
   Bemol/Brastemp/Consul): usuário testou no navegador e mandou print —
   página 404 real da Casas Bahia. Nunca funcionou; o bloqueio de bot
   (que já impedia validar via curl) escondia que o palpite também
   estava errado.
2. **Brastemp** (`/search?q=`): esse retornava HTTP 200 nos meus testes
   — mas investigando o CONTEÚDO da página (via WebFetch) depois do
   susto da Casas Bahia, a página real dizia "não encontramos nenhum
   resultado para 'search'": o nome do parâmetro de busca estava errado
   e a busca nunca rodava de verdade, mesmo com a página carregando sem
   erro nenhum. **Status 200 não é prova de que uma busca funciona**, só
   de que o servidor respondeu alguma coisa.

**Versão final, bem mais conservadora**: `_PADROES_BUSCA_POR_SITE` só
tem UMA entrada — Amazon (`/s?k={q}`), um formato de busca global,
extremamente estável, usado há mais de uma década em todos os países
(não é um chute novo pra esse projeto, diferente dos outros). Qualquer
outra loja (Magazine Luiza, Casas Bahia, Brastemp, Consul, Samsung, LG,
Electrolux) cai na **homepage real do site** — menos preciso (não entra
já com a busca pronta), mas nunca mais aponta pra um parâmetro errado ou
um caminho que não existe. `_SITE_OFICIAL_POR_MARCA` também corrige um
bug pré-existente: "Loja Oficial da Marca" sempre apontava pro site da
Electrolux mesmo pra produto Brastemp/Consul/Samsung/LG — agora cada
marca vai pro próprio site oficial de verdade.

`None` só quando a própria loja não tem site nenhum (Eletro Norte, loja
física fictícia sem `website_url`) — tabela mostra "Sem site" nesse caso.

## Links reais expandidos além da Bemol (Brastemp, Consul, Samsung, LG)

Usuário testou o link genérico ("Ver na loja") e comparou com o da Amazon
(que entra certinho na busca) — perguntou por que os outros só abrem a
homepage em vez do produto específico. Resposta: só a Bemol tinha dado
real até então. Perguntado se valia a pena repetir o mesmo trabalho de
achar produto real (sitemap + JSON-LD) pra mais lojas — usuário topou
tentar Brastemp/Consul/Samsung/LG.

`seed_data.py`: `bemol_real` (uma loja só) generalizado pra `lojas_reais`
(dict `{nome_da_loja: {...}}`, várias lojas por produto). Achados via
sitemap público de cada marca:
- **Brastemp e Consul** (mesma plataforma VTEX da Bemol): sitemap
  `/sitemap/product-N.xml` + JSON-LD deram URL + preço + estoque + foto
  REAIS pros 4 produtos (BRM44, BRE80, CRB39, CRM50) — mesmo modelo exato
  do nosso catálogo em 2 casos (BRM44, CRB39), aproximação por capacidade
  nos outros 2. Preço/estoque desses 4 na "Loja Oficial da Marca"
  refletem o que a página real dizia no momento da busca (a maioria
  "OutOfStock" — dado real, não escolha nossa).
- **Samsung e LG**: sitemap/busca achou a URL real do produto (RF22R7351SR
  501L pra RF50, GC-L247SLUV 601L — capacidade EXATA — pra GC-L, etc.),
  mas **essas duas não publicam preço/estoque em lugar estático nenhum**
  — confirmado checando o HTML bruto da página (nenhum `R$`, nenhum JSON-LD
  com `offers`): o preço só existe depois de uma chamada de API feita pelo
  JavaScript do navegador, invisível pra qualquer requisição HTTP simples
  (`requests`/`curl`/WebFetch, nenhum executa JS). Por isso essas 4
  entradas (RT46, RF50, GC-B, GC-L) só têm `url` (+ `imagem` via
  `og:image`, quando existe) — preço/estoque continuam simulados pra elas,
  já que inventar um valor e chamá-lo de "real" seria pior que não ter.
- `popular_produtos_e_precos()`: "Loja Oficial da Marca" agora entra
  GARANTIDA na seleção de lojas de um produto sempre que há dado real pra
  ela (mesma garantia que a Bemol já tinha) — preço/estoque usam o dado
  real quando presente, senão caem no mesmo simulado de qualquer loja sem
  dado real (decisão campo a campo, não tudo-ou-nada por loja).

**Amazon não foi tentada** — a busca (`/s?k=`) já resolve bem o caso de
uso sem precisar achar produto exato.

## Electrolux, Casas Bahia e Magazine Luiza — cobertura completa (todos os produtos, todas as lojas)

Usuário testou de novo e reportou 3 coisas: (1) Electrolux ainda só
abria a homepage — causa real: eu só tinha testado `www.electrolux.com.br`
(site institucional, sempre 503 em qualquer busca); a LOJA de verdade
fica em `loja.electrolux.com.br` (achada via WebSearch), mesma
plataforma VTEX de Bemol/Brastemp/Consul — mesmo modelo DFN41/IB7S já
usado pra Bemol, com preço/estoque reais (ambos InStock). (2) Casas
Bahia "ainda não mostra o produto específico, só abre o site deles" —
faltava dado real pra Casas Bahia em quase todos os produtos (só tinha
pro Electrolux DF44). (3) Pedido explícito: **"quero que todos os
produtos estejam com todos os links de todas as marcas funcionando"**.

**Casas Bahia e Magazine Luiza bloqueiam TODA requisição automatizada**
(confirmado de novo — até uma URL de produto real achada via WebSearch
dá 403 pros meus próprios pedidos, curl e WebFetch). Pra essas duas,
sempre que possível, o fluxo virou: eu acho a URL real via WebSearch
(nunca inventada — sempre um resultado indexado, título batendo com o
produto certo) e **peço pro usuário abrir no próprio navegador** (não
bloqueado) pra confirmar preço/estoque antes de eu gravar como dado
real — mesmo processo usado com sucesso 2x seguidas (Electrolux DF44 na
Casas Bahia e na Magazine Luiza, ambos confirmados "sem estoque").

Pros outros 9 produtos, o usuário pediu pra eu mesmo achar os links
("por que você só não pesquisa como Claude... acha os links e põe tudo
certinho") em vez de confirmar um por um — mudança de processo
explícita. Resultado: 15 URLs novas (Magazine Luiza + Casas Bahia pra
Electrolux IF55, Brastemp BRM44/BRE80, Consul CRB39/CRM50, Samsung
RT46/RF50, LG GC-L; só Magazine Luiza pra LG GC-B, Casas Bahia não
retornou nenhum resultado pra esse modelo) achadas via WebSearch,
sempre o MESMO modelo já usado nas outras lojas quando possível (ex:
BRM44HK, CRB39AK, IB7S, RF22R7351SR — mesma consistência de sempre).
**Só `url`, sem `preco`/`em_estoque`** — diferente da Casas Bahia/
Magazine Luiza da Electrolux DF44 (que o usuário confirmou no
navegador), essas 15 não foram verificadas por ninguém: uma troca
deliberada de confiança por velocidade, sinalizada explicitamente nos
comentários do código (`# Achadas via WebSearch`) pra não se confundir
com dado de verdade confirmado.

`popular_produtos_e_precos()` também mudou de "sorteia 2-4 das 4 lojas
online" pra **sempre incluir as 4** (Amazon, Magazine Luiza, Casas
Bahia, Loja Oficial da Marca) + 1 física — fazia sentido sortear quando
só a Bemol tinha dado real (todo o resto igualmente simulado), mas
sortear MENOS que todas agora esconderia dado bom atrás de sorte,
contrariando o pedido de cobertura completa.

**(Estado descrito acima ficou obsoleto pouco depois — ver seção
"Magazine Luiza e Casas Bahia removidas..." mais abaixo: as duas saíram
do catálogo de vez, e "Loja Oficial da Marca" virou 5 lojas com nome
próprio.)**

## Magazine Luiza e Casas Bahia removidas, Carrefour no lugar, marcas com nome próprio

Depois de confirmar (README acima) que Magazine Luiza e Casas Bahia
bloqueiam qualquer automação — mesmo Playwright sem disfarce nenhum —,
usuário pediu pra **remover as duas de vez** e "colocar todas que não
nos bloqueiam" no lugar, além de trocar o rótulo genérico "Loja Oficial
da Marca" pelo **nome real de cada marca**.

**Lojas candidatas testadas antes de escolher** (mesma disciplina de
sempre — nunca adicionar sem checar `robots.txt` primeiro): Mercado
Livre **bloqueia explicitamente bots de IA no robots.txt**
(`Disallow: /` pra `ClaudeBot`/`GPTBot`/etc — achado real, quase virou
mais um erro se eu tivesse pulado essa checagem), Fast Shop não respondeu
robots.txt, Kabum respondeu mas tem catálogo de eletrodomésticos fraco
pras nossas 5 marcas (só 1 Brastemp de linha diferente). **Carrefour**
passou em tudo: `robots.txt` permite, é VTEX (mesma plataforma de Bemol/
Brastemp/Consul/Electrolux), e tem cobertura real pra praticamente o
catálogo inteiro via WebSearch.

**Achado ao testar o JSON-LD do Carrefour produto a produto**: várias
páginas retornam `"price": 0` junto com `"availability": InStock` — dado
de catálogo claramente quebrado (visto em Electrolux DF44/IF55 parcial,
Brastemp BRE80, Consul CRM50, Samsung RT46/RF50). Só usei preço/estoque
reais do Carrefour nos 4 produtos onde o preço veio um valor de verdade
(Brastemp BRM44, Consul CRB39, LG GC-B, LG GC-L) — os outros ficam só
com `url` (mesmo padrão de honestidade de sempre: nunca gravar um "0"
como se fosse preço real). Electrolux DF44 nem tem entrada de Carrefour
— toda URL encontrada pra DFN41 lá deu 404 (anúncio removido do índice).

**"Loja Oficial da Marca" virou 5 `Store` distintos** (Electrolux,
Brastemp, Consul, Samsung, LG) em vez de um genérico reaproveitado —
resolve o pedido ("quero o nome da marca mesmo") e também elimina de vez
o lookup `_SITE_OFICIAL_POR_MARCA` que existia só pra compensar o rótulo
genérico. `popular_produtos_e_precos()` mudou de "sempre as 4 lojas
online" pra: Amazon + Carrefour (universais, todo produto) + a loja
DAQUELA marca especificamente (nunca a Consul aparecendo num produto
Samsung) + 1 física — mantém a cobertura máxima pedida antes, sem
misturar marca errada com produto errado.

## Painel admin — busca e toggle (polish adicional)

- Barra de busca (Alpine.js, filtro client-side por nome/modelo/marca —
  não precisa de round-trip ao servidor pra uma lista de 10 produtos).
- Checkbox de "em estoque" trocado por um toggle switch (trilho + bolinha
  deslizando, `peer-checked` do Tailwind) — mais claro visualmente que uma
  checkbox nua, mesmo funcionamento por baixo (`name="in_stock"`, ligado
  ao `<form>` via atributo `form=`, como já era).

## Login do painel admin + rota /admin (não mais /admin/precos)

Pedido do usuário: tela de login (usuário `admin`, senha `admin12345`)
protegendo o painel, e a URL virar `/admin` em vez de `/admin/precos`.

- **Credenciais configuráveis, não hardcoded**: `Config.ADMIN_USERNAME`/
  `ADMIN_PASSWORD` (`config.py`) leem de variável de ambiente
  (`ADMIN_USERNAME`/`ADMIN_PASSWORD` no `.env`), com fallback pros
  valores exatos pedidos (`admin`/`admin12345`) — mesmo padrão já
  estabelecido pra `SECRET_KEY`/`GROQ_API_KEY`. Pra trocar a senha em
  produção (Railway), é só definir essas duas variáveis no painel do
  serviço — nenhum código muda.
- **Sessão, não cookie com a senha**: login bem-sucedido grava só
  `session["admin_logado"] = True` (sessão do Flask, assinada com
  `SECRET_KEY` — não dá pra falsificar sem saber a chave); a senha em si
  nunca é gravada em lugar nenhum além da comparação no momento do
  login.
- **`hmac.compare_digest`** em vez de `==` pra comparar usuário/senha —
  comparação em tempo constante, não vaza (por quanto tempo a resposta
  demora) quantos caracteres bateram certo. Baixo custo de implementar,
  sem motivo pra pular mesmo com usuário fixo único.
- **`login_necessario`** (decorator simples, `functools.wraps`) protege
  `listar_precos`/`editar_preco` — sem sessão válida, redireciona pra
  `/admin/login`.
- **Rota**: `listar_precos` virou `@admin_bp.route("", strict_slashes=False)`
  (blueprint já tem `url_prefix="/admin"`, então isso resolve exatamente
  em `/admin`, sem precisar de `/admin/` com barra nem redirect extra —
  testado que bate 302 direto pro login numa hop só, não 308→302 como
  aconteceria com `route("/")`). `editar_preco` virou
  `/admin/<id>/editar` (era `/admin/precos/<id>/editar`) — nenhum
  template precisou mudar, todos já usavam `url_for('admin.editar_preco', ...)`
  em vez de string fixa.
- Novo `admin_login.html` (formulário simples, mesmo estilo visual do
  resto do painel) + botão "Sair" (`/admin/logout`) no topo de
  `admin_precos.html`.

Testado de ponta a ponta com curl + cookies: sem login → `/admin`
redireciona pro login; senha errada → fica de fora; senha certa → entra;
logout → tranca de novo. `/admin/precos` (rota antiga) agora dá 404, como
esperado.

## Auditoria Bemol + Samsung na loja errada + Americanas (mais opções) + fim do bug de homepage de vez

Usuário reportou o Carrefour caindo em homepage num produto (Electrolux
DF44 — corrigido, achei URL real com busca focada no formato canônico
`/produto/{slug}-{id}`) e pediu pra auditar a Bemol do mesmo jeito, além
de "mais opções de lugares para comprar".

- **Bemol auditada**: achei o mesmo tipo de bug nos 2 produtos LG (Bemol
  sorteada como loja física por sorteio, sem dado real — cai na homepage
  dela, dando a entender que "talvez venda" quando já sabíamos que não
  vende LG). Corrigido: LG nunca mais sorteia Bemol como opção física, só
  Eletro Norte (que já mostra "Sem site" honestamente).
- **Achado sobre a Samsung, sem querer**: pesquisando mais lojas, o
  domínio `shop.samsung.com` apareceu repetido nos resultados — é a LOJA
  de verdade da Samsung (também VTEX, JSON-LD **estático**), diferente de
  `www.samsung.com` (site institucional/marketing, precisava de
  Playwright pra ver o preço). Troquei as 2 entradas da Samsung pra usar
  `shop.samsung.com` — preço/estoque real sem precisar de navegador
  headless nenhum, mais simples e mais confiável que a solução anterior.
- **Americanas adicionada** — testada antes (robots.txt limpo, sem
  bloqueio de bot de IA como o Mercado Livre tinha) e com bom catálogo:
  achei dado real (JSON-LD, `offers` em formato de lista — é marketplace,
  vários vendedores por produto, usei sempre o mais barato) pra 7 dos 10
  produtos.
- **Correção estrutural pra nunca mais cair em homepage**: em vez de
  sempre incluir Carrefour/Americanas em TODO produto (o que gerava
  exatamente o bug relatado sempre que faltasse dado real pra algum),
  `popular_produtos_e_precos()` agora só inclui essas duas quando JÁ
  existe uma URL real confirmada pra aquele produto específico — a Amazon
  continua sempre incluída (busca sempre funciona, não depende de achar
  URL nenhuma). Isso garante, na estrutura do código, que nenhuma oferta
  dessas duas caia em homepage — nem hoje, nem se um produto novo entrar
  no catálogo no futuro sem alguém lembrar de pesquisar o Carrefour/
  Americanas pra ele.

Confirmado com curl nos 10 produtos: zero links "nus" pra homepage do
Carrefour/Americanas sobrando; toda oferta mostrada tem link real
(Amazon/Carrefour/Americanas/loja da marca/Bemol) ou estado honesto
("Esgotado"/"Sem site") quando não tem.

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
