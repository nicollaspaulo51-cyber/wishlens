"""WishLens · Descobrir: feed para rolar com coisas relacionadas aos seus desejos."""

import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from src import armazenamento, ui
from src.categorias import FAIXA_PRECO, emoji
from src.feed import gerar_feed
from src.links import links_para

ui.configurar("Descobrir", "✨")
cor = ui.cores()

POR_PAGINA = 8
ROTULO = {"perfil": "🎯 Seu perfil", "vizinhos": "👥 Gente parecida", "novo": "🧭 Algo novo"}
TIPO = {"comprar": "Comprar", "receita": "Comer", "adotar": "Adotar"}

st.title("✨ Descobrir")
st.caption("Role para ver coisas ligadas aos seus desejos. **❤️ Quero** salva nos seus desejos e o feed se ajusta; "
           "**🙈 Não curti** esconde o item.")

df = armazenamento.todos()
usuarios = sorted(df["usuario"].unique()) if not df.empty else []
padrao = ui.usuario_padrao(usuarios)
if padrao not in usuarios:
    usuarios = [padrao] + usuarios
quem = st.selectbox("Feed de", usuarios, index=usuarios.index(padrao))
if quem.startswith("exemplo:"):
    st.caption("🧪 Feed montado a partir de dados fictícios de demonstração.")

estado = st.session_state.setdefault("feed", {})
meu = estado.setdefault(quem, {"ocultos": set(), "paginas": 1})


def querer(item, motivo_tipo):
    acao = f"feed_{motivo_tipo}"
    if quem.startswith("exemplo:"):  # dados de exemplo ficam só na memória
        armazenamento.adicionar_varios([{
            "id": str(uuid.uuid4()), "usuario": quem, "criado_em": datetime.now(), "item": item.nome,
            "categoria": item.categoria, "tipo": item.tipo, "faixa_preco": FAIXA_PRECO.get(item.categoria, "—"),
            "confianca": None, "cidade": None, "acao": acao}])
    else:
        armazenamento.salvar_desejo(item, None, None, None, acao=acao)
    st.toast(f"{emoji(item)} {item.nome} salvo nos desejos")


def ocultar(item):
    meu["ocultos"].add(item.nome)


cartoes = []
for p in range(meu["paginas"]):
    cartoes += gerar_feed(df, quem, ocultos=meu["ocultos"], quantidade=POR_PAGINA, pagina=p)

if not cartoes:
    st.info("Você já viu tudo o que o catálogo tem por enquanto. Novos itens aparecem quando o catálogo crescer.")
    st.stop()

for i, c in enumerate(cartoes):
    it = c.item
    with st.container(border=True):
        col_emoji, col_txt = st.columns([1, 5], vertical_alignment="center")
        col_emoji.markdown(f'<div style="font-size:3.4rem;text-align:center;line-height:1">{emoji(it)}</div>',
                           unsafe_allow_html=True)
        col_txt.markdown(
            f'<span class="wl-badge">{ROTULO[c.tipo_motivo]}</span>'
            f'<div style="font-family:\'Bricolage Grotesque\',system-ui,sans-serif;font-size:1.45rem;'
            f'font-weight:800;line-height:1.2;margin:.2rem 0">{it.nome.capitalize()}</div>'
            f'<div class="wl-muted" style="font-size:.9rem">{c.motivo}</div>'
            f'<div style="margin-top:.4rem">{ui.badge(TIPO[it.tipo])}{ui.badge(it.categoria)}'
            f'{ui.badge("💰 " + c.faixa_preco)}</div>', unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        b1.button("❤️ Quero", key=f"q_{quem}_{it.nome}", on_click=querer, args=(it, c.tipo_motivo),
                  use_container_width=True, type="primary")
        b2.button("🙈 Não curti", key=f"n_{quem}_{it.nome}", on_click=ocultar, args=(it,),
                  use_container_width=True)
        nome_link, url = next(iter(links_para(it).items()))
        b3.link_button(f"{nome_link} ↗", url, use_container_width=True)

total = len(gerar_feed(df, quem, ocultos=meu["ocultos"], quantidade=10_000))
if len(cartoes) < total:
    if st.button("⬇️ Ver mais", use_container_width=True):
        meu["paginas"] += 1
        st.rerun()
else:
    st.caption("Fim do feed por enquanto ✨")
