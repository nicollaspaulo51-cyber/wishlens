"""WishLens · Pódio: ranking de hoje, da semana e geral, por tema."""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import armazenamento, jogo, ui
from src.temas import POR_ID, TEMAS, tema_do_dia

ui.configurar("Pódio", "🏆")

st.title("Pódio")
hoje = tema_do_dia()
st.markdown(ui.selo_tema_do_dia(hoje), unsafe_allow_html=True)

pontuadas = jogo.calcular_pontos(armazenamento.capturas())
eu = armazenamento.usuario_atual()
if pontuadas.empty:
    st.info("Ninguém jogou ainda. Tire a primeira foto em **Jogar**, ou carregue os dados de exemplo na barra lateral.")
    st.stop()

opcoes_tema = ["todos"] + [t.id for t in TEMAS]
escolha = st.segmented_control("Tema", opcoes_tema, default="todos", selection_mode="single",
                               format_func=lambda i: "Todos" if i == "todos" else f"{POR_ID[i].emoji} {POR_ID[i].nome}")
tema = None if escolha in (None, "todos") else escolha

for aba, periodo in zip(st.tabs(["Hoje", "Semana", "Geral"]), ["hoje", "semana", "geral"]):
    with aba:
        ranking = jogo.podio(pontuadas, periodo, tema=tema)
        if ranking.empty:
            st.info("Sem pontos neste período ainda.")
            continue
        st.markdown(ui.podio_html(ranking, eu), unsafe_allow_html=True)
        pos = jogo.posicao_de(ranking, eu)
        if pos:
            st.markdown(f"Você está em **{pos}º** de {len(ranking)}.")
        tabela = ranking.assign(
            jogador=[ui.nome_publico(u) + (" (você)" if u == eu else "") for u in ranking["usuario"]])
        st.dataframe(tabela[["posicao", "jogador", "pontos", "achados"]], hide_index=True,
                     use_container_width=True,
                     column_config={"posicao": st.column_config.NumberColumn("#", width="small")})

# ---------- Achados mais raros da semana ----------
st.subheader("Achados mais raros da semana")
semana = jogo.no_periodo(pontuadas, "semana")
semana = semana[semana["aceita"]] if not semana.empty else semana
if tema:
    semana = semana[semana["tema"] == tema]
if semana.empty:
    st.caption("Nenhum achado nesta semana.")
else:
    raros = semana.sort_values(["raridade", "criado_em"], ascending=[False, True]).head(5)
    st.markdown(ui.lista([
        (f'{POR_ID[r.tema].emoji} {html.escape(r.achado)}',
         f'{html.escape(ui.nome_publico(r.usuario))}, +{int(r.raridade)} de raridade')
        for r in raros.itertuples()]), unsafe_allow_html=True)
