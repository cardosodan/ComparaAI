# ComparaAI

Comparador de preços de eletrodomésticos — Fase 1 (MVP): geladeiras, dados
mockados, rodando localmente. Nome provisório (placeholder), ver seção
"Nome do projeto" do brief original.

**Status: Passo 1 concluído** (setup do projeto + estrutura de pastas +
Tailwind). Próximo passo: modelos de banco + seed de dados mockados.

## Stack

- Backend: Python + Flask + Flask-SQLAlchemy + Flask-Migrate
- Banco: SQLite em desenvolvimento (troca pra Postgres via `DATABASE_URL`,
  sem tocar em código — abstração do SQLAlchemy)
- CSS: Tailwind CSS v4, via **CLI standalone** (`tools/tailwindcss.exe`,
  binário baixado direto do GitHub releases) — **sem Node.js/npm**, de
  propósito, pra manter tudo num codebase Python só (mesma justificativa do
  brief original: fácil de deployar numa VPS sem gerenciar frontend
  separado).
- Interatividade (a partir do Passo 4+): HTMX + Alpine.js, via CDN.

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
- [ ] 2. Modelos de banco (`models.py`) + script de seed com dados mockados
- [ ] 3. Layout base (`base.html`) com navbar, footer, sistema de cores/tipografia
- [ ] 4. Home page com busca
- [ ] 5. Rota e template de resultados de busca + filtros
- [ ] 6. Página de produto com tabela comparativa e gráfico de histórico
- [ ] 7. Ajustes finos de responsividade e microinterações
- [ ] 8. Painel admin simples de edição manual de preços
