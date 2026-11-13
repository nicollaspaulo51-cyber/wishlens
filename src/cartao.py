"""Textos do resultado de uma foto (o cartão de pontos), sem Streamlit: usados pelo app web e pelo servidor."""

from __future__ import annotations


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


def partes_e_destaque(resultado: dict, vezes_antes: int) -> tuple[list[str], list[str], str]:
    """(parcelas dos pontos, bônus, frase de destaque) de uma foto aceita."""
    partes = [f"base +{int(resultado['base'])}"]
    if resultado["novidade"]:
        partes.append(f"novo pra você +{int(resultado['novidade'])}")
    if resultado["raridade"]:
        partes.append(f"raridade +{int(resultado['raridade'])}")
    if resultado["do_dia"]:
        partes.append("tema do dia ×2")
    bonus = [d for d in str(resultado.get("detalhes") or "").split("; ") if d]
    if resultado.get("mesmo_objeto") == "turma":
        destaque = "Esse mesmo objeto já foi fotografado por alguém da turma aqui: vale, mas sem bônus de raridade."
    elif vezes_antes == 0 and resultado["raridade"]:
        destaque = "Você é a primeira pessoa a achar isso."
    elif vezes_antes:
        destaque = f"Já foi achado {vezes_antes}× pela turma."
    else:
        destaque = "Diga o modelo, a espécie ou a raça para ganhar mais pontos."
    return partes, bonus, destaque
