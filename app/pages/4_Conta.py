"""WishLens · Conta: entrar e sair, e o link para a análise do projeto (o que antes ficava na barra lateral)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import ui

ui.configurar("Conta", "👤")

st.title("Conta")
with st.container(border=True):
    ui.conta_e_usuario()

st.subheader("Como pontuar")
st.markdown("""
- Toda foto aceita vale **10 pontos**, e **+10** na primeira vez que você acha aquilo.
- **Até +20** pela raridade. No tema de hoje, tudo vale **o dobro**.
- **Mirante** (a até 40 m de um lugar do mapa): +5. **Lupa** cheia: o próximo achado ganha +50%.
- **Desafios do dia**: +15 cada. **7 dias seguidos**: +20.""")

st.subheader("Projeto")
st.page_link("pages/3_Avaliação.py", label="Avaliação dos juízes e dados da turma", icon=":material/insights:")
st.caption("Só guardamos o bairro e um quadrado de cerca de 500 m de cada foto, nunca a coordenada exata.")
