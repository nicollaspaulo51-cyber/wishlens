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
/* Painel do dia: lupa, corrente, meta da turma e desafios */
.wl-dia {{ display:grid; grid-template-columns:auto 1fr; gap:.5rem .8rem; align-items:center; margin:-.2rem 0 .7rem;
          font-size:.92rem; }}
.wl-lupa {{ display:flex; gap:3px; }}
.wl-lupa i {{ width:18px; height:8px; border-radius:4px; background:var(--wl-line); }}
.wl-lupa i.on {{ background:var(--wl-accent); }}
.wl-lupa.cheia i {{ background:var(--wl-sol); animation:wl-brilho 1.4s ease-in-out infinite; }}
@keyframes wl-brilho {{ 50% {{ filter:brightness(1.25); }} }}
.wl-meta {{ grid-column:1 / -1; border:1px solid var(--wl-line); border-radius:12px; padding:.5rem .7rem;
           background:var(--wl-surface); }}
.wl-meta .wl-trilho {{ height:8px; border-radius:4px; background:var(--wl-soft); margin-top:.35rem; overflow:hidden; }}
.wl-meta .wl-trilho b {{ display:block; height:100%; background:var(--wl-accent); transition:width .8s ease-out; }}
.wl-desafios-box {{ grid-column:1 / -1; }}
.wl-desafios-box summary {{ cursor:pointer; min-height:44px; display:flex; align-items:center; gap:.3rem; }}
.wl-desafios {{ list-style:none; margin:0; padding:0 0 .3rem; display:flex; flex-direction:column; gap:.2rem; }}
.wl-desafios li {{ display:flex; gap:.5rem; align-items:baseline; }}
.wl-desafios li.ok {{ color:var(--wl-muted); text-decoration:line-through; }}
.wl-desafios .wl-marca {{ font-weight:700; color:var(--wl-accent); min-width:2.2rem; }}
/* Pontos que contam de 0 até o total (sem @property, aparece o número final direto) */
@property --wl-n {{ syntax:'<integer>'; initial-value:0; inherits:false; }}
.wl-conta {{ --wl-n:var(--fim); counter-reset:wl var(--wl-n); animation:wl-contar 1.1s cubic-bezier(.2,.8,.2,1); }}
.wl-conta::before {{ content:"+" counter(wl); }}
@keyframes wl-contar {{ from {{ --wl-n:0; }} }}
.wl-badge.wl-bonus {{ background:var(--wl-sol); color:var(--wl-sol-ink); }}
.wl-sr {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.wl-medalhas {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(9.5rem, 1fr)); gap:.5rem; margin-bottom:.8rem; }}
.wl-medalha {{ border:1px solid var(--wl-line); border-radius:12px; padding:.6rem .7rem; background:var(--wl-surface); }}
.wl-medalha b {{ display:block; font-family:var(--wl-titulos); }}
.wl-medalha.bronze {{ border-color:#B87333; }} .wl-medalha.prata {{ border-color:#9AA5AD; }}
.wl-medalha.ouro {{ border-color:var(--wl-sol); background:color-mix(in srgb, var(--wl-sol) 18%, var(--wl-surface)); }}
.wl-medalha.nada {{ opacity:.7; }}
@media (prefers-reduced-motion: reduce) {{ .wl-conta, .wl-lupa.cheia i {{ animation:none; }}
  .wl-meta .wl-trilho b {{ transition:none; }} }}
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


def badge(texto: str, classe: str = "") -> str:
    return f'<span class="wl-badge {classe}">{texto}</span>'


def lista(linhas: list[tuple[str, str]]) -> str:
    """Lista HTML simples (segue o tema, ao contrário do st.dataframe)."""
    itens = "".join(f"<li><span>{a}</span><span class='wl-muted'>{b}</span></li>" for a, b in linhas)
    return f'<ul class="wl-list">{itens}</ul>'


def selo_tema_do_dia(tema) -> str:
    """Bloco amarelo com o tema do dia (vale o dobro): o destaque da tela de jogo."""
    return (f'<div class="wl-selo"><span class="wl-emoji" aria-hidden="true">{tema.emoji}</span>'
            f'<div><div class="wl-t">{html.escape(tema.nome)}</div><small>Tema de hoje. Procure em '
            f'{html.escape(tema.onde)}.</small></div><div class="wl-dobro" aria-label="pontos em dobro">×2</div></div>')


def painel_do_dia(estado: dict, corrente: int, meta: dict) -> str:
    """Lupa (3 partes), corrente de dias, meta da turma e os 3 desafios do dia (jogo.estado_do_dia)."""
    e = html.escape
    carga = estado["lupa"]
    partes = "".join(f'<i class="{"on" if k < carga else ""}"></i>' for k in range(3))
    lupa_txt = "Lupa cheia: o próximo achado vale +50%" if estado["lupa_cheia"] else f"Lupa {carga}/3 temas"
    lupa = (f'<div class="wl-lupa {"cheia" if estado["lupa_cheia"] else ""}" role="img" aria-label="{e(lupa_txt)}">'
            f'{partes}</div><div>{e(lupa_txt)}'
            + (f'. Corrente: <b>{corrente} {"dia" if corrente == 1 else "dias"}</b>' if corrente else "") + '</div>')
    t = meta["tema"]
    if meta["cumprida"]:
        meta_txt = f"Meta da turma cumprida: {meta['feitas']} fotos de {t.nome.lower()}. Cada uma ganhou +10."
    elif meta["aberta"]:
        meta_txt = (f"Meta da turma: {meta['feitas']} de {meta['alvo']} fotos de {t.nome.lower()}. "
                    f"Faltam {meta['faltam_min']} min.")
    else:
        meta_txt = (f"Meta da turma, das {meta['comeca']} às {meta['termina']}: {meta['alvo']} fotos de "
                    f"{t.nome.lower()}. Todos que ajudarem ganham +10 por foto.")
    largura = min(100, round(100 * meta["feitas"] / meta["alvo"]))
    meta_html = (f'<div class="wl-meta">{e(meta_txt)}<div class="wl-trilho" role="progressbar" aria-valuemin="0" '
                 f'aria-valuemax="{meta["alvo"]}" aria-valuenow="{meta["feitas"]}"><b style="width:{largura}%"></b>'
                 f'</div></div>')
    itens = ""
    for d in estado["desafios"]:
        marca = "✔" if d["ok"] else f'{d["feito"]}/{d["alvo"]}'
        itens += (f'<li class="{"ok" if d["ok"] else ""}"><span class="wl-marca">{marca}</span>'
                  f'<span>{e(d["texto"])} (+15)</span></li>')
    feitos = sum(d["ok"] for d in estado["desafios"])
    # recolhido: no celular o mapa precisa aparecer sem rolar muito
    return (f'<div class="wl-dia">{lupa}{meta_html}<details class="wl-desafios-box"><summary>Desafios do dia: '
            f'<b>{feitos} de {len(estado["desafios"])}</b> feitos</summary>'
            f'<ul class="wl-desafios">{itens}</ul></details></div>')


def medalhas_html(lista_medalhas: list[dict]) -> str:
    e = html.escape
    cartoes = []
    for m in lista_medalhas:
        nivel = m["nivel"] or "nada"
        falta = f'faltam {m["proximo"]} para o próximo nível' if m["proximo"] else "nível máximo"
        cartoes.append(f'<div class="wl-medalha {nivel}"><b>{e(m["nome"])}</b>'
                       f'<span>{e(m["nivel"] or "ainda sem nível")}</span><br>'
                       f'<span class="wl-muted" style="font-size:.85rem">{m["valor"]} {e(m["conta"])}, {falta}</span></div>')
    return f'<div class="wl-medalhas">{"".join(cartoes)}</div>'


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
    pontos = int(resultado["pontos"])
    bonus = [d for d in str(resultado.get("detalhes") or "").split("; ") if d]
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
        f'<div class="wl-card wl-valeu"><div class="wl-pontos"><span class="wl-conta" style="--fim:{pontos}" '
        f'aria-hidden="true"></span><span class="wl-sr">+{pontos}</span> <small>pontos</small></div>'
        f'<h3 style="margin:.5rem 0 0;padding:0">{e(achado[:1].upper() + achado[1:])}</h3>'
        f'<div class="wl-muted" style="font-size:.9rem">{tema.emoji} {e(tema.nome)}</div>'
        f'<div style="margin:.6rem 0 .2rem">{"".join(badge(p) for p in partes)}'
        f'{"".join(badge(e(b), "wl-bonus") for b in bonus)}</div>'
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
