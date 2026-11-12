"""Brisa Suave Store: loja de aplicativos do Brisa Suave OS."""
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from brisa import comum  # noqa: E402


class LinhaApp(Gtk.ListBoxRow):
    def __init__(self, loja, app):
        super().__init__()
        self.loja, self.app = loja, app
        self.pacote = app["pacotes"][0]
        caixa = Gtk.Box(spacing=14)
        caixa.set_border_width(10)
        caixa.pack_start(comum.icone(app.get("icone"), 48), False, False, 0)

        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER)
        linha_nome = Gtk.Box(spacing=8)
        nome = Gtk.Label(xalign=0)
        nome.set_markup(f"<b>{GLib.markup_escape_text(app['nome'])}</b>")
        linha_nome.pack_start(nome, False, False, 0)
        selo = Gtk.Label(label="Leve" if app.get("peso") == "leve" else "Pesado")
        selo.get_style_context().add_class("brisa-leve" if app.get("peso") == "leve" else "brisa-pesado")
        linha_nome.pack_start(selo, False, False, 0)
        textos.pack_start(linha_nome, False, False, 0)
        descricao = Gtk.Label(label=app.get("descricao", ""), xalign=0, wrap=True, max_width_chars=60)
        descricao.get_style_context().add_class("brisa-subtitulo")
        textos.pack_start(descricao, False, False, 0)
        caixa.pack_start(textos, True, True, 0)

        self.botao = Gtk.Button(valign=Gtk.Align.CENTER)
        self.botao.set_size_request(110, -1)
        self.botao.connect("clicked", self.ao_clicar)
        caixa.pack_start(self.botao, False, False, 0)
        self.add(caixa)
        self.atualizar_botao()

    @property
    def instalado(self):
        return self.pacote in self.loja.instalados

    def atualizar_botao(self):
        estilo = self.botao.get_style_context()
        if self.instalado:
            self.botao.set_label("Remover")
            estilo.remove_class("suggested-action")
            estilo.add_class("destructive-action")
        else:
            self.botao.set_label("Instalar")
            estilo.remove_class("destructive-action")
            estilo.add_class("suggested-action")

    def ao_clicar(self, _botao):
        if self.instalado:
            pergunta = Gtk.MessageDialog(transient_for=self.loja, modal=True,
                                         message_type=Gtk.MessageType.QUESTION,
                                         buttons=Gtk.ButtonsType.YES_NO,
                                         text=f"Remover {self.app['nome']}?")
            pergunta.format_secondary_text("Você pode instalar de novo depois pela Brisa Suave Store.")
            resposta = pergunta.run()
            pergunta.destroy()
            if resposta != Gtk.ResponseType.YES:
                return
            self.loja.executar("remover", self)
        else:
            self.loja.executar("instalar", self)


