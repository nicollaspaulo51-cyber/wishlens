"""Partes de interface compartilhadas entre as páginas: paleta, barra lateral e estilos.

O tema (claro/escuro, fontes, cantos) é o nativo do Streamlit, em .streamlit/config.toml. Aqui ficam só as
cores que o tema nativo não alcança (mapa, gráficos, cartões em HTML) e as classes wl-*.
"""

import html

import streamlit as st

from src import armazenamento

# Mesmas cores do config.toml. "sol" é o amarelo da lupa do personagem: só pontos e tema do dia.
PALETA = {
    "claro": {"bg": "#EEF2EC", "surface": "#FFFFFF", "ink": "#12241D", "muted": "#4A5F55", "line": "#C9D4CB",
              "accent": "#136B4C", "accent_ink": "#FFFFFF", "soft": "#DDE8DF",
              "sol": "#FFC83D", "sol_ink": "#2A2000", "heat": "Greens"},
    "escuro": {"bg": "#0E1914", "surface": "#16251E", "ink": "#E4EEE8", "muted": "#A3B8AD", "line": "#2C4136",
               "accent": "#4CC793", "accent_ink": "#06130D", "soft": "#1E3329",
               "sol": "#FFC83D", "sol_ink": "#2A2000", "heat": "Emrld"},
}
TITULOS = '"Bricolage Grotesque", "Trebuchet MS", system-ui, sans-serif'


def tema() -> str:
    """'claro' ou 'escuro', conforme o tema do Streamlit (segue o aparelho; muda em ⋮ → Settings)."""
    try:
        return "escuro" if st.context.theme.type == "dark" else "claro"
    except Exception:  # fora de uma sessão (testes)
        return "claro"


def cores() -> dict:
    return PALETA[tema()]


def _css() -> str:
    c = cores()
    return f"""
<style>
:root {{ --wl-surface:{c['surface']}; --wl-ink:{c['ink']}; --wl-muted:{c['muted']}; --wl-line:{c['line']};
        --wl-accent:{c['accent']}; --wl-accent-ink:{c['accent_ink']}; --wl-soft:{c['soft']};
        --wl-sol:{c['sol']}; --wl-sol-ink:{c['sol_ink']}; --wl-titulos:{TITULOS}; }}
.wl-muted {{ color: var(--wl-muted); }}
.wl-card {{ padding: 1rem 1.1rem; border-radius: 14px; border: 1px solid var(--wl-line);
           background: var(--wl-surface); margin-bottom: .8rem; }}
.wl-badge {{ display:inline-block; padding:.15rem .6rem; border-radius:999px; font-size:.85rem;
            background: var(--wl-soft); color: var(--wl-ink); margin: 0 .3rem .3rem 0; }}
.wl-list {{ list-style:none; margin:0; padding:0; }}
.wl-list li {{ display:flex; justify-content:space-between; gap:.8rem; padding:.5rem 0;
              border-bottom:1px solid var(--wl-line); }}
.wl-list li:last-child {{ border-bottom:0; }}
.wl-list li span:last-child {{ text-align:right; }}
/* Barra do jogo: marca à esquerda, placar à direita */
.wl-barra {{ display:flex; justify-content:space-between; align-items:center; gap:.6rem; margin:-1.5rem 0 .6rem; }}
.wl-brand {{ font-family:var(--wl-titulos); font-weight:800; font-size:1.5rem; line-height:1; letter-spacing:-.02em; }}
.wl-placar {{ display:flex; gap:.4rem; }}
.wl-placar span {{ border:1px solid var(--wl-line); background:var(--wl-surface); border-radius:999px;
                  padding:.3rem .7rem; font-size:.9rem; white-space:nowrap; }}
.wl-placar b {{ font-family:var(--wl-titulos); }}
/* Selo do tema do dia: o único bloco amarelo da tela */
.wl-selo {{ display:flex; align-items:center; gap:.8rem; padding:.7rem .9rem; border-radius:14px;
           background:var(--wl-sol); color:var(--wl-sol-ink); margin-bottom:.7rem; }}
.wl-selo .wl-emoji {{ font-size:2rem; line-height:1; }}
.wl-selo .wl-t {{ font-family:var(--wl-titulos); font-weight:800; font-size:1.25rem; line-height:1.15; }}
.wl-selo .wl-dobro {{ margin-left:auto; font-family:var(--wl-titulos); font-weight:800; font-size:1.7rem; line-height:1; }}
.wl-selo small {{ display:block; font-size:.85rem; }}
/* Resultado da foto */
.wl-pontos {{ font-family:var(--wl-titulos); font-weight:800; font-size:3rem; line-height:1; letter-spacing:-.03em; }}
.wl-pontos small {{ font-size:1.1rem; letter-spacing:0; }}
.wl-valeu {{ border-left:8px solid var(--wl-sol); }}
.wl-recusa .wl-pontos {{ color:var(--wl-muted); }}
.wl-estilo {{ font-family:var(--wl-titulos); font-weight:800; font-size:1.7rem; line-height:1.15; color:var(--wl-accent); }}
/* Pódio */
.wl-podio {{ display:flex; align-items:flex-end; justify-content:center; gap:.5rem; margin:.5rem 0 1rem; }}
.wl-degrau {{ flex:1; max-width:9rem; text-align:center; min-width:0; }}
.wl-degrau .wl-bloco {{ border-radius:12px 12px 0 0; background:var(--wl-soft); border:1px solid var(--wl-line);
                        font-family:var(--wl-titulos); font-weight:800; font-size:1.6rem;
                        display:flex; align-items:flex-start; justify-content:center; padding-top:.4rem; }}
.wl-degrau.p1 .wl-bloco {{ height:6.5rem; background:var(--wl-sol); color:var(--wl-sol-ink); border-color:var(--wl-sol); }}
.wl-degrau.p2 .wl-bloco {{ height:4.8rem; }}
.wl-degrau.p3 .wl-bloco {{ height:3.6rem; }}
.wl-degrau .wl-nome {{ font-weight:700; font-size:.95rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
/* o componente que pede o GPS não precisa aparecer (continua funcionando com altura zero) */
[data-testid="stElementContainer"]:has(iframe[title*="streamlit_js_eval"]) {{ height:0; min-height:0; overflow:hidden; margin:0; }}
</style>
"""


