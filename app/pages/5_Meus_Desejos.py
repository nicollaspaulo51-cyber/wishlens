"""WishLens · Meus Desejos: gráficos dos seus desejos de consumo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from src import armazenamento, ui
from src.clustering import perfil_do_usuario
from src.exportar import anonimizar

ui.configurar("Meus Desejos", "⭐")
cor = ui.cores()

st.title("⭐ Meus Desejos")

df_todos = armazenamento.todos()
usuarios = sorted(df_todos["usuario"].unique()) if not df_todos.empty else []
padrao = ui.usuario_padrao(usuarios)
if padrao not in usuarios:
    usuarios = [padrao] + usuarios
quem = st.selectbox("Ver desejos de", usuarios, index=usuarios.index(padrao))
df = armazenamento.do_usuario(quem)

if df.empty:
    st.info("Nenhum desejo ainda. Fotografe algo na página **Home** e clique em *Salvar*, "
            "ou carregue os dados de exemplo na barra lateral.")
    st.stop()

if quem.startswith("exemplo:"):
    st.caption("🧪 Você está vendo dados fictícios de demonstração.")

# ---------- Perfil (clustering) ----------
perfil = perfil_do_usuario(df_todos, quem)
if perfil:
    st.markdown(
        f'<div class="wl-card"><span class="wl-muted" style="font-size:.8rem;letter-spacing:.08em;'
        f'text-transform:uppercase">Seu perfil de desejo</span>'
        f'<div style="font-family:\'Bricolage Grotesque\',system-ui,sans-serif;font-size:1.7rem;'
        f'font-weight:800;color:{cor["accent"]}">{perfil}</div>'
        f'<span class="wl-muted" style="font-size:.85rem">Grupo encontrado pelo K-Means comparando a proporção '
        f'dos seus desejos por categoria com a de {df_todos["usuario"].nunique()} pessoas.</span></div>',
        unsafe_allow_html=True)

# ---------- Resumo ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Desejos", len(df))
c2.metric("Categoria favorita", df["categoria"].mode()[0])
c3.metric("Para comprar", int((df["tipo"] == "comprar").sum()))
c4.metric("Comer / Adotar", f'{int((df["tipo"] == "receita").sum())} / {int((df["tipo"] == "adotar").sum())}')

# ---------- Gráficos ----------
st.subheader("O que você mais deseja")
por_cat = df["categoria"].value_counts().reset_index()
fig = px.bar(por_cat, x="count", y="categoria", orientation="h",
             labels={"count": "desejos", "categoria": ""}, color_discrete_sequence=[cor["accent"]])
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(ui.estilizar(fig, 340), use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Comprar, comer ou adotar?")
    nomes = {"comprar": "Comprar", "receita": "Comer", "adotar": "Adotar"}
    fig = px.pie(df.assign(tipo=df["tipo"].map(nomes)), names="tipo", hole=0.58, color="tipo",
                 color_discrete_map={nomes[k]: v for k, v in ui.cor_tipo().items()})
    st.plotly_chart(ui.estilizar(fig, 300), use_container_width=True)
with col_b:
    st.subheader("Top itens")
    top = df["item"].value_counts().head(8)
    st.markdown(ui.lista([(i, f"{n}×") for i, n in top.items()]), unsafe_allow_html=True)

st.subheader("Quando você deseja")
dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
tmp = df.assign(dia=df["criado_em"].dt.dayofweek.map(dict(enumerate(dias))),
                hora=df["criado_em"].dt.hour)
mapa = tmp.pivot_table(index="dia", columns="hora", values="item", aggfunc="count", fill_value=0)
mapa = mapa.reindex([d for d in dias if d in mapa.index])
fig = px.imshow(mapa, color_continuous_scale=cor["heat"], aspect="auto",
                labels={"x": "hora do dia", "y": "", "color": "desejos"})
st.plotly_chart(ui.estilizar(fig, 260), use_container_width=True)

st.subheader("Ao longo do tempo")
por_dia = df.set_index("criado_em").resample("D")["item"].count().rename("desejos").reset_index()
fig = px.area(por_dia, x="criado_em", y="desejos", labels={"criado_em": ""},
              color_discrete_sequence=[cor["accent"]])
st.plotly_chart(ui.estilizar(fig, 240), use_container_width=True)

with st.expander("Ver tabela completa e baixar"):
    st.dataframe(df.drop(columns=["id"]).sort_values("criado_em", ascending=False),
                 hide_index=True, use_container_width=True)
    st.download_button("⬇️ Baixar CSV anonimizado (todas as pessoas)",
                       anonimizar(df_todos).to_csv(index=False).encode(),
                       "desejos_anonimizado.csv", "text/csv", use_container_width=True,
                       help="Sem nomes, ids, fotos ou localização exata: pronto para a análise.")