class JanelaStore(Gtk.Window):
    def __init__(self):
        super().__init__(title="Brisa Suave Store")
        self.set_default_size(960, 640)
        self.set_icon_from_file(str(comum.ICONES / "brisa-store.svg"))
        self.variante = comum.info_brisa().get("VARIANTE", "pc64")
        self.catalogo = comum.carregar_catalogo()
        self.apps, self.instalados, self.linhas = [], set(), []
        self.ocupado = False

        cabecalho = Gtk.HeaderBar(show_close_button=True, title="Brisa Suave Store")
        self.busca = Gtk.SearchEntry(placeholder_text="Procurar apps")
        self.busca.set_size_request(280, -1)
        self.busca.connect("search-changed", lambda _b: self.filtrar())
        cabecalho.pack_end(self.busca)
        self.set_titlebar(cabecalho)

        self.categorias = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.categorias.set_size_request(200, -1)
        self.categorias.connect("row-selected", lambda _l, _r: self.filtrar())
        for chave, nome, icone in [("todos", "Todos os apps", "view-app-grid"),
                                   *[(c["id"], c["nome"], c.get("icone")) for c in self.catalogo.get("categorias", [])],
                                   ("instalados", "Instalados", "emblem-ok")]:
            linha = Gtk.ListBoxRow()
            linha.chave = chave
            caixa = Gtk.Box(spacing=10)
            caixa.set_border_width(8)
            caixa.pack_start(comum.icone(icone, 24), False, False, 0)
            caixa.pack_start(Gtk.Label(label=nome, xalign=0), True, True, 0)
            linha.add(caixa)
            self.categorias.add(linha)

        self.lista = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.lista.set_filter_func(self._mostrar_linha)
        self.lista.set_placeholder(Gtk.Label(label="Nenhum app encontrado."))
        rolagem = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        rolagem.add(self.lista)

        self.carregando = Gtk.Spinner(active=True)
        self.situacao = Gtk.Label(label="Carregando a loja...", xalign=0)
        self.progresso = Gtk.ProgressBar(show_text=True, hexpand=True)
        rodape = Gtk.Box(spacing=10)
        rodape.set_border_width(8)
        rodape.pack_start(self.carregando, False, False, 0)
        rodape.pack_start(self.situacao, False, False, 0)
        rodape.pack_start(self.progresso, True, True, 0)

        direita = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        direita.pack_start(rolagem, True, True, 0)
        direita.pack_start(Gtk.Separator(), False, False, 0)
        direita.pack_start(rodape, False, False, 0)

        corpo = Gtk.Box()
        corpo.pack_start(self.categorias, False, False, 0)
        corpo.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        corpo.pack_start(direita, True, True, 0)
        self.add(corpo)
        self.show_all()
        self.progresso.hide()
        self.categorias.select_row(self.categorias.get_row_at_index(0))
        comum.em_segundo_plano(self._ler_disponiveis, self._mostrar_apps)

    # ------------------------------------------------ carregar
    def _ler_disponiveis(self):
        apps = comum.apps_da_variante(self.catalogo, self.variante)
        principais = [app["pacotes"][0] for app in apps if app.get("pacotes")]
        disponiveis = comum.pacotes_disponiveis(principais)
        instalados = comum.pacotes_instalados(principais)
        return [app for app in apps if app.get("pacotes") and app["pacotes"][0] in disponiveis], instalados

    def _mostrar_apps(self, resultado):
        self.apps, self.instalados = resultado
        for app in sorted(self.apps, key=lambda a: a["nome"].lower()):
            linha = LinhaApp(self, app)
            self.linhas.append(linha)
            self.lista.add(linha)
        self.lista.show_all()
        self.carregando.stop()
        self.carregando.hide()
        self.situacao.set_text(f"{len(self.apps)} apps disponíveis para este aparelho.")
        self.filtrar()

    # ------------------------------------------------ filtro
    def _categoria(self):
        linha = self.categorias.get_selected_row()
        return linha.chave if linha else "todos"

    def _mostrar_linha(self, linha):
        categoria = self._categoria()
        if categoria == "instalados" and not linha.instalado:
            return False
        if categoria not in ("todos", "instalados") and linha.app.get("categoria") != categoria:
            return False
        termo = self.busca.get_text().strip().lower()
        if termo:
            texto = f"{linha.app['nome']} {linha.app.get('descricao', '')} {' '.join(linha.app.get('palavras', []))}"
            return termo in texto.lower()
        return True

    def filtrar(self):
        self.lista.invalidate_filter()

    # ------------------------------------------------ instalar / remover
    def executar(self, acao, linha):
        if self.ocupado:
            comum.mensagem(self, "Aguarde um pouco", "A loja ainda está terminando o pedido anterior.", "aviso")
            return
        self.ocupado = True
        for outra in self.linhas:
            outra.botao.set_sensitive(False)
        verbo = "Instalando" if acao == "instalar" else "Removendo"
        self.situacao.set_text(f"{verbo} {linha.app['nome']}...")
        self.progresso.set_fraction(0)
        self.progresso.set_text("")
        self.progresso.show()
        comum.rodar_helper_ao_vivo([acao, linha.pacote], self._progresso,
                                   lambda codigo, saida: self._terminou(acao, linha, codigo, saida))

    def _progresso(self, texto):
        if texto.startswith(("pmstatus:", "dlstatus:")):
            partes = texto.split(":", 3)
            if len(partes) == 4:
                try:
                    self.progresso.set_fraction(min(1.0, float(partes[2]) / 100))
                except ValueError:
                    pass
                self.progresso.set_text(partes[3])

    def _terminou(self, acao, linha, codigo, saida):
        self.ocupado = False
        self.progresso.hide()
        self.instalados = comum.pacotes_instalados([app["pacotes"][0] for app in self.apps])
        for outra in self.linhas:
            outra.botao.set_sensitive(True)
            outra.atualizar_botao()
        self.filtrar()
        nome = linha.app["nome"]
        if codigo == 0:
            texto = f"{nome} instalado. Ele já está no menu Iniciar." if acao == "instalar" else f"{nome} removido."
            self.situacao.set_text(texto)
            comum.notificar("Brisa Suave Store", texto, "brisa-store")
        else:
            self.situacao.set_text(f"Não deu certo com {nome}.")
            dica = "Confira se o aparelho está conectado à internet e tente de novo."
            if "lock" in saida.lower():
                dica = "Outro programa está instalando ou atualizando agora. Tente de novo em alguns minutos."
            comum.mensagem(self, f"Não deu certo com {nome}", f"{dica}\n\nDetalhes:\n{saida[-600:]}", "erro")


def main():
    comum.aplicar_css()
    janela = JanelaStore()
    janela.connect("destroy", Gtk.main_quit)
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
