"""Agregação de preço/histórico pra exibição — página de produto (Passo 6).
Separado de search.py de propósito: search.py é sobre ACHAR produtos,
este módulo é sobre como EXIBIR preço/histórico de UM produto já achado.
"""
from collections import defaultdict
from datetime import datetime


def montar_historico_para_grafico(produto) -> dict:
    """Devolve {"labels": [...], "serie_media": [...], "series_por_loja":
    {nome_loja: [...]}} pronto pro Chart.js (brief seção 6.3: "por loja ou
    média"). Um ponto por dia (é como o seed gera, ver seed_data.
    gerar_historico_de_precos) — dia sem ponto pra uma loja específica
    vira `None` na série dela, o Chart.js pula o ponto sem quebrar a linha
    inteira."""
    pontos = sorted(produto.price_history, key=lambda h: h.recorded_at)
    if not pontos:
        return {"labels": [], "serie_media": [], "series_por_loja": {}}

    datas_ordenadas = sorted({p.recorded_at.date() for p in pontos})
    labels = [d.strftime("%d/%m") for d in datas_ordenadas]

    por_loja_e_data = defaultdict(dict)
    for ponto in pontos:
        por_loja_e_data[ponto.store.name][ponto.recorded_at.date()] = float(ponto.price)

    series_por_loja = {
        loja: [valores.get(d) for d in datas_ordenadas] for loja, valores in por_loja_e_data.items()
    }

    serie_media = []
    for d in datas_ordenadas:
        valores_do_dia = [valores[d] for valores in por_loja_e_data.values() if d in valores]
        serie_media.append(round(sum(valores_do_dia) / len(valores_do_dia), 2) if valores_do_dia else None)

    return {"labels": labels, "serie_media": serie_media, "series_por_loja": series_por_loja}


def tempo_relativo(momento: datetime, agora: datetime) -> str:
    """"atualizado há X horas" (brief seção 6.3) — texto pronto, não deixa
    conta de data solta no template Jinja."""
    horas = (agora - momento).total_seconds() / 3600
    if horas < 1:
        return "agora mesmo"
    if horas < 24:
        h = int(horas)
        return f"há {h} hora{'s' if h != 1 else ''}"
    dias = int(horas / 24)
    return f"há {dias} dia{'s' if dias != 1 else ''}"


# Fase 1 é só geladeiras — mapeamento de specs fixo pra essa categoria.
# Categoria nova (fogão, lava-louças...) vai precisar do próprio mapeamento
# quando ganhar produtos de verdade (specs de fogão não tem "capacidade em
# litros", por exemplo).
def formatar_especificacoes(specs: dict) -> list[tuple[str, str]]:
    linhas = []
    if "capacidade_litros" in specs:
        linhas.append(("Capacidade", f"{specs['capacidade_litros']} litros"))
    if "frost_free" in specs:
        linhas.append(("Frost Free", "Sim" if specs["frost_free"] else "Não"))
    if "cor" in specs:
        linhas.append(("Cor", specs["cor"]))
    if "voltagem" in specs:
        linhas.append(("Voltagem", specs["voltagem"]))
    if "dimensoes_cm" in specs:
        linhas.append(("Dimensões (A x L x P)", f"{specs['dimensoes_cm']} cm"))
    if "consumo_kwh_mes" in specs:
        linhas.append(("Consumo médio", f"{specs['consumo_kwh_mes']} kWh/mês"))
    return linhas
