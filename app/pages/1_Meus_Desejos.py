"""WishLens · Meus Desejos: gráficos dos seus desejos de consumo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from src import armazenamento, ui

ui.configurar("Meus Desejos", "⭐")

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

# ---------- Resumo ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Desejos", len(df))
c2.metric("Categoria favorita", df["categoria"].mode()[0])
c3.metric("Para comprar", int((df["tipo"] == "comprar").sum()))
c4.metric("Comida / Adoção", f'{int((df["tipo"] == "receita").sum())} / {int((df["tipo"] == "adotar").sum())}')

# ---------- Gráficos ----------
st.subheader("O que você mais deseja")
por_cat = df["categoria"].value_counts().reset_index()
fig = px.bar(por_cat, x="count", y="categoria", orientation="h",
             labels={"count": "desejos", "categoria": ""}, color_discrete_sequence=["#7C5CFF"])
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=360, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Comprar, comer ou adotar?")
    fig = px.pie(df, names="tipo", hole=0.55,
                 color="tipo", color_discrete_map={"comprar": "#7C5CFF", "receita": "#FF8A3D", "adotar": "#2BB673"})
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
with col_b:
    st.subheader("Top itens")
    top = df["item"].value_counts().head(8).reset_index()
    st.dataframe(top.rename(columns={"item": "item", "count": "vezes"}), hide_index=True, use_container_width=True)

st.subheader("Quando você deseja")
dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
tmp = df.assign(dia=df["criado_em"].dt.dayofweek.map(dict(enumerate(dias))),
                hora=df["criado_em"].dt.hour)
mapa = tmp.pivot_table(index="dia", columns="hora", values="id", aggfunc="count", fill_value=0)
mapa = mapa.reindex([d for d in dias if d in mapa.index])
fig = px.imshow(mapa, color_continuous_scale="Purples", aspect="auto",
                labels={"x": "hora do dia", "y": "", "color": "desejos"})
fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Ao longo do tempo")
por_dia = df.set_index("criado_em").resample("D")["id"].count().rename("desejos").reset_index()
fig = px.area(por_dia, x="criado_em", y="desejos", labels={"criado_em": ""},
              color_discrete_sequence=["#7C5CFF"])
fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

with st.expander("Ver tabela completa"):
    st.dataframe(df.drop(columns=["id"]).sort_values("criado_em", ascending=False),
                 hide_index=True, use_container_width=True)
    st.download_button("Baixar CSV", df.to_csv(index=False).encode(), f"desejos_{quem}.csv", "text/csv")
