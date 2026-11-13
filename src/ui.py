"""Partes de interface compartilhadas entre as páginas: tema claro/escuro, barra lateral e estilos."""

import html

import streamlit as st

from src import armazenamento

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
.wl-place h3 {{ margin:0 0 .2rem 0; }}
.wl-place a {{ color: var(--wl-accent); }}
.wl-place .wl-list li span:first-child {{ white-space:nowrap; }}
.wl-hero {{ padding:1rem 1.2rem; border-radius:18px; margin-bottom:.8rem; color:var(--wl-accent-ink);
           background: linear-gradient(135deg, var(--wl-accent), color-mix(in srgb, var(--wl-accent) 55%, #ff7a59)); }}
.wl-hero .wl-k {{ font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; opacity:.85; }}
.wl-hero .wl-t {{ font-family:"Bricolage Grotesque",system-ui,sans-serif; font-weight:800; font-size:1.6rem; line-height:1.15; }}
.wl-hero small {{ opacity:.9; }}
.wl-pontos {{ font-family:"Bricolage Grotesque",system-ui,sans-serif; font-weight:800; font-size:2.4rem; color:var(--wl-accent); line-height:1; }}
.wl-podio {{ display:flex; align-items:flex-end; justify-content:center; gap:.5rem; margin:.5rem 0 1rem; }}
.wl-degrau {{ flex:1; max-width:9rem; text-align:center; }}
.wl-degrau .wl-bloco {{ border-radius:12px 12px 0 0; background:var(--wl-soft); border:1px solid var(--wl-line);
                        font-family:"Bricolage Grotesque",system-ui,sans-serif; font-weight:800; font-size:1.5rem;
                        display:flex; align-items:flex-start; justify-content:center; padding-top:.4rem; }}
.wl-degrau.p1 .wl-bloco {{ height:6.5rem; background:var(--wl-accent); color:var(--wl-accent-ink); }}
.wl-degrau.p2 .wl-bloco {{ height:4.8rem; }}
.wl-degrau.p3 .wl-bloco {{ height:3.6rem; }}
.wl-degrau .wl-nome {{ font-weight:600; font-size:.9rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.wl-barra {{ display:flex; justify-content:space-between; align-items:center; gap:.6rem; margin:-1.5rem 0 .4rem; }}
.wl-placar {{ display:flex; gap:.4rem; }}
.wl-placar span {{ background:var(--wl-soft); border:1px solid var(--wl-line); border-radius:999px;
                  padding:.25rem .65rem; font-size:.9rem; white-space:nowrap; }}
/* o componente que pede o GPS não precisa aparecer (continua funcionando com altura zero) */
[data-testid="stElementContainer"]:has(iframe[title*="streamlit_js_eval"]) {{ height:0; min-height:0; overflow:hidden; margin:0; }}
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
                    'Point. Snap. Discover.</div>', unsafe_allow_html=True)
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
            from src.exemplo import gerar_capturas
            armazenamento.remover_capturas_exemplo()
            armazenamento.adicionar_capturas(gerar_capturas())
            st.toast("Dados de exemplo carregados")
        if st.button("Remover dados de exemplo", use_container_width=True):
            armazenamento.remover_capturas_exemplo()
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
        consentimento = st.checkbox("Concordo em guardar minhas capturas do jogo para análise anonimizada", key="cad_ok")
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


def badge(texto: str) -> str:
    return f'<span class="wl-badge">{texto}</span>'


def lista(linhas: list[tuple[str, str]]) -> str:
    """Lista HTML simples (segue o tema, ao contrário do st.dataframe)."""
    itens = "".join(f"<li><span>{a}</span><span class='wl-muted'>{b}</span></li>" for a, b in linhas)
    return f'<ul class="wl-list">{itens}</ul>'


def faixa_tema_do_dia(tema, outros) -> None:
    """Destaque do tema do dia (vale o dobro) e os outros temas, que valem sempre."""
    chips = "".join(badge(f"{t.emoji} {t.nome}") for t in outros if t.id != tema.id)
    st.markdown(
        f'<div class="wl-hero"><div class="wl-k">Tema do dia · pontos em dobro</div>'
        f'<div class="wl-t">{tema.emoji} {html.escape(tema.nome)}</div>'
        f'<small>Procure em {html.escape(tema.onde)}.</small></div>'
        f'<div style="margin:-.3rem 0 .6rem"><span class="wl-muted" style="font-size:.8rem">Também valem: </span>{chips}</div>',
        unsafe_allow_html=True)


def linha_juizes(juizes: dict | None, tema_final: str | None) -> str:
    """'Juízes: IA ✔ · CLIP ✔' (o CLIP leva ✖ quando o tema dele é outro)."""
    if not juizes or juizes.get("juiz") == "manual":
        return "Juiz: você (reconhecimento automático não instalado)"
    from src.jogo import normalizar_juiz

    juiz = normalizar_juiz(juizes["juiz"])
    partes = []
    if juiz in ("ia+clip", "ia"):
        partes.append("IA ✔")
    if juiz in ("ia+clip", "clip"):
        viu_tela = juizes.get("clip_foto_real") is False and tema_final != "pecas"
        concorda = juiz == "clip" or juizes.get("clip_tema") == tema_final
        partes.append("CLIP ✖ (viu tela)" if viu_tela else "CLIP " + ("✔" if concorda else "✖"))
    return "Juízes: " + " · ".join(partes)


def cartao_pontos(resultado: dict, tema, achado: str, vezes_antes: int, juizes: str = "") -> None:
    """Resultado de uma captura: pontos e parcelas, ou o motivo da recusa."""
    e = html.escape
    rodape = f'<div class="wl-muted" style="font-size:.75rem;margin-top:.4rem">{e(juizes)}</div>' if juizes else ""
    if not resultado.get("aceita"):
        st.markdown(
            f'<div class="wl-card"><div class="wl-pontos" style="color:var(--wl-muted)">0 pontos</div>'
            f'<div style="margin-top:.4rem">❌ {e(str(resultado.get("motivo") or "não valeu"))}</div>'
            f'<div class="wl-muted" style="font-size:.85rem;margin-top:.3rem">Vale só foto tirada agora, '
            f'de algo real na sua frente, de um dos temas.</div>{rodape}</div>', unsafe_allow_html=True)
        return
    partes = [f"base +{resultado['base']}"]
    if resultado["novidade"]:
        partes.append(f"novo pra você +{resultado['novidade']}")
    if resultado["raridade"]:
        partes.append(f"raridade +{resultado['raridade']}")
    if resultado["do_dia"]:
        partes.append("tema do dia ×2")
    if vezes_antes == 0 and resultado["raridade"]:
        destaque = "🥇 Primeira pessoa a achar isso!"
    elif vezes_antes:
        destaque = f"Já foi achado {vezes_antes}× pela turma."
    else:
        destaque = "Diga o modelo, a espécie ou a raça para ganhar mais pontos."
    st.markdown(
        f'<div class="wl-card"><div class="wl-muted" style="font-size:.8rem">{tema.emoji} {e(tema.nome)}</div>'
        f'<h3 style="margin:.1rem 0 .4rem">{e(achado[:1].upper() + achado[1:])}</h3>'
        f'<div class="wl-pontos">+{int(resultado["pontos"])} pontos</div>'
        f'<div style="margin:.5rem 0 .2rem">{"".join(badge(p) for p in partes)}</div>'
        f'<div class="wl-muted" style="font-size:.85rem">{destaque}</div>{rodape}</div>', unsafe_allow_html=True)


def nome_publico(usuario: str) -> str:
    return usuario.removeprefix("exemplo:")


def podio_html(ranking, eu: str | None = None) -> str:
    """Pódio de 3 degraus (2º, 1º, 3º) com nome e pontos."""
    ordem = [(2, "p2"), (1, "p1"), (3, "p3")]
    degraus = []
    for pos, classe in ordem:
        linha = ranking[ranking["posicao"] == pos]
        if linha.empty:
            degraus.append(f'<div class="wl-degrau {classe}"></div>')
            continue
        r = linha.iloc[0]
        nome = html.escape(nome_publico(str(r["usuario"]))) + (" (você)" if r["usuario"] == eu else "")
        medalha = {1: "🥇", 2: "🥈", 3: "🥉"}[pos]
        degraus.append(f'<div class="wl-degrau {classe}"><div style="font-size:1.6rem">{medalha}</div>'
                       f'<div class="wl-nome">{nome}</div><div class="wl-muted" style="font-size:.8rem">'
                       f'{int(r["pontos"])} pts</div><div class="wl-bloco">{pos}</div></div>')
    return f'<div class="wl-podio">{"".join(degraus)}</div>'
