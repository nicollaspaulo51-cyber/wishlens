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

st.title("Minha coleção")

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
    st.caption("Dados fictícios de demonstração.")

# ---------- Resumo e estilo ----------
estilo = jogo.estilo_jogador(pontuadas, quem)
if estilo:
    st.markdown(
        f'<div class="wl-card"><div class="wl-estilo">{html.escape(estilo)}</div>'
        f'<span class="wl-muted" style="font-size:.9rem">É o seu estilo de jogador: o grupo em que o K-Means '
        f'colocou você ao comparar o que você fotografa com {pontuadas["usuario"].nunique()} jogadores.</span></div>',
        unsafe_allow_html=True)

st.markdown(ui.resumo_html([
    (int(aceitas["pontos"].sum()), "pontos"),
    (aceitas["achado"].map(jogo.normalizar).nunique(), "achados diferentes"),
    (jogo.corrente_atual(pontuadas, quem), f"dias seguidos ({jogo.CORRENTE_DIAS} dão +{jogo.CORRENTE})"),
    (len(minhas), "fotos"),
    (f'{(~minhas["aceita"]).mean():.0%}', "recusadas")]), unsafe_allow_html=True)

# ---------- Álbum de figurinhas por tema ----------
st.subheader("Álbum")
st.caption("Figurinha colada: um achado seu. Tracejada: a turma já achou e você ainda não (só a 1ª letra).")
medalha_de = {m["id"]: m for m in jogo.medalhas(pontuadas, quem)}
contagem_turma = (pontuadas[pontuadas["aceita"]].assign(chave=lambda d: d["achado"].map(jogo.normalizar))
                  .groupby(["tema", "chave"]).size())
paginas = []
for tema in TEMAS:
    meus = aceitas[aceitas["tema"] == tema.id]
    unicos = meus.assign(chave=meus["achado"].map(jogo.normalizar)).drop_duplicates("chave")
    colados = [(r.achado, int(contagem_turma.get((tema.id, r.chave), 1))) for r in unicos.itertuples()]
    total = int((contagem_turma.index.get_level_values("tema") == tema.id).sum())
    paginas.append(ui.album_html(tema, colados, jogo.lacunas(pontuadas, quem, tema.id), total,
                                 medalha_de.get(tema.id)))
st.markdown("".join(paginas), unsafe_allow_html=True)
st.markdown(ui.medalhas_html([medalha_de["mirantes"]]), unsafe_allow_html=True)

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
