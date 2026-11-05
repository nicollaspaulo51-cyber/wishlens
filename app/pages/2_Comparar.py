"""WishLens · Comparar: o quanto seus desejos combinam com os de outra pessoa."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.graph_objects as go
import streamlit as st

from src import armazenamento, ui
from src.categorias import CATEGORIAS
from src.perfil import similaridade_cosseno, sugestoes, vetor_perfil

ui.configurar("Comparar", "🤝")

st.title("🤝 Comparar desejos")
st.caption("A comparação só acontece com quem aceitou compartilhar os desejos.")

df_todos = armazenamento.todos()
usuarios = sorted(df_todos["usuario"].unique()) if not df_todos.empty else []
if len(usuarios) < 2:
    st.info("É preciso ter pelo menos duas pessoas com desejos salvos. "
            "Carregue os dados de exemplo na barra lateral para ver como funciona.")
    st.stop()

padrao = ui.usuario_padrao(usuarios)
c1, c2 = st.columns(2)
eu = c1.selectbox("Você", usuarios, index=usuarios.index(padrao) if padrao in usuarios else 0)
outros = sorted((u for u in usuarios if u != eu), key=lambda u: not u.startswith("exemplo:"))
outro = c2.selectbox("Comparar com", outros)

if any(u.startswith("exemplo:") for u in (eu, outro)):
    st.caption("🧪 Comparação com dados fictícios de demonstração.")

aceite = st.checkbox(f"{outro} aceitou compartilhar os desejos comigo", value=outro.startswith("exemplo:"))
if not aceite:
    st.warning("Sem o aceite da outra pessoa, a comparação não é exibida (privacidade / LGPD).")
    st.stop()

df_eu, df_outro = armazenamento.do_usuario(eu), armazenamento.do_usuario(outro)
v_eu, v_outro = vetor_perfil(df_eu), vetor_perfil(df_outro)
sim = similaridade_cosseno(v_eu, v_outro)

# ---------- Resultado ----------
frase = ("Almas gêmeas do consumo! 💜" if sim >= 0.8 else
         "Vocês combinam bastante 😄" if sim >= 0.5 else
         "Alguns gostos em comum 🙂" if sim >= 0.25 else
         "Gostos bem diferentes 🤷")
st.markdown(f'<div class="wl-card" style="text-align:center"><div style="font-size:3rem;font-weight:700">'
            f'{sim:.0%}</div>de combinação · {frase}</div>', unsafe_allow_html=True)
st.progress(sim)
st.caption("Calculado pela **similaridade do cosseno** entre os perfis (proporção de desejos por categoria).")

# ---------- Radar ----------
st.subheader("Perfis lado a lado")
cats = [c for c in CATEGORIAS if v_eu[c] > 0 or v_outro[c] > 0]
fig = go.Figure()
for nome, v, cor in ((eu, v_eu, "#7C5CFF"), (outro, v_outro, "#FF8A3D")):
    fig.add_trace(go.Scatterpolar(r=[v[c] for c in cats] + [v[cats[0]]], theta=cats + [cats[0]],
                                  fill="toself", name=nome, line_color=cor, opacity=0.65))
fig.update_layout(polar=dict(radialaxis=dict(visible=True, tickformat=".0%")),
                  height=420, margin=dict(l=30, r=30, t=20, b=20), legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

# ---------- Em comum e sugestões ----------
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Em comum")
    comuns = sorted(set(df_eu["item"]) & set(df_outro["item"]))
    st.write(" ".join(ui.badge(i) for i in comuns) if comuns else "Nenhum item em comum ainda.",
             unsafe_allow_html=True)
with col_b:
    st.subheader(f"{outro} deseja, você ainda não")
    sug = sugestoes(df_eu, df_outro)
    if sug.empty:
        st.write("Nada novo por aqui.")
    else:
        st.dataframe(sug, hide_index=True, use_container_width=True)
