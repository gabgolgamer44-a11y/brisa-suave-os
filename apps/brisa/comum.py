"""Funções usadas por todos os apps do Brisa Suave OS.

Nada aqui precisa de permissão de administrador: o que precisa passa pelo
ajudante /usr/lib/brisa/brisa-helper, chamado com pkexec.
"""
import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

HELPER = "/usr/lib/brisa/brisa-helper"
ARQ_MODO = Path("/run/brisa/modo")
ARQ_VERSAO = Path("/etc/brisa-release")
CATALOGO = Path("/usr/share/brisa/store/catalogo.json")
PAPEIS = Path("/usr/share/brisa/wallpapers")
ICONES = Path("/usr/share/brisa/icones")
CACHE = Path.home() / ".cache" / "brisa"
CONFIG = Path.home() / ".config" / "brisa"

AZUL = "#2F86E8"

TEMAS = {
    "azul": {"nome": "Azul", "cor": "#2F86E8", "papel": "brisa-azul.svg", "escuro": False},
    "roxo": {"nome": "Roxo", "cor": "#7B3FE4", "papel": "brisa-roxo.svg", "escuro": False},
    "verde": {"nome": "Verde", "cor": "#1F9E6E", "papel": "brisa-verde.svg", "escuro": False},
    "laranja": {"nome": "Laranja", "cor": "#E8742F", "papel": "brisa-laranja.svg", "escuro": False},
    "escuro": {"nome": "Escuro", "cor": "#4FA8FF", "papel": "brisa-escuro.svg", "escuro": True},
}

MODOS = {
    "normal": "Normal",
    "economia": "Economia",
    "gamer": "Gamer",
}


# ---------------------------------------------------------------- sistema

def info_brisa() -> dict:
    """Lê /etc/brisa-release (VERSAO, VARIANTE, BASE)."""
    dados = {"VERSAO": "?", "VARIANTE": "pc64", "BASE": "Debian"}
    try:
        for linha in ARQ_VERSAO.read_text(encoding="utf-8").splitlines():
            if "=" in linha:
                chave, valor = linha.split("=", 1)
                dados[chave.strip()] = valor.strip().strip('"')
    except OSError:
        pass
    return dados


def modo_atual() -> str:
    try:
        modo = ARQ_MODO.read_text().strip()
        return modo if modo in MODOS else "normal"
    except OSError:
        return "normal"


