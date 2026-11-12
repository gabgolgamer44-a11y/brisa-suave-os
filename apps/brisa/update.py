"""Brisa Suave Update: procura e instala atualizações.

  brisa-update           abre a janela
  brisa-update --vigiar  fica de olho e avisa quando houver atualização (roda no login)
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from brisa import comum

ULTIMA_VERIFICACAO = comum.CACHE / "ultima-verificacao"
HISTORICO_APT = Path("/var/log/apt/history.log")
UM_DIA = 24 * 60 * 60


# ---------------------------------------------------------------- sem interface

def listar_atualizacoes() -> list:
    """[(pacote, versão_atual, versão_nova)] do que pode ser atualizado."""
    env = dict(os.environ, LANG="C", LC_ALL="C")
    try:
        saida = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True,
                               env=env, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    lista = []
    for linha in saida.splitlines():
        if "/" not in linha or "[upgradable from:" not in linha:
            continue
        nome = linha.split("/", 1)[0]
        partes = linha.split()
        nova = partes[1] if len(partes) > 1 else "?"
        atual = linha.rsplit("[upgradable from:", 1)[1].strip(" ]")
        lista.append((nome, atual, nova))
    return lista


def tamanho_download(pacotes) -> int:
    if not pacotes:
        return 0
    env = dict(os.environ, LANG="C", LC_ALL="C")
    try:
        saida = subprocess.run(["apt-cache", "show", "--no-all-versions", *pacotes], capture_output=True,
                               text=True, env=env, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return 0
    total = 0
    for linha in saida.splitlines():
        if linha.startswith("Size:"):
            try:
                total += int(linha.split(":", 1)[1])
            except ValueError:
                pass
    return total


def ler_historico(limite=40) -> list:
    """[(data, resumo)] das últimas mudanças feitas pelo apt."""
    try:
        texto = HISTORICO_APT.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    registros = []
    for bloco in texto.split("\n\n"):
        dados = {}
        for linha in bloco.strip().splitlines():
            if ": " in linha:
                chave, valor = linha.split(": ", 1)
                dados[chave] = valor
        if "Start-Date" not in dados:
            continue

        def contar(chave):
            valor = dados.get(chave, "")
            return valor.count("), ") + 1 if valor else 0

        partes = []
        for chave, nome in (("Upgrade", "atualizados"), ("Install", "instalados"), ("Remove", "removidos"),
                            ("Purge", "removidos")):
            quantidade = contar(chave)
            if quantidade:
                partes.append(f"{quantidade} {nome}")
        if partes:
            registros.append((dados["Start-Date"].replace("  ", " "), ", ".join(partes)))
    return list(reversed(registros))[:limite]


def _marcar_verificacao():
    comum.CACHE.mkdir(parents=True, exist_ok=True)
    ULTIMA_VERIFICACAO.write_text(str(int(time.time())))


def _precisa_verificar() -> bool:
    try:
        return time.time() - int(ULTIMA_VERIFICACAO.read_text().strip()) > UM_DIA
    except (OSError, ValueError):
        return True


def _avisar(quantidade):
    titulo = "Atualizações disponíveis"
    texto = f"{quantidade} atualização pronta para instalar." if quantidade == 1 else \
        f"{quantidade} atualizações prontas para instalar."
    icone = str(comum.ICONES / "brisa-update.svg")
    try:
        resposta = subprocess.run(
            ["notify-send", "-a", "Brisa Suave Update", "-i", icone, "-A", "abrir=Atualizar agora",
             titulo, texto], capture_output=True, text=True, timeout=1800).stdout.strip()
    except subprocess.TimeoutExpired:
        return
    except OSError:
        return
    if resposta == "abrir":
        subprocess.Popen(["brisa-update"], start_new_session=True)


def vigiar():
    time.sleep(180)  # deixa o computador terminar de ligar
    while True:
        if comum.modo_atual() != "gamer" and _precisa_verificar():
            codigo, _ = comum.rodar_helper("atualizar-lista", timeout=900)
            if codigo == 0:
                _marcar_verificacao()
                quantidade = len(listar_atualizacoes())
                if quantidade:
                    _avisar(quantidade)
        time.sleep(1800)


# ---------------------------------------------------------------- janela

def abrir_janela():
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk, Pango

    class JanelaUpdate(Gtk.Window):
        def __init__(self):
            super().__init__(title="Brisa Suave Update")
            self.set_default_size(760, 560)
            self.set_icon_from_file(str(comum.ICONES / "brisa-update.svg"))
            self.ocupado = False

            abas = Gtk.Notebook()
            abas.append_page(self._montar_atualizacoes(), Gtk.Label(label="Atualizações"))
            abas.append_page(self._montar_historico(), Gtk.Label(label="Histórico"))
            abas.connect("switch-page", lambda _a, _p, numero: numero == 1 and self._carregar_historico())
            self.add(abas)
            GLib.idle_add(self.procurar)

        # ------------------------------------------------ aba atualizações
        def _montar_atualizacoes(self):
            caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            caixa.set_border_width(20)
            topo = Gtk.Box(spacing=14)
            topo.pack_start(comum.imagem_de_arquivo(comum.ICONES / "brisa-update.svg", 56), False, False, 0)
            textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
            self.titulo = Gtk.Label(label="Procurando atualizações...", xalign=0)
            self.titulo.get_style_context().add_class("brisa-titulo")
            self.subtitulo = Gtk.Label(xalign=0, wrap=True)
            self.subtitulo.get_style_context().add_class("brisa-subtitulo")
            textos.pack_start(self.titulo, False, False, 0)
            textos.pack_start(self.subtitulo, False, False, 0)
            topo.pack_start(textos, True, True, 0)
            caixa.pack_start(topo, False, False, 0)

            self.modelo = Gtk.ListStore(str, str, str)
            tabela = Gtk.TreeView(model=self.modelo)
            for indice, nome in enumerate(("Programa", "Versão atual", "Versão nova")):
                celula = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
                coluna = Gtk.TreeViewColumn(nome, celula, text=indice)
                coluna.set_expand(True)
                coluna.set_resizable(True)
                tabela.append_column(coluna)
            rolagem = Gtk.ScrolledWindow(vexpand=True)
            rolagem.add(tabela)
            caixa.pack_start(rolagem, True, True, 0)

            self.progresso = Gtk.ProgressBar(show_text=True)
            self.progresso.set_no_show_all(True)
            caixa.pack_start(self.progresso, False, False, 0)

            self.registro = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
            rolagem_registro = Gtk.ScrolledWindow(min_content_height=120)
            rolagem_registro.add(self.registro)
            detalhes = Gtk.Expander(label="Ver detalhes")
            detalhes.add(rolagem_registro)
            caixa.pack_start(detalhes, False, False, 0)

            botoes = Gtk.Box(spacing=8, halign=Gtk.Align.END)
            self.botao_procurar = Gtk.Button(label="Procurar de novo")
            self.botao_procurar.connect("clicked", lambda _b: self.procurar())
            self.botao_atualizar = Gtk.Button(label="Atualizar agora")
            self.botao_atualizar.get_style_context().add_class("suggested-action")
            self.botao_atualizar.connect("clicked", lambda _b: self.atualizar())
            self.botao_atualizar.set_sensitive(False)
            botoes.pack_start(self.botao_procurar, False, False, 0)
            botoes.pack_start(self.botao_atualizar, False, False, 0)
            caixa.pack_start(botoes, False, False, 0)
            return caixa

        def _escrever_registro(self, linha):
            if linha.startswith(("pmstatus:", "dlstatus:")):
                partes = linha.split(":", 3)
                if len(partes) == 4:
                    try:
                        self.progresso.set_fraction(min(1.0, float(partes[2]) / 100))
                    except ValueError:
                        pass
                    self.progresso.set_text(partes[3])
                return
            buffer = self.registro.get_buffer()
            buffer.insert(buffer.get_end_iter(), linha + "\n")
            self.registro.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)

        def _ocupar(self, sim, texto=""):
            self.ocupado = sim
            self.botao_procurar.set_sensitive(not sim)
            self.botao_atualizar.set_sensitive(not sim and len(self.modelo) > 0)
            if sim:
                self.progresso.set_fraction(0)
                self.progresso.set_text(texto)
                self.progresso.show()
            else:
                self.progresso.hide()

        def procurar(self):
            if self.ocupado:
                return False
            self.titulo.set_text("Procurando atualizações...")
            self.subtitulo.set_text("Isso pode levar um minuto.")
            self._ocupar(True, "Conferindo os servidores")
            comum.rodar_helper_ao_vivo(["atualizar-lista"], self._escrever_registro, self._procurou)
            return False

        def _procurou(self, codigo, saida):
            if codigo != 0:
                self._ocupar(False)
                self.titulo.set_text("Não deu para procurar atualizações")
                if "lock" in saida.lower() or "trava" in saida.lower():
                    self.subtitulo.set_text("Outro programa está mexendo nos pacotes agora. "
                                            "Tente de novo em alguns minutos.")
                else:
                    self.subtitulo.set_text("Confira se o aparelho está conectado à internet.")
                return
            _marcar_verificacao()

            def buscar():
                lista = listar_atualizacoes()
                return lista, tamanho_download([pacote for pacote, _atual, _nova in lista])

            comum.em_segundo_plano(buscar, self._mostrar_lista)

        def _mostrar_lista(self, resultado):
            lista, tamanho = resultado
            self.modelo.clear()
            for item in lista:
                self.modelo.append(list(item))
            self._ocupar(False)
            if lista:
                quantidade = len(lista)
                self.titulo.set_text(f"{quantidade} atualização disponível" if quantidade == 1
                                     else f"{quantidade} atualizações disponíveis")
                aviso = " O modo gamer está ligado: é melhor atualizar depois de jogar." \
                    if comum.modo_atual() == "gamer" else ""
                self.subtitulo.set_text(f"Vai baixar cerca de {comum.bytes_legivel(tamanho)}.{aviso}")
            else:
                self.titulo.set_text("Seu sistema está atualizado")
                self.subtitulo.set_text("Nenhuma atualização no momento. O Brisa Suave Update confere "
                                        "sozinho uma vez por dia.")

        def atualizar(self):
            if self.ocupado:
                return
            self.titulo.set_text("Atualizando...")
            self.subtitulo.set_text("Não desligue o aparelho até terminar.")
            self._ocupar(True, "Preparando")
            comum.rodar_helper_ao_vivo(["atualizar-tudo"], self._escrever_registro, self._atualizou)

        def _atualizou(self, codigo, saida):
            self._ocupar(False)
            if codigo == 0:
                comum.notificar("Atualização concluída", "O Brisa Suave OS está em dia.", "brisa-update")
                self.procurar()
            else:
                self.titulo.set_text("A atualização não terminou")
                self.subtitulo.set_text("Clique em \"Ver detalhes\" para saber o motivo, ou tente de novo.")

        # ------------------------------------------------ aba histórico
        def _montar_historico(self):
            self.modelo_historico = Gtk.ListStore(str, str)
            tabela = Gtk.TreeView(model=self.modelo_historico)
            for indice, nome in enumerate(("Quando", "O que mudou")):
                coluna = Gtk.TreeViewColumn(nome, Gtk.CellRendererText(), text=indice)
                coluna.set_expand(True)
                tabela.append_column(coluna)
            rolagem = Gtk.ScrolledWindow()
            rolagem.set_border_width(12)
            rolagem.add(tabela)
            return rolagem

        def _carregar_historico(self):
            self.modelo_historico.clear()
            for data, resumo in ler_historico():
                self.modelo_historico.append([data, resumo])

    comum.aplicar_css()
    janela = JanelaUpdate()
    janela.connect("destroy", Gtk.main_quit)
    janela.show_all()
    Gtk.main()


def main():
    if "--vigiar" in sys.argv[1:]:
        vigiar()
        return 0
    abrir_janela()
    return 0


if __name__ == "__main__":
    sys.exit(main())
