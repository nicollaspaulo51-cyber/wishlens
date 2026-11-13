"""WishLens · Minha Coleção: álbum dos seus achados por tema, estilo de jogador e gráficos."""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from src import armazenamento, jogo, ui
from src.temas import POR_ID, TEMAS

ui.configurar("Minha Coleção", "📚")
cor = ui.cores()

st.title("📚 Minha Coleção")

pontuadas = jogo.calcular_pontos(armazenamento.capturas())
jogadores = sorted(pontuadas["usuario"].unique()) if not pontuadas.empty else []
eu = armazenamento.usuario_atual()
padrao = eu if eu in jogadores or not jogadores else ("exemplo:eu" if "exemplo:eu" in jogadores else jogadores[0])
if padrao not in jogadores:
    jogadores = [padrao] + jogadores
quem = st.selectbox("Coleção de", jogadores, index=jogadores.index(padrao), format_func=ui.nome_publico)

minhas = pontuadas[pontuadas["usuario"] == quem] if not pontuadas.empty else pontuadas
aceitas = minhas[minhas["aceita"]] if not minhas.empty else minhas
if aceitas.empty:
    st.info("Nenhum achado ainda. Vá em **Jogar** e tire a primeira foto!")
    st.stop()
if quem.startswith("exemplo:"):
    st.caption("🧪 Dados fictícios de demonstração.")

# ---------- Resumo e estilo ----------
estilo = jogo.estilo_jogador(pontuadas, quem)
if estilo:
    st.markdown(
        f'<div class="wl-card"><span class="wl-muted" style="font-size:.8rem;letter-spacing:.08em;'
        f'text-transform:uppercase">Seu estilo de jogador</span>'
        f'<div style="font-family:\'Bricolage Grotesque\',system-ui,sans-serif;font-size:1.7rem;'
        f'font-weight:800;color:{cor["accent"]}">{html.escape(estilo)}</div>'
        f'<span class="wl-muted" style="font-size:.85rem">Grupo encontrado pelo K-Means comparando a proporção '
        f'das suas capturas por tema com a de {pontuadas["usuario"].nunique()} jogadores.</span></div>',
        unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pontos", int(aceitas["pontos"].sum()))
c2.metric("Achados diferentes", aceitas["achado"].map(jogo.normalizar).nunique())
c3.metric("Fotos", len(minhas))
c4.metric("Recusadas", f'{(~minhas["aceita"]).mean():.0%}')

# ---------- Álbum por tema ----------
st.subheader("Álbum")
contagem_turma = (pontuadas[pontuadas["aceita"]].assign(chave=lambda d: d["achado"].map(jogo.normalizar))
                  .groupby(["tema", "chave"]).size())
for tema in TEMAS:
    meus = aceitas[aceitas["tema"] == tema.id]
    unicos = meus.assign(chave=meus["achado"].map(jogo.normalizar)).drop_duplicates("chave")
    with st.expander(f"{tema.emoji} {tema.nome} · {len(unicos)} achados", expanded=len(unicos) > 0):
        if unicos.empty:
            st.caption(f"Nada ainda. Procure em {tema.onde}.")
            continue
        linhas = []
        for r in unicos.itertuples():
            vezes = int(contagem_turma.get((tema.id, r.chave), 1))
            raridade = "💎 raro" if vezes <= 1 else ("✨ incomum" if vezes <= 3 else "comum")
            linhas.append((html.escape(r.achado), f"{raridade} · achado {vezes}× pela turma"))
        st.markdown(ui.lista(linhas), unsafe_allow_html=True)

# ---------- Gráficos ----------
st.subheader("Quando e o quê")
por_tema = aceitas["tema"].map(lambda t: POR_ID[t].nome).value_counts().reset_index()
fig = px.bar(por_tema, x="count", y="tema", orientation="h", labels={"count": "achados", "tema": ""},
             color_discrete_sequence=[cor["accent"]])
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(ui.estilizar(fig, 240), use_container_width=True)

por_dia = aceitas.assign(dia=aceitas["criado_em"].dt.date).groupby("dia")["pontos"].sum().reset_index()
fig = px.bar(por_dia, x="dia", y="pontos", labels={"dia": "", "pontos": "pontos"},
             color_discrete_sequence=[cor["accent"]])
st.plotly_chart(ui.estilizar(fig, 240), use_container_width=True)