def rodar(cmd, timeout=60) -> tuple:
    """Roda um comando e devolve (código, saída)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as erro:
        return 1, str(erro)


def rodar_helper(*args, timeout=600) -> tuple:
    return rodar(["pkexec", HELPER, *args], timeout=timeout)


def rodar_helper_ao_vivo(args, ao_receber_linha, ao_terminar):
    """Roda o ajudante numa thread e entrega cada linha da saída.

    As funções de retorno são chamadas na thread da interface (GLib.idle_add).
    """
    from gi.repository import GLib

    def trabalho():
        try:
            proc = subprocess.Popen(
                ["pkexec", HELPER, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as erro:
            GLib.idle_add(ao_terminar, 1, str(erro))
            return
        ultimas = []
        for linha in proc.stdout:
            linha = linha.rstrip("\n")
            ultimas = (ultimas + [linha])[-15:]
            GLib.idle_add(ao_receber_linha, linha)
        codigo = proc.wait()
        GLib.idle_add(ao_terminar, codigo, "\n".join(ultimas))

    threading.Thread(target=trabalho, daemon=True).start()


def em_segundo_plano(funcao, ao_terminar=None):
    """Roda funcao() numa thread e entrega o resultado na thread da interface."""
    from gi.repository import GLib

    def trabalho():
        resultado = funcao()
        if ao_terminar:
            GLib.idle_add(ao_terminar, resultado)

    threading.Thread(target=trabalho, daemon=True).start()


def notificar(titulo, texto, icone="brisa-central"):
    caminho = ICONES / f"{icone}.svg"
    cmd = ["notify-send", "-a", "Brisa Suave OS", titulo, texto]
    if caminho.exists():
        cmd[1:1] = ["-i", str(caminho)]
    rodar(cmd, timeout=10)


# ---------------------------------------------------------------- xfconf

def xfconf_ler(canal, propriedade):
    codigo, saida = rodar(["xfconf-query", "-c", canal, "-p", propriedade], timeout=10)
    return saida if codigo == 0 else None


def xfconf_gravar(canal, propriedade, valor, tipo="string"):
    if isinstance(valor, bool):
        valor = "true" if valor else "false"
    rodar(["xfconf-query", "-c", canal, "-p", propriedade, "-n", "-t", tipo, "-s", str(valor)], timeout=10)


# ---------------------------------------------------------------- aparência

def _monitores():
    codigo, saida = rodar(["xrandr", "--listmonitors"], timeout=10)
    nomes = []
    if codigo == 0:
        for linha in saida.splitlines()[1:]:
            partes = linha.split()
            if partes:
                nomes.append(partes[-1])
    return nomes


def aplicar_papel_de_parede(caminho: str):
    """Coloca a imagem como papel de parede em todos os monitores."""
    codigo, saida = rodar(["xfconf-query", "-c", "xfce4-desktop", "-l"], timeout=10)
    props = [p for p in saida.splitlines() if p.endswith("/last-image")] if codigo == 0 else []
    if not props:
        props = [f"/backdrop/screen0/monitor{nome}/workspace0/last-image" for nome in _monitores()]
        props.append("/backdrop/screen0/monitor0/workspace0/last-image")
    for prop in props:
        base = prop.rsplit("/", 1)[0]
        xfconf_gravar("xfce4-desktop", f"{base}/image-style", 5, "int")  # 5 = ampliado
        xfconf_gravar("xfce4-desktop", prop, caminho)


CSS_DESTAQUE = """/* Brisa Suave OS: cor de destaque ({nome}). Gerado pelo Brisa Suave Central. */
@define-color brisa_destaque {cor};
*:selected, selection, row:selected, .view:selected, treeview.view:selected,
menuitem:hover, menu menuitem:hover {{ background-color: @brisa_destaque; color: #FFFFFF; }}
progressbar progress, scale highlight, switch:checked, levelbar block.filled {{
  background-color: @brisa_destaque; border-color: @brisa_destaque; }}
entry:focus {{ border-color: @brisa_destaque; }}
"""


def aplicar_tema(chave: str):
    tema = TEMAS.get(chave, TEMAS["azul"])
    aplicar_papel_de_parede(str(PAPEIS / tema["papel"]))
    xfconf_gravar("xsettings", "/Net/ThemeName", "Arc-Dark" if tema["escuro"] else "Arc")
    xfconf_gravar("xsettings", "/Net/IconThemeName", "Papirus-Dark" if tema["escuro"] else "Papirus")
    xfconf_gravar("xfwm4", "/general/theme", "Arc-Dark")
    gtk = Path.home() / ".config" / "gtk-3.0"
    gtk.mkdir(parents=True, exist_ok=True)
    (gtk / "gtk.css").write_text(CSS_DESTAQUE.format(nome=tema["nome"], cor=tema["cor"]), encoding="utf-8")
    CONFIG.mkdir(parents=True, exist_ok=True)
    (CONFIG / "tema").write_text(chave, encoding="utf-8")


def tema_atual() -> str:
    try:
        chave = (CONFIG / "tema").read_text(encoding="utf-8").strip()
        return chave if chave in TEMAS else "azul"
    except OSError:
        return "azul"


# ---------------------------------------------------------------- informações

class LeitorCPU:
    """Calcula o uso do processador entre duas leituras de /proc/stat."""

    def __init__(self):
        self._antes = self._ler()

    @staticmethod
    def _ler():
        try:
            campos = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
            valores = [int(v) for v in campos]
            ocioso = valores[3] + (valores[4] if len(valores) > 4 else 0)
            return sum(valores), ocioso
        except (OSError, ValueError, IndexError):
            return 0, 0

    def uso(self) -> float:
        total, ocioso = self._ler()
        total_antes, ocioso_antes = self._antes
        self._antes = (total, ocioso)
        delta = total - total_antes
        if delta <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * (1 - (ocioso - ocioso_antes) / delta)))


def memoria() -> tuple:
    """(usada, total) em bytes."""
    dados = {}
    try:
        for linha in Path("/proc/meminfo").read_text().splitlines():
            chave, valor = linha.split(":", 1)
            dados[chave] = int(valor.split()[0]) * 1024
    except (OSError, ValueError):
        return 0, 0
    total = dados.get("MemTotal", 0)
    return total - dados.get("MemAvailable", 0), total


def disco() -> tuple:
    uso = shutil.disk_usage("/")
    return uso.used, uso.total


def temperatura():
    maiores = []
    for zona in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            maiores.append(int(zona.read_text().strip()) / 1000)
        except (OSError, ValueError):
            pass
    validas = [t for t in maiores if 0 < t < 150]
    return max(validas) if validas else None


def frequencia_mhz():
    try:
        return int(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read_text()) // 1000
    except (OSError, ValueError):
        return None


def bateria():
    """(porcentagem, situação) ou None se não tiver bateria."""
    for bat in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        try:
            carga = int((bat / "capacity").read_text().strip())
            situacao = (bat / "status").read_text().strip()
        except (OSError, ValueError):
            continue
        traducao = {"Charging": "carregando", "Discharging": "na bateria", "Full": "carregada",
                    "Not charging": "na tomada"}
        return carga, traducao.get(situacao, situacao.lower())
    return None


def modelo_processador() -> str:
    try:
        texto = Path("/proc/cpuinfo").read_text()
    except OSError:
        texto = ""
    achado = re.search(r"^model name\s*:\s*(.+)$", texto, re.M)
    if achado:
        return re.sub(r"\s+", " ", achado.group(1)).strip()
    try:
        return Path("/proc/device-tree/model").read_text().strip("\x00\n ")
    except OSError:
        return f"{os.cpu_count()} núcleos"


def bytes_legivel(valor: float) -> str:
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if valor < 1024 or unidade == "TB":
            return f"{valor:.1f} {unidade}".replace(".", ",") if unidade != "B" else f"{int(valor)} B"
        valor /= 1024
    return str(valor)


# ---------------------------------------------------------------- loja

def carregar_catalogo() -> dict:
    try:
        return json.loads(CATALOGO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"categorias": [], "apps": []}


def apps_da_variante(catalogo: dict, variante: str) -> list:
    return [app for app in catalogo.get("apps", [])
            if not app.get("somente") or variante in app["somente"]]


def pacotes_disponiveis(pacotes) -> set:
    """Pacotes que existem nos repositórios configurados."""
    pacotes = sorted(set(pacotes))
    if not pacotes:
        return set()
    codigo, saida = rodar(["apt-cache", "policy", *pacotes], timeout=120)
    disponiveis, atual = set(), None
    for linha in saida.splitlines():
        if linha and not linha.startswith(" ") and linha.endswith(":"):
            atual = linha[:-1]
        elif atual and linha.strip().startswith("Candidat") and "(none)" not in linha and "(nenhum)" not in linha:
            disponiveis.add(atual)
    return disponiveis


def pacotes_instalados(pacotes) -> set:
    pacotes = sorted(set(pacotes))
    if not pacotes:
        return set()
    codigo, saida = rodar(["dpkg-query", "-W", "-f=${Package} ${db:Status-Status}\n", *pacotes], timeout=60)
    return {linha.split()[0] for linha in saida.splitlines()
            if linha.endswith(" installed") and not linha.startswith("dpkg-query")}


# ---------------------------------------------------------------- interface

CSS_APPS = b"""
.brisa-titulo { font-size: 20px; font-weight: bold; }
.brisa-subtitulo { opacity: 0.75; }
.brisa-cartao { padding: 14px; border-radius: 10px; }
.brisa-modo { padding: 18px 12px; border-radius: 12px; }
.brisa-modo-ativo { background-color: #2F86E8; color: #FFFFFF; }
.brisa-modo-ativo label { color: #FFFFFF; }
.brisa-leve { background-color: #1F9E6E; color: #FFFFFF; border-radius: 6px; padding: 1px 8px; font-size: 11px; }
.brisa-pesado { background-color: #E8742F; color: #FFFFFF; border-radius: 6px; padding: 1px 8px; font-size: 11px; }
.brisa-numero { font-size: 28px; font-weight: bold; }
.brisa-relogio { font-size: 44px; font-weight: 300; }
.brisa-botao-azul { background-image: none; background-color: #2F86E8; color: #FFFFFF; }
"""


def aplicar_css():
    from gi.repository import Gdk, Gtk
    provedor = Gtk.CssProvider()
    provedor.load_from_data(CSS_APPS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provedor, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def imagem_de_arquivo(caminho, tamanho):
    from gi.repository import GdkPixbuf, Gtk
    try:
        pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(caminho), tamanho, tamanho, True)
        return Gtk.Image.new_from_pixbuf(pix)
    except Exception:  # noqa: BLE001 - imagem faltando não pode derrubar o app
        return Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.DIALOG)


def icone(nome, tamanho=48):
    """Ícone do tema (Papirus) pelo nome, ou um arquivo se for caminho."""
    from gi.repository import Gtk
    if nome and nome.startswith("/"):
        return imagem_de_arquivo(nome, tamanho)
    tema = Gtk.IconTheme.get_default()
    if not nome or not tema.has_icon(nome):
        nome = "application-x-executable"
    imagem = Gtk.Image.new_from_icon_name(nome, Gtk.IconSize.DIALOG)
    imagem.set_pixel_size(tamanho)
    return imagem


def mensagem(janela, titulo, texto, tipo="info"):
    from gi.repository import Gtk
    tipos = {"info": Gtk.MessageType.INFO, "erro": Gtk.MessageType.ERROR, "aviso": Gtk.MessageType.WARNING}
    dialogo = Gtk.MessageDialog(transient_for=janela, modal=True, message_type=tipos[tipo],
                                buttons=Gtk.ButtonsType.OK, text=titulo)
    dialogo.format_secondary_text(texto)
    dialogo.run()
    dialogo.destroy()
