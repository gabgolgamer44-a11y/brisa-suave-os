"""Brisa Boas-vindas: assistente da primeira vez que o Brisa Suave OS é ligado.

  brisa-boas-vindas                 abre o assistente
  brisa-boas-vindas --primeira-vez  só abre se ainda não foi concluído (usado no login)

Telas: boas-vindas, internet (Wi-Fi), cor do sistema, atalhos, apps, pronto.
"""
import os
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from brisa import comum  # noqa: E402

MARCA = comum.CONFIG / "boas-vindas-feito"

# apps oferecidos (ids do catálogo da Brisa Suave Store), na ordem em que aparecem
APPS_SUGERIDOS = ["libreoffice", "evince", "galculator", "retroarch", "audacious", "gimp",
                  "supertux", "steam", "gcompris"]

ATALHOS = [
    ("Windows", "Abre o menu Iniciar"),
    ("Windows + E", "Abre os seus arquivos"),
    ("Windows + R", "Procura e abre um aplicativo"),
    ("Windows + D", "Mostra a área de trabalho"),
    ("Windows + L", "Bloqueia a tela"),
    ("Windows + setas", "Encaixa a janela num canto da tela"),
    ("Windows + C", "Abre o Brisa Suave Central"),
    ("Windows + G", "Liga e desliga o modo gamer"),
    ("Ctrl + Shift + Esc", "Gerenciador de tarefas"),
    ("Alt + F4", "Fecha a janela"),
    ("Print Screen", "Tira um print da tela"),
]


# ---------------------------------------------------------------- internet

def tem_internet() -> bool:
    try:
        with socket.create_connection(("deb.debian.org", 80), timeout=4):
            return True
    except OSError:
        return False


def _dividir_nmcli(linha):
    """nmcli -t separa por ':' e escapa os ':' de dentro com '\\:'."""
    partes = re.split(r"(?<!\\):", linha)
    return [p.replace("\\:", ":").replace("\\\\", "\\") for p in partes]


def redes_wifi() -> list:
    """[(nome, sinal, protegida, conectada)] ordenado pelo sinal."""
    codigo, saida = comum.rodar(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                                 "dev", "wifi", "list", "--rescan", "auto"], timeout=30)
    if codigo != 0:
        return []
    redes = {}
    for linha in saida.splitlines():
        campos = _dividir_nmcli(linha)
        if len(campos) < 4 or not campos[1]:
            continue
        uso, nome, sinal, seguranca = campos[:4]
        try:
            sinal = int(sinal)
        except ValueError:
            sinal = 0
        anterior = redes.get(nome)
        if not anterior or sinal > anterior[1]:
            redes[nome] = (nome, sinal, bool(seguranca.strip() and seguranca != "--"), uso.strip() == "*")
    return sorted(redes.values(), key=lambda r: (not r[3], -r[1]))


def conectar_wifi(nome, senha) -> tuple:
    cmd = ["nmcli", "dev", "wifi", "connect", nome]
    if senha:
        cmd += ["password", senha]
    return comum.rodar(cmd, timeout=60)


