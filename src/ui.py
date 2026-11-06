"""Partes de interface compartilhadas entre as páginas: tema claro/escuro, barra lateral e estilos."""

import streamlit as st

from src import armazenamento
from src.exemplo import gerar_exemplos

# Paleta igual à da prévia (https://claude.ai/artifact/4sZtfAn7K85Kc6bASY7sjJ)
TEMAS = {
    "claro": {"bg": "#F6F5FB", "surface": "#FFFFFF", "ink": "#1B1830", "muted": "#666180",
              "line": "#E3E0EE", "accent": "#6D4AFF", "accent_ink": "#FFFFFF", "soft": "#EEE9FF",
              "buy": "#6D4AFF", "food": "#E8701F", "adopt": "#17975F", "heat": "Purples"},
    "escuro": {"bg": "#12101B", "surface": "#1B1828", "ink": "#EEEBFA", "muted": "#A39EBE",
               "line": "#2D2942", "accent": "#9C86FF", "accent_ink": "#14111F", "soft": "#272043",
               "buy": "#9C86FF", "food": "#FF9B57", "adopt": "#3FCB8B", "heat": "Purp"},
}

FONTES = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800"
          "&family=Figtree:wght@400;500;600&display=swap")


def tema() -> str:
    return st.session_state.setdefault("tema", "claro")


def cores() -> dict:
    return TEMAS[tema()]


def cor_tipo() -> dict:
    c = cores()
    return {"comprar": c["buy"], "receita": c["food"], "adotar": c["adopt"]}


def _alternar_tema() -> None:
    st.session_state["tema"] = "escuro" if tema() == "claro" else "claro"


def _css() -> str:
    c = cores()
    return f"""
<style>
@import url('{FONTES}');
:root {{ --wl-bg:{c['bg']}; --wl-surface:{c['surface']}; --wl-ink:{c['ink']}; --wl-muted:{c['muted']};
        --wl-line:{c['line']}; --wl-accent:{c['accent']}; --wl-accent-ink:{c['accent_ink']}; --wl-soft:{c['soft']}; }}
[data-testid="stApp"], [data-testid="stApp"] p, [data-testid="stApp"] label, [data-testid="stApp"] li,
[data-testid="stApp"] input, [data-testid="stApp"] button, [data-testid="stMarkdownContainer"],
[data-testid="stApp"] h4, [data-testid="stApp"] h5, [data-testid="stApp"] h6 {{
  font-family: "Figtree", "Segoe UI", system-ui, sans-serif; }}
[data-testid="stApp"] h1, [data-testid="stApp"] h2, [data-testid="stApp"] h3, [data-testid="stMetricValue"] {{
  font-family: "Bricolage Grotesque", "Trebuchet MS", system-ui, sans-serif !important; letter-spacing:-.01em; }}
[data-testid="stApp"] {{ background: var(--wl-bg); color: var(--wl-ink); transition: background .35s, color .35s; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: var(--wl-surface); border-right: 1px solid var(--wl-line); }}
[data-testid="stApp"] h1, [data-testid="stApp"] h2, [data-testid="stApp"] h3, [data-testid="stApp"] h4,
[data-testid="stApp"] p, [data-testid="stApp"] label, [data-testid="stApp"] li,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stSidebarNav"] span,
[data-testid="stExpander"] summary, [data-testid="stMarkdownContainer"] {{ color: var(--wl-ink); }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: var(--wl-muted) !important; }}
[data-testid="stTextInputRootElement"], [data-testid="stTextInputRootElement"] input,
[data-testid="stNumberInputContainer"], [data-testid="stNumberInputContainer"] input,
[data-testid="stSelectbox"] [data-rac], [data-testid="stSelectbox"] input,
[data-baseweb="input"], [data-baseweb="input"] input, [data-baseweb="select"] > div,
[data-testid="stFileUploaderDropzone"], [data-testid="stProgressBarTrack"] {{
  background-color: var(--wl-bg) !important; color: var(--wl-ink) !important; border-color: var(--wl-line) !important; }}
[data-testid="stSelectbox"] button {{ color: var(--wl-muted); }}
[data-testid="stCameraInput"] div, [data-testid="stCameraInput"] button {{
  background-color: var(--wl-bg) !important; color: var(--wl-muted) !important; border-color: var(--wl-line) !important; }}
[role="listbox"], [role="option"], [data-baseweb="popover"] li, [data-baseweb="menu"] {{
  background-color: var(--wl-surface); color: var(--wl-ink); }}
[role="option"]:hover, [role="option"][data-focused="true"] {{ background-color: var(--wl-soft); }}
[role="tooltip"], [role="tooltip"] *, [data-baseweb="tooltip"] div {{
  background-color: var(--wl-surface) !important; color: var(--wl-ink) !important; }}
[data-testid="stExpander"] details, [data-testid="stTabs"] [role="tablist"] {{ border-color: var(--wl-line); }}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseLinkButton-secondary"] {{
  background: var(--wl-surface); color: var(--wl-ink); border-color: var(--wl-line); }}
[data-testid="stBaseButton-primary"] {{ background: var(--wl-accent); color: var(--wl-accent-ink); border-color: var(--wl-accent); }}
hr {{ border-color: var(--wl-line) !important; }}
.wl-card {{ padding: 1rem 1.2rem; border-radius: 16px; border: 1px solid var(--wl-line);
           background: var(--wl-surface); margin-bottom: .8rem; }}
.wl-badge {{ display:inline-block; padding:.15rem .6rem; border-radius:999px; font-size:.8rem;
            background: var(--wl-soft); color: var(--wl-ink); margin: 0 .3rem .3rem 0; }}
.wl-list {{ list-style:none; margin:0; padding:0; }}
.wl-list li {{ display:flex; justify-content:space-between; gap:.8rem; padding:.45rem 0;
              border-bottom:1px solid var(--wl-line); }}
.wl-list li:last-child {{ border-bottom:0; }}
.wl-muted {{ color: var(--wl-muted); }}
.wl-brand {{ font-family:"Bricolage Grotesque", system-ui, sans-serif; font-weight:800; font-size:1.4rem; line-height:1.1; }}
@media (prefers-reduced-motion: reduce) {{ [data-testid="stApp"] {{ transition:none; }} }}
</style>
"""


