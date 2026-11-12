"""brisa-modo: troca entre os modos Normal, Economia e Gamer.

Uso:
  brisa-modo normal | economia | gamer
  brisa-modo alternar-gamer      (atalho Windows + G)
  brisa-modo atual

A parte do sistema (processador, brilho, tarefas de fundo) é feita pelo
ajudante como administrador. A parte da sessão (efeitos visuais e
notificações) é feita aqui, como usuário, e volta ao normal depois.
"""
import json
import sys

from brisa import comum

ARQ_ANTES = comum.CACHE / "antes-do-modo.json"

TEXTOS = {
    "normal": ("Modo Normal", "Desempenho equilibrado."),
    "economia": ("Modo Economia ligado", "Processador e brilho reduzidos para gastar menos."),
    "gamer": ("Modo Gamer ligado", "Processador no máximo, tarefas de fundo pausadas e notificações silenciadas."),
}


def _guardar_estado_da_sessao():
    """Guarda como a sessão estava antes de sair do modo Normal."""
    if ARQ_ANTES.exists():
        return
    estado = {
        "compositor": comum.xfconf_ler("xfwm4", "/general/use_compositing") or "true",
        "nao_perturbe": comum.xfconf_ler("xfce4-notifyd", "/do-not-disturb") or "false",
    }
    comum.CACHE.mkdir(parents=True, exist_ok=True)
    ARQ_ANTES.write_text(json.dumps(estado), encoding="utf-8")


def _restaurar_estado_da_sessao():
    try:
        estado = json.loads(ARQ_ANTES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        estado = {"compositor": "true", "nao_perturbe": "false"}
    comum.xfconf_gravar("xfwm4", "/general/use_compositing", estado["compositor"] == "true", "bool")
    comum.xfconf_gravar("xfce4-notifyd", "/do-not-disturb", estado["nao_perturbe"] == "true", "bool")
    try:
        ARQ_ANTES.unlink()
    except OSError:
        pass


def mudar_modo(novo: str, avisar: bool = True) -> tuple:
    """Troca o modo. Devolve (deu_certo, mensagem)."""
    if novo not in comum.MODOS:
        return False, f"Modo desconhecido: {novo}"
    anterior = comum.modo_atual()
    if novo != "normal" and anterior == "normal":
        _guardar_estado_da_sessao()

    # o aviso sai antes de silenciar as notificações do modo gamer
    if avisar and novo == "gamer":
        comum.notificar(*TEXTOS[novo], icone="brisa-gamer")

    codigo, saida = comum.rodar_helper("modo", novo, timeout=60)
    if codigo != 0:
        return False, saida or "Não foi possível trocar o modo."

    if novo == "normal":
        _restaurar_estado_da_sessao()
    elif novo == "economia":
        comum.xfconf_gravar("xfwm4", "/general/use_compositing", False, "bool")
        comum.xfconf_gravar("xfce4-notifyd", "/do-not-disturb", False, "bool")
    elif novo == "gamer":
        comum.xfconf_gravar("xfwm4", "/general/use_compositing", False, "bool")
        comum.xfconf_gravar("xfce4-notifyd", "/do-not-disturb", True, "bool")

    if avisar and novo != "gamer":
        comum.notificar(*TEXTOS[novo])
    return True, TEXTOS[novo][0]


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "ajuda"):
        print(__doc__)
        return 0
    if args[0] == "atual":
        print(comum.modo_atual())
        return 0
    novo = args[0]
    if novo == "alternar-gamer":
        novo = "normal" if comum.modo_atual() == "gamer" else "gamer"
    ok, texto = mudar_modo(novo)
    print(texto)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
