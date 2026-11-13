"""WishLens · Avaliação: CLIP x IA nas fotos do jogo (fase 5 do CRISP-DM).

Em toda foto julgam dois modelos open source: a IA (diz tema, achado e se é foto real) e o CLIP da OpenAI
(diz o tema e a chance de ser foto de tela). Esta página compara os dois com os dados do jogo.
"""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from src import armazenamento, jogo, ui
from src.exportar import COLUNAS_CSV, anonimizar

ui.configurar("Avaliação", "📊")
cor = ui.cores()

st.title("📊 Avaliação dos juízes")
st.markdown(
    "Fase 5 do CRISP-DM: **os modelos acertam?** Em cada foto do jogo julgam dois modelos open source: a **IA** "
    "(diz o tema, o achado e se é foto real) e o **CLIP** da OpenAI (diz o tema e a chance de ser foto de tela). "
    f"O CLIP barra a foto quando vê uma tela com chance ≥ {jogo.VETO_TELA:.0%} ou quando o tema da IA "
    f"fica fora dos {jogo.VETO_RANK} primeiros palpites dele (de 7: os 5 temas, tela e nenhum).")

pontuadas = jogo.calcular_pontos(armazenamento.capturas())
if pontuadas.empty:
    st.info("Sem fotos ainda. Jogue em **Jogar** ou carregue os dados de exemplo na barra lateral.")
    st.stop()
if pontuadas["usuario"].astype(str).str.startswith("exemplo:").any():
    st.caption("🧪 Inclui dados fictícios de demonstração.")

a = jogo.avaliar_juizes(pontuadas)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fotos com os 2 juízes", a["comparadas"])
c2.metric("Concordância de tema", f'{a["concordancia"]:.0%}' if a["concordancia"] is not None else "—")
c3.metric("Vetos do CLIP", int(a["vetos"].sum()) if len(a["vetos"]) else 0)
c4.metric("Achado específico (IA)", f'{a["especificos"]:.0%}' if a["especificos"] is not None else "—",
          help="Fotos aceitas com modelo, espécie, raça ou peça. Sozinho, o CLIP só diria o genérico ('carro').")

if a["comparadas"]:
    st.subheader("Matriz de confusão: tema da IA × tema do CLIP")
    st.caption("Na diagonal, os dois concordam. Fora dela, onde discordam.")
    m = a["matriz"]
    fig = px.imshow(m, text_auto=True, aspect="auto", color_continuous_scale=cor["heat"],
                    labels={"x": "CLIP", "y": "IA", "color": "fotos"})
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(ui.estilizar(fig, 380), use_container_width=True)

    st.subheader("Onde o CLIP mais discorda")
    por_tema = a["por_tema"].rename("concordância").reset_index().rename(columns={"ia": "tema"})
    fig = px.bar(por_tema, x="concordância", y="tema", orientation="h", range_x=[0, 1],
                 labels={"tema": ""}, color_discrete_sequence=[cor["accent"]])
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(ui.estilizar(fig, 260), use_container_width=True)
else:
    st.info("Ainda não há fotos julgadas pelos dois modelos (precisa da VISAO_URL e do CLIP instalado).")

st.subheader("Por que as fotos foram recusadas")
if len(a["recusas"]):
    recusas = (a["recusas"].rename(lambda m: m.split(" (")[0] if "discordaram" in m else m)
               .groupby(level=0).sum().sort_values().rename("fotos").reset_index())
    fig = px.bar(recusas, x="fotos", y="motivo", orientation="h", labels={"motivo": ""},
                 color_discrete_sequence=[cor["accent"]])
    st.plotly_chart(ui.estilizar(fig, 260), use_container_width=True)
    st.caption(f'Taxa de recusa geral: {(~pontuadas["aceita"]).mean():.0%} das fotos.')
else:
    st.caption("Nenhuma foto recusada.")

st.subheader("O que os juízes deixaram passar (contestações)")
st.caption("Fotos recusadas em que a pessoa disse \"o juiz errou, era…\". Não dão pontos; mostram onde o "
           "identificador ainda erra (ex.: mouse que não era aceito como peça).")
if a["contestadas"].empty:
    st.caption("Nenhuma contestação ainda.")
else:
    st.markdown(ui.lista([(f"Juiz disse: {html.escape(r.tema_dito)} → era: {html.escape(r.contestada)}",
                           f"{int(r.vezes)}×") for r in a["contestadas"].itertuples()]), unsafe_allow_html=True)

st.divider()
csv = anonimizar(pontuadas[[c for c in COLUNAS_CSV if c in pontuadas]]).to_csv(index=False).encode("utf-8")
st.download_button("Baixar CSV anonimizado (para o notebook de avaliação)", csv, "avaliacao_juizes.csv",
                   "text/csv", use_container_width=True)
