"""Partes de interface compartilhadas entre as páginas."""

import streamlit as st

from src import armazenamento
from src.exemplo import gerar_exemplos

CSS = """
<style>
.wl-card {padding: 1rem 1.2rem; border-radius: 14px; border: 1px solid rgba(128,128,128,.25);
          background: rgba(124, 92, 255, .06); margin-bottom: .8rem;}
.wl-badge {display:inline-block; padding:.15rem .6rem; border-radius:999px; font-size:.8rem;
           background: rgba(124, 92, 255, .15); margin-right:.3rem;}
</style>
"""


def configurar(titulo: str, icone: str = "🔍") -> None:
    st.set_page_config(page_title=f"WishLens · {titulo}", page_icon=icone, layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    barra_lateral()


def barra_lateral() -> None:
    with st.sidebar:
        st.markdown("## 🔍 WishLens")
        st.caption("Point. Snap. Want.")
        # Guardado fora do widget: o Streamlit apaga o estado de widgets ao trocar de página.
        st.session_state.setdefault("usuario", "eu")
        st.session_state["_campo_usuario"] = st.session_state["usuario"]
        st.text_input("Seu nome de usuário", key="_campo_usuario",
                      on_change=lambda: st.session_state.update(usuario=st.session_state["_campo_usuario"].strip() or "eu"))
        st.divider()
        st.markdown("**Demonstração**")
        st.caption("Dados fictícios para ver os gráficos funcionando. Não são dados reais.")
        if st.button("Carregar dados de exemplo", use_container_width=True):
            armazenamento.remover_exemplos()
            armazenamento.adicionar_varios(gerar_exemplos())
            st.toast("Dados de exemplo carregados")
        if st.button("Remover dados de exemplo", use_container_width=True):
            armazenamento.remover_exemplos()
            st.toast("Dados de exemplo removidos")
        st.divider()
        st.caption("⚠️ Protótipo: os desejos ficam só nesta sessão do navegador.")


def usuario_padrao(usuarios: list[str]) -> str:
    """Usuário atual; se ele tiver poucos desejos e houver exemplos, mostra o exemplo."""
    from src import armazenamento as arm
    atual = arm.usuario_atual()
    if len(arm.do_usuario(atual)) < 3 and "exemplo:eu" in usuarios:
        return "exemplo:eu"
    return atual


def badge(texto: str) -> str:
    return f'<span class="wl-badge">{texto}</span>'