def sinal_em_barras(sinal):
    return "▂▄▆█"[: max(1, min(4, (sinal + 24) // 25))]


# ---------------------------------------------------------------- janela

class Assistente(Gtk.Window):
    def __init__(self):
        super().__init__(title="Boas-vindas ao Brisa Suave OS")
        self.set_default_size(820, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_from_file(str(comum.ICONES / "brisa-boas-vindas.svg"))
        self.variante = comum.info_brisa().get("VARIANTE", "pc64")
        self.escolhidos = set()

        self.pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
                               transition_duration=250)
        self.paginas = [
            ("inicio", self._pagina_inicio()),
            ("internet", self._pagina_internet()),
            ("cor", self._pagina_cor()),
            ("atalhos", self._pagina_atalhos()),
            ("apps", self._pagina_apps()),
            ("pronto", self._pagina_pronto()),
        ]
        for nome, pagina in self.paginas:
            self.pilha.add_named(pagina, nome)

        # rodapé: bolinhas de progresso e botões
        self.bolinhas = Gtk.Label()
        self.voltar = Gtk.Button(label="Voltar")
        self.voltar.connect("clicked", lambda _b: self._ir(-1))
        self.proximo = Gtk.Button(label="Próximo")
        self.proximo.get_style_context().add_class("suggested-action")
        self.proximo.connect("clicked", lambda _b: self._ir(+1))
        self.pular = Gtk.Button(label="Pular tudo")
        self.pular.set_relief(Gtk.ReliefStyle.NONE)
        self.pular.connect("clicked", lambda _b: self._concluir())

        rodape = Gtk.Box(spacing=8)
        rodape.set_border_width(14)
        rodape.pack_start(self.pular, False, False, 0)
        rodape.set_center_widget(self.bolinhas)
        rodape.pack_end(self.proximo, False, False, 0)
        rodape.pack_end(self.voltar, False, False, 0)

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.pack_start(self.pilha, True, True, 0)
        caixa.pack_start(Gtk.Separator(), False, False, 0)
        caixa.pack_start(rodape, False, False, 0)
        self.add(caixa)
        self.indice = 0
        self._atualizar_rodape()

    # ------------------------------------------------ navegação
    def _ir(self, passo):
        nome_atual = self.paginas[self.indice][0]
        if passo > 0 and nome_atual == "apps":
            self.indice += 1
            self.pilha.set_visible_child_name("pronto")
            self._atualizar_rodape()
            self._instalar_escolhidos()
            return
        if passo > 0 and nome_atual == "pronto":
            self._concluir()
            return
        self.indice = max(0, min(len(self.paginas) - 1, self.indice + passo))
        nome = self.paginas[self.indice][0]
        self.pilha.set_visible_child_name(nome)
        if nome == "internet":
            self._verificar_internet()
        elif nome == "apps":
            self._carregar_apps()
        self._atualizar_rodape()

    def _atualizar_rodape(self):
        total = len(self.paginas)
        self.bolinhas.set_markup("  ".join(
            "<span foreground='#2F86E8'>●</span>" if i == self.indice else "<span foreground='#9aa7bd'>○</span>"
            for i in range(total)))
        self.voltar.set_sensitive(0 < self.indice < total - 1)
        nome = self.paginas[self.indice][0]
        textos = {"inicio": "Começar", "apps": "Instalar e terminar", "pronto": "Concluir"}
        self.proximo.set_label(textos.get(nome, "Próximo"))
        self.pular.set_visible(nome not in ("pronto",))

    def _concluir(self):
        comum.CONFIG.mkdir(parents=True, exist_ok=True)
        MARCA.write_text("ok\n", encoding="utf-8")
        self.destroy()

    # ------------------------------------------------ páginas
    @staticmethod
    def _pagina_base(titulo, texto=None, icone=None):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        caixa.set_border_width(32)
        if icone:
            caixa.pack_start(comum.imagem_de_arquivo(icone, 96), False, False, 0)
        rotulo = Gtk.Label(label=titulo, xalign=0 if not icone else 0.5)
        rotulo.get_style_context().add_class("brisa-titulo")
        caixa.pack_start(rotulo, False, False, 0)
        if texto:
            sub = Gtk.Label(label=texto, wrap=True, xalign=0 if not icone else 0.5,
                            justify=Gtk.Justification.LEFT if not icone else Gtk.Justification.CENTER)
            sub.get_style_context().add_class("brisa-subtitulo")
            caixa.pack_start(sub, False, False, 0)
        return caixa

    def _pagina_inicio(self):
        caixa = self._pagina_base(
            "Olá! Boas-vindas ao Brisa Suave OS",
            "Vamos deixar o sistema do seu jeito. Leva só um minutinho:\n"
            "conectar à internet, escolher a cor, conhecer os atalhos e instalar os apps que você quiser.",
            icone=str(comum.Path("/usr/share/brisa/logo.svg")))
        caixa.set_valign(Gtk.Align.CENTER)
        return caixa

    def _pagina_internet(self):
        caixa = self._pagina_base("Internet", "Conecte o aparelho à internet para receber atualizações e instalar apps.")
        self.situacao_internet = Gtk.Label(xalign=0)
        caixa.pack_start(self.situacao_internet, False, False, 0)

        self.lista_wifi = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        rolagem = Gtk.ScrolledWindow(vexpand=True)
        rolagem.add(self.lista_wifi)
        caixa.pack_start(rolagem, True, True, 0)

        linha = Gtk.Box(spacing=8)
        self.senha = Gtk.Entry(placeholder_text="Senha do Wi-Fi", visibility=False, hexpand=True)
        self.senha.connect("activate", lambda _e: self._conectar())
        self.botao_conectar = Gtk.Button(label="Conectar")
        self.botao_conectar.connect("clicked", lambda _b: self._conectar())
        atualizar = Gtk.Button(label="Procurar redes")
        atualizar.connect("clicked", lambda _b: self._verificar_internet())
        linha.pack_start(self.senha, True, True, 0)
        linha.pack_start(self.botao_conectar, False, False, 0)
        linha.pack_start(atualizar, False, False, 0)
        caixa.pack_start(linha, False, False, 0)
        dica = Gtk.Label(xalign=0, wrap=True,
                         label="Usando cabo de rede? Ele conecta sozinho, é só clicar em Próximo.")
        dica.get_style_context().add_class("brisa-subtitulo")
        caixa.pack_start(dica, False, False, 0)
        return caixa

    def _pagina_cor(self):
        caixa = self._pagina_base("Escolha a cor do sistema", "Dá para trocar quando quiser no Brisa Suave Central.")
        grade = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=5,
                            min_children_per_line=5, column_spacing=10, row_spacing=10, homogeneous=True)
        self.situacao_cor = Gtk.Label(xalign=0)
        for chave, tema in comum.TEMAS.items():
            botao = Gtk.Button()
            conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            conteudo.pack_start(comum.imagem_de_arquivo(comum.PAPEIS / tema["papel"], 120), False, False, 0)
            conteudo.pack_start(Gtk.Label(label=tema["nome"]), False, False, 0)
            botao.add(conteudo)
            botao.connect("clicked", self._escolher_cor, chave)
            grade.add(botao)
        caixa.pack_start(grade, False, False, 0)
        caixa.pack_start(self.situacao_cor, False, False, 0)
        self.situacao_cor.set_markup(f"Cor atual: <b>{comum.TEMAS[comum.tema_atual()]['nome']}</b>")
        return caixa

    def _pagina_atalhos(self):
        caixa = self._pagina_base("Atalhos de teclado", "São os mesmos do Windows. A tecla Windows também se chama Super.")
        grade = Gtk.Grid(column_spacing=24, row_spacing=10)
        for linha, (tecla, acao) in enumerate(ATALHOS):
            rotulo = Gtk.Label(xalign=0)
            rotulo.set_markup(f"<b>{GLib.markup_escape_text(tecla)}</b>")
            grade.attach(rotulo, 0, linha, 1, 1)
            grade.attach(Gtk.Label(label=acao, xalign=0), 1, linha, 1, 1)
        caixa.pack_start(grade, False, False, 0)
        return caixa

    def _pagina_apps(self):
        caixa = self._pagina_base("Quer instalar algum app?",
                                  "Marque os que quiser. Eles são instalados no final. "
                                  "Dá para instalar outros depois pela Brisa Suave Store.")
        self.lista_apps = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.lista_apps.set_placeholder(Gtk.Label(label="Carregando a lista..."))
        rolagem = Gtk.ScrolledWindow(vexpand=True)
        rolagem.add(self.lista_apps)
        caixa.pack_start(rolagem, True, True, 0)
        self.apps_carregados = False
        return caixa

    def _pagina_pronto(self):
        caixa = self._pagina_base("Tudo pronto!", icone=str(comum.ICONES / "brisa-boas-vindas.svg"))
        caixa.set_valign(Gtk.Align.CENTER)
        self.texto_pronto = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        caixa.pack_start(self.texto_pronto, False, False, 0)
        self.progresso = Gtk.ProgressBar(show_text=True)
        self.progresso.set_no_show_all(True)
        caixa.pack_start(self.progresso, False, False, 0)
        return caixa

    # ------------------------------------------------ internet
    def _verificar_internet(self):
        self.situacao_internet.set_text("Conferindo a conexão...")

        def buscar():
            return tem_internet(), redes_wifi()

        comum.em_segundo_plano(buscar, self._mostrar_redes)

    def _mostrar_redes(self, resultado):
        online, redes = resultado
        if online:
            self.situacao_internet.set_markup("<span foreground='#1F9E6E'><b>✔ Conectado à internet.</b></span>")
        else:
            self.situacao_internet.set_markup("<b>Sem internet.</b> Escolha sua rede Wi-Fi abaixo e digite a senha.")
        for filho in self.lista_wifi.get_children():
            self.lista_wifi.remove(filho)
        if not redes:
            self.lista_wifi.add(Gtk.Label(label="Nenhuma rede Wi-Fi encontrada.", xalign=0, margin=10))
        for nome, sinal, protegida, conectada in redes:
            linha = Gtk.ListBoxRow()
            linha.rede = (nome, protegida)
            caixa = Gtk.Box(spacing=10)
            caixa.set_border_width(8)
            barras = Gtk.Label(label=sinal_em_barras(sinal))
            caixa.pack_start(barras, False, False, 0)
            texto = GLib.markup_escape_text(nome)
            rotulo = Gtk.Label(xalign=0)
            rotulo.set_markup(f"<b>{texto}</b>  (conectado)" if conectada else texto)
            caixa.pack_start(rotulo, True, True, 0)
            if protegida:
                caixa.pack_start(Gtk.Label(label="🔒"), False, False, 0)
            linha.add(caixa)
            self.lista_wifi.add(linha)
        self.lista_wifi.show_all()

    def _conectar(self):
        linha = self.lista_wifi.get_selected_row()
        if not linha or not hasattr(linha, "rede"):
            comum.mensagem(self, "Escolha uma rede", "Clique no nome da sua rede Wi-Fi na lista.", "aviso")
            return
        nome, protegida = linha.rede
        senha = self.senha.get_text()
        if protegida and not senha:
            comum.mensagem(self, "Falta a senha", f"Digite a senha da rede \"{nome}\".", "aviso")
            return
        self.botao_conectar.set_sensitive(False)
        self.situacao_internet.set_text(f"Conectando em \"{nome}\"...")

        def terminou(resultado):
            codigo, _saida = resultado
            self.botao_conectar.set_sensitive(True)
            if codigo != 0:
                self.situacao_internet.set_markup(
                    f"<b>Não conectou em \"{GLib.markup_escape_text(nome)}\".</b> Confira a senha e tente de novo.")
            else:
                self.senha.set_text("")
                self._verificar_internet()

        comum.em_segundo_plano(lambda: conectar_wifi(nome, senha), terminou)

    # ------------------------------------------------ cor
    def _escolher_cor(self, _botao, chave):
        comum.aplicar_tema(chave)
        self.situacao_cor.set_markup(f"Cor atual: <b>{comum.TEMAS[chave]['nome']}</b>")

    # ------------------------------------------------ apps
    def _carregar_apps(self):
        if self.apps_carregados:
            return
        self.apps_carregados = True

        def buscar():
            catalogo = comum.carregar_catalogo()
            por_id = {a["id"]: a for a in comum.apps_da_variante(catalogo, self.variante)}
            apps = [por_id[i] for i in APPS_SUGERIDOS if i in por_id]
            principais = [a["pacotes"][0] for a in apps]
            disponiveis = comum.pacotes_disponiveis(principais)
            instalados = comum.pacotes_instalados(principais)
            return [a for a in apps if a["pacotes"][0] in disponiveis], instalados

        comum.em_segundo_plano(buscar, self._mostrar_apps)

    def _mostrar_apps(self, resultado):
        apps, instalados = resultado
        self.lista_apps.set_placeholder(Gtk.Label(
            label="Sem internet, a lista de apps não carrega. Instale depois pela Brisa Suave Store."))
        for app in apps:
            linha = Gtk.Box(spacing=12)
            linha.set_border_width(8)
            marcar = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            ja_tem = app["pacotes"][0] in instalados
            marcar.set_sensitive(not ja_tem)
            marcar.connect("toggled", self._marcar_app, app)
            linha.pack_start(marcar, False, False, 0)
            linha.pack_start(comum.icone(app.get("icone"), 40), False, False, 0)
            textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            nome = Gtk.Label(xalign=0)
            extra = "  ✔ já instalado" if ja_tem else ""
            nome.set_markup(f"<b>{GLib.markup_escape_text(app['nome'])}</b>{extra}")
            textos.pack_start(nome, False, False, 0)
            descricao = Gtk.Label(label=app.get("descricao", ""), xalign=0, wrap=True)
            descricao.get_style_context().add_class("brisa-subtitulo")
            textos.pack_start(descricao, False, False, 0)
            linha.pack_start(textos, True, True, 0)
            selo = Gtk.Label(label="Leve" if app.get("peso") == "leve" else "Pesado")
            selo.get_style_context().add_class("brisa-leve" if app.get("peso") == "leve" else "brisa-pesado")
            selo.set_valign(Gtk.Align.CENTER)
            linha.pack_start(selo, False, False, 0)
            self.lista_apps.add(linha)
        self.lista_apps.show_all()

    def _marcar_app(self, botao, app):
        if botao.get_active():
            self.escolhidos.add(app["id"])
        else:
            self.escolhidos.discard(app["id"])

    def _instalar_escolhidos(self):
        catalogo = {a["id"]: a for a in comum.carregar_catalogo().get("apps", [])}
        fila = [catalogo[i] for i in APPS_SUGERIDOS if i in self.escolhidos and i in catalogo]
        if not fila:
            self._mostrar_fim([])
            return
        self.proximo.set_sensitive(False)
        self.progresso.show()
        resultados = []

        def proximo_app():
            if not fila:
                self.progresso.hide()
                self.proximo.set_sensitive(True)
                self._mostrar_fim(resultados)
                return
            app = fila.pop(0)
            self.texto_pronto.set_text(f"Instalando {app['nome']}... não desligue o aparelho.")
            self.progresso.set_fraction(0)
            self.progresso.set_text("")

            def linha(texto):
                if texto.startswith(("pmstatus:", "dlstatus:")):
                    partes = texto.split(":", 3)
                    if len(partes) == 4:
                        try:
                            self.progresso.set_fraction(min(1.0, float(partes[2]) / 100))
                        except ValueError:
                            pass
                        self.progresso.set_text(partes[3])

            def terminou(codigo, _saida):
                resultados.append((app["nome"], codigo == 0))
                proximo_app()

            comum.rodar_helper_ao_vivo(["instalar", app["pacotes"][0]], linha, terminou)

        proximo_app()

    def _mostrar_fim(self, resultados):
        partes = ["O Brisa Suave OS está pronto para usar."]
        ok = [nome for nome, deu in resultados if deu]
        falhou = [nome for nome, deu in resultados if not deu]
        if ok:
            partes.append("Instalados: " + ", ".join(ok) + ". Eles já estão no menu Iniciar.")
        if falhou:
            partes.append("Não deu para instalar: " + ", ".join(falhou) +
                          ". Tente depois pela Brisa Suave Store, com internet.")
        partes.append("\nQuer rever este assistente? Ele está no menu Iniciar, em \"Boas-vindas\".")
        self.texto_pronto.set_text("\n".join(partes))


def main():
    if "--primeira-vez" in sys.argv[1:]:
        # não abre no pendrive (sessão live) nem se já foi concluído
        if MARCA.exists() or Path("/run/live/medium").exists():
            return 0
        import time
        time.sleep(6)  # deixa o primeiro login aplicar o tema antes
    comum.aplicar_css()
    janela = Assistente()
    janela.connect("destroy", Gtk.main_quit)
    janela.show_all()
    janela.progresso.hide()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