def configurar(titulo: str, icone: str = "🔍") -> None:
    st.set_page_config(page_title=f"WishLens · {titulo}", page_icon=icone, layout="centered")
    tema()
    st.markdown(_css(), unsafe_allow_html=True)
    barra_lateral()


def barra_lateral() -> None:
    with st.sidebar:
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown('<div class="wl-brand">🔍 WishLens</div><div class="wl-muted" style="font-size:.8rem">'
                    'Point. Snap. Want.</div>', unsafe_allow_html=True)
        escuro = tema() == "escuro"
        c2.button("🌙" if escuro else "☀️", key="botao_tema", on_click=_alternar_tema,
                  help="Tema escuro: clique para clarear" if escuro else "Tema claro: clique para escurecer")

        if armazenamento.supabase_configurado():
            _conta()
        else:
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
        st.caption(f"Armazenamento: {armazenamento.descricao_backend()}")


def _conta() -> None:
    """Login/cadastro no Supabase (só aparece quando o Supabase está configurado)."""
    from src import banco

    sessao = banco.sessao_atual()
    if sessao:
        st.markdown(f"Olá, **{sessao.apelido}**")
        if st.button("Sair", use_container_width=True):
            banco.sair()
            st.rerun()
        return

    entrar, criar = st.tabs(["Entrar", "Criar conta"])
    with entrar, st.form("form_entrar"):
        email = st.text_input("E-mail", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        if st.form_submit_button("Entrar", use_container_width=True):
            try:
                banco.entrar(email, senha)
                st.rerun()
            except Exception as erro:
                st.error(f"Não foi possível entrar: confira e-mail e senha. ({type(erro).__name__})")
    with criar, st.form("form_criar"):
        apelido = st.text_input("Apelido (aparece para quem você conectar)", key="cad_apelido")
        email = st.text_input("E-mail", key="cad_email")
        senha = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="cad_senha")
        consentimento = st.checkbox("Concordo em guardar meus desejos para análise anonimizada", key="cad_ok")
        if st.form_submit_button("Criar conta", use_container_width=True):
            if not (apelido.strip() and email and len(senha) >= 6 and consentimento):
                st.warning("Preencha tudo, use senha com 6+ caracteres e marque o consentimento.")
            else:
                try:
                    banco.cadastrar(email, senha, apelido.strip())
                    st.success("Conta criada! Se o Supabase pedir, confirme o e-mail e depois entre.")
                except Exception as erro:
                    st.error(f"Não foi possível criar a conta ({type(erro).__name__}). O apelido pode já existir.")


def estilizar(fig, altura: int = 320):
    """Aplica o tema atual a um gráfico Plotly."""
    c = cores()
    fig.update_layout(
        template="plotly_dark" if tema() == "escuro" else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Figtree, system-ui, sans-serif", color=c["ink"]),
        height=altura, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="",
    )
    return fig


def usuario_padrao(usuarios: list[str]) -> str:
    """Usuário atual; se ele tiver poucos desejos e houver exemplos, mostra o exemplo."""
    atual = armazenamento.usuario_atual()
    if len(armazenamento.do_usuario(atual)) < 3 and "exemplo:eu" in usuarios:
        return "exemplo:eu"
    return atual


def badge(texto: str) -> str:
    return f'<span class="wl-badge">{texto}</span>'


def lista(linhas: list[tuple[str, str]]) -> str:
    """Lista HTML simples (segue o tema, ao contrário do st.dataframe)."""
    itens = "".join(f"<li><span>{a}</span><span class='wl-muted'>{b}</span></li>" for a, b in linhas)
    return f'<ul class="wl-list">{itens}</ul>'
