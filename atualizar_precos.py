"""Job de atualização automática de preços — busca a página real de cada
oferta e usa a Groq pra extrair o preço atual (ver app/services/
atualizacao_precos.py pra como/por que isso funciona, e as limitações
legais/técnicas documentadas lá).

Uso:
    venv\\Scripts\\python.exe atualizar_precos.py

Pensado pra rodar 1x/dia via agendador (Windows: Agendador de Tarefas —
ver README, seção "Atualização automática de preços", pra o passo a
passo de configurar isso sem precisar rodar na mão todo dia).
"""
import time

from app import create_app
from app.models import Price
from app.services.atualizacao_precos import PAUSA_ENTRE_REQUISICOES_SEGUNDOS, atualizar_oferta

app = create_app()

with app.app_context():
    ofertas = Price.query.filter(Price.url.isnot(None), Price.url != "#").all()
    print(f"{len(ofertas)} ofertas com URL pra atualizar.")

    sucesso, falha = 0, 0
    for i, preco in enumerate(ofertas, start=1):
        print(f"[{i}/{len(ofertas)}] {preco.product.name} — {preco.store.name}...", end=" ")
        if atualizar_oferta(preco):
            print(f"OK (novo preco: R$ {preco.price})")
            sucesso += 1
        else:
            print("falhou/pulado (ver log acima)")
            falha += 1
        if i < len(ofertas):
            time.sleep(PAUSA_ENTRE_REQUISICOES_SEGUNDOS)

    print(f"\nConcluido: {sucesso} atualizadas, {falha} falharam/puladas.")