def configurar(titulo: str, icone: str = "🔍") -> None:
    st.set_page_config(page_title=f"WishLens · {titulo}", page_icon=icone, layout="centered")
    st.markdown(_css(), unsafe_allow_html=True)
    barra_lateral()


def barra_lateral() -> None:
    with st.sidebar:
        st.markdown('<div class="wl-brand">WishLens</div><div class="wl-muted" style="font-size:.85rem">'
                    'Point. Snap. Discover.</div>', unsafe_allow_html=True)

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
        font=dict(family="Atkinson Hyperlegible, system-ui, sans-serif", color=c["ink"]),
        height=altura, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="",
    )
    return fig


def badge(texto: str) -> str:
    return f'<span class="wl-badge">{texto}</span>'


def lista(linhas: list[tuple[str, str]]) -> str:
    """Lista HTML simples (segue o tema, ao contrário do st.dataframe)."""
    itens = "".join(f"<li><span>{a}</span><span class='wl-muted'>{b}</span></li>" for a, b in linhas)
    return f'<ul class="wl-list">{itens}</ul>'


def selo_tema_do_dia(tema) -> str:
    """Bloco amarelo com o tema do dia (vale o dobro): o destaque da tela de jogo."""
    return (f'<div class="wl-selo"><span class="wl-emoji" aria-hidden="true">{tema.emoji}</span>'
            f'<div><div class="wl-t">{html.escape(tema.nome)}</div><small>Tema de hoje. Procure em '
            f'{html.escape(tema.onde)}.</small></div><div class="wl-dobro" aria-label="pontos em dobro">×2</div></div>')


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
    rodape = f'<div class="wl-muted" style="font-size:.8rem;margin-top:.5rem">{e(juizes)}</div>' if juizes else ""
    if not resultado.get("aceita"):
        st.markdown(
            f'<div class="wl-card wl-recusa"><div class="wl-pontos">0 <small>pontos</small></div>'
            f'<div style="margin-top:.5rem"><b>Não valeu:</b> {e(str(resultado.get("motivo") or "foto recusada"))}.</div>'
            f'<div class="wl-muted" style="font-size:.9rem;margin-top:.3rem">Vale foto tirada agora, '
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
        destaque = "Você é a primeira pessoa a achar isso."
    elif vezes_antes:
        destaque = f"Já foi achado {vezes_antes}× pela turma."
    else:
        destaque = "Diga o modelo, a espécie ou a raça para ganhar mais pontos."
    st.markdown(
        f'<div class="wl-card wl-valeu"><div class="wl-pontos">+{int(resultado["pontos"])} <small>pontos</small></div>'
        f'<h3 style="margin:.5rem 0 0;padding:0">{e(achado[:1].upper() + achado[1:])}</h3>'
        f'<div class="wl-muted" style="font-size:.9rem">{tema.emoji} {e(tema.nome)}</div>'
        f'<div style="margin:.6rem 0 .2rem">{"".join(badge(p) for p in partes)}</div>'
        f'<div class="wl-muted" style="font-size:.9rem">{destaque}</div>{rodape}</div>', unsafe_allow_html=True)


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
