"""Brisa Suave Central: modos, informações do aparelho, aparência, data e hora."""
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from brisa import comum, modo  # noqa: E402

FUSOS = [
    ("America/Sao_Paulo", "Brasília (SP, RJ, MG, Sul, Nordeste, GO, DF)"),
    ("America/Manaus", "Amazonas, Roraima e Rondônia (1 hora a menos)"),
    ("America/Cuiaba", "Mato Grosso e Mato Grosso do Sul (1 hora a menos)"),
    ("America/Rio_Branco", "Acre (2 horas a menos)"),
    ("America/Noronha", "Fernando de Noronha (1 hora a mais)"),
]

DESCRICAO_MODOS = {
    "normal": ("Normal", "Desempenho equilibrado para o dia a dia.", "brisa-central"),
    "economia": ("Economia", "Gasta menos energia: processador e brilho reduzidos, sem efeitos visuais.",
                 "brisa-economia"),
    "gamer": ("Gamer", "Processador no máximo, tarefas de fundo pausadas e notificações silenciadas.",
              "brisa-gamer"),
}


def titulo(texto, subtitulo=None):
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    rotulo = Gtk.Label(label=texto, xalign=0)
    rotulo.get_style_context().add_class("brisa-titulo")
    caixa.pack_start(rotulo, False, False, 0)
    if subtitulo:
        sub = Gtk.Label(label=subtitulo, xalign=0, wrap=True)
        sub.get_style_context().add_class("brisa-subtitulo")
        caixa.pack_start(sub, False, False, 0)
    return caixa


def pagina():
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    caixa.set_border_width(24)
    return caixa


class PaginaModos:
    def __init__(self, janela):
        self.janela = janela
        self.caixa = pagina()
        self.caixa.pack_start(titulo("Modos", "Escolha como o aparelho deve se comportar agora. "
                                                "O modo Gamer também liga e desliga com Windows + G."),
                              False, False, 0)
        linha = Gtk.Box(spacing=12, homogeneous=True)
        self.botoes = {}
        for chave, (nome, texto, icone) in DESCRICAO_MODOS.items():
            botao = Gtk.Button()
            botao.get_style_context().add_class("brisa-modo")
            conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            conteudo.pack_start(comum.imagem_de_arquivo(comum.ICONES / f"{icone}.svg", 56), False, False, 0)
            nome_rotulo = Gtk.Label(label=nome)
            nome_rotulo.get_style_context().add_class("brisa-titulo")
            conteudo.pack_start(nome_rotulo, False, False, 0)
            conteudo.pack_start(Gtk.Label(label=texto, wrap=True, justify=Gtk.Justification.CENTER,
                                          max_width_chars=22), False, False, 0)
            botao.add(conteudo)
            botao.connect("clicked", self.ao_escolher, chave)
            linha.pack_start(botao, True, True, 0)
            self.botoes[chave] = botao
        self.caixa.pack_start(linha, False, False, 0)
        self.situacao = Gtk.Label(xalign=0)
        self.caixa.pack_start(self.situacao, False, False, 0)
        self.atualizar()
        GLib.timeout_add_seconds(2, self._vigiar)

    def _vigiar(self):
        self.atualizar()
        return True

    def atualizar(self):
        atual = comum.modo_atual()
        for chave, botao in self.botoes.items():
            estilo = botao.get_style_context()
            if chave == atual:
                estilo.add_class("brisa-modo-ativo")
            else:
                estilo.remove_class("brisa-modo-ativo")
        self.situacao.set_markup(f"Modo atual: <b>{comum.MODOS[atual]}</b>")

    def ao_escolher(self, _botao, chave):
        for botao in self.botoes.values():
            botao.set_sensitive(False)
        self.situacao.set_text("Trocando o modo...")

        def terminou(resultado):
            ok, texto = resultado
            for botao in self.botoes.values():
                botao.set_sensitive(True)
            self.atualizar()
            if not ok:
                comum.mensagem(self.janela, "Não deu para trocar o modo", texto, "erro")

        comum.em_segundo_plano(lambda: modo.mudar_modo(chave), terminou)


class PaginaAparelho:
    def __init__(self):
        self.caixa = pagina()
        self.caixa.pack_start(titulo("Meu aparelho", "Como o aparelho está agora."), False, False, 0)
        self.leitor = comum.LeitorCPU()
        grade = Gtk.Grid(column_spacing=18, row_spacing=14)
        self.barras, self.valores = {}, {}
        itens = [("cpu", "Processador"), ("memoria", "Memória (RAM)"), ("disco", "Armazenamento")]
        for linha, (chave, nome) in enumerate(itens):
            grade.attach(Gtk.Label(label=nome, xalign=0), 0, linha, 1, 1)
            barra = Gtk.ProgressBar(hexpand=True, valign=Gtk.Align.CENTER)
            grade.attach(barra, 1, linha, 1, 1)
            valor = Gtk.Label(xalign=1, width_chars=22)
            grade.attach(valor, 2, linha, 1, 1)
            self.barras[chave], self.valores[chave] = barra, valor
        self.caixa.pack_start(grade, False, False, 0)

        self.detalhes = Gtk.Label(xalign=0, selectable=True)
        self.caixa.pack_start(self.detalhes, False, False, 0)
        info = comum.info_brisa()
        nomes_variante = {"pc64": "PC 64 bits", "pc32": "PC 32 bits", "btv11": "TV box BTV 11"}
        sistema = Gtk.Label(xalign=0, selectable=True)
        sistema.set_markup(
            f"<b>Sistema:</b> Brisa Suave OS {GLib.markup_escape_text(info.get('VERSAO', '?'))} · "
            f"{nomes_variante.get(info.get('VARIANTE'), info.get('VARIANTE'))} · "
            f"base {GLib.markup_escape_text(info.get('BASE', 'Debian'))}\n"
            f"<b>Processador:</b> {GLib.markup_escape_text(comum.modelo_processador())}")
        self.caixa.pack_start(sistema, False, False, 0)
        self.atualizar()
        GLib.timeout_add_seconds(2, self.atualizar)

    def atualizar(self):
        uso = self.leitor.uso()
        self.barras["cpu"].set_fraction(uso / 100)
        self.valores["cpu"].set_text(f"{uso:.0f}%")
        usada, total = comum.memoria()
        if total:
            self.barras["memoria"].set_fraction(usada / total)
            self.valores["memoria"].set_text(f"{comum.bytes_legivel(usada)} de {comum.bytes_legivel(total)}")
        usado, total_disco = comum.disco()
        self.barras["disco"].set_fraction(usado / total_disco if total_disco else 0)
        self.valores["disco"].set_text(f"{comum.bytes_legivel(usado)} de {comum.bytes_legivel(total_disco)}")

        partes = []
        temp = comum.temperatura()
        partes.append(f"<b>Temperatura:</b> {temp:.0f} °C" if temp is not None else "<b>Temperatura:</b> sem sensor")
        freq = comum.frequencia_mhz()
        if freq:
            partes.append(f"<b>Velocidade:</b> {freq} MHz")
        bat = comum.bateria()
        if bat:
            partes.append(f"<b>Bateria:</b> {bat[0]}% ({bat[1]})")
        partes.append(f"<b>Modo:</b> {comum.MODOS[comum.modo_atual()]}")
        self.detalhes.set_markup("     ".join(partes))
        return True


class PaginaAparencia:
    def __init__(self, janela):
        self.janela = janela
        self.caixa = pagina()
        self.caixa.pack_start(titulo("Aparência", "Escolha a cor do sistema. O papel de parede muda junto."),
                              False, False, 0)
        grade = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=5,
                            column_spacing=12, row_spacing=12, homogeneous=True)
        self.botoes = {}
        for chave, tema in comum.TEMAS.items():
            botao = Gtk.Button()
            conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            conteudo.pack_start(comum.imagem_de_arquivo(comum.PAPEIS / tema["papel"], 150), False, False, 0)
            conteudo.pack_start(Gtk.Label(label=tema["nome"]), False, False, 0)
            botao.add(conteudo)
            botao.connect("clicked", self.ao_escolher_tema, chave)
            grade.add(botao)
            self.botoes[chave] = botao
        self.caixa.pack_start(grade, False, False, 0)

        outra = Gtk.Button(label="Usar outra imagem como papel de parede...")
        outra.set_halign(Gtk.Align.START)
        outra.connect("clicked", self.ao_escolher_imagem)
        self.caixa.pack_start(outra, False, False, 0)
        self.situacao = Gtk.Label(xalign=0)
        self.caixa.pack_start(self.situacao, False, False, 0)
        self.situacao.set_markup(f"Tema atual: <b>{comum.TEMAS[comum.tema_atual()]['nome']}</b>")

    def ao_escolher_tema(self, _botao, chave):
        comum.aplicar_tema(chave)
        self.situacao.set_markup(f"Tema atual: <b>{comum.TEMAS[chave]['nome']}</b>. "
                                 "Alguns apps abertos mudam de cor quando forem reabertos.")

    def ao_escolher_imagem(self, _botao):
        dialogo = Gtk.FileChooserDialog(title="Escolha uma imagem", transient_for=self.janela,
                                        action=Gtk.FileChooserAction.OPEN)
        dialogo.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Usar esta imagem", Gtk.ResponseType.OK)
        filtro = Gtk.FileFilter()
        filtro.set_name("Imagens")
        filtro.add_pixbuf_formats()
        dialogo.add_filter(filtro)
        if dialogo.run() == Gtk.ResponseType.OK:
            comum.aplicar_papel_de_parede(dialogo.get_filename())
            self.situacao.set_text("Papel de parede trocado.")
        dialogo.destroy()


class PaginaDataHora:
    def __init__(self, janela):
        self.janela = janela
        self.caixa = pagina()
        self.caixa.pack_start(titulo("Data e hora"), False, False, 0)
        self.relogio = Gtk.Label(xalign=0)
        self.relogio.get_style_context().add_class("brisa-relogio")
        self.caixa.pack_start(self.relogio, False, False, 0)
        self.data = Gtk.Label(xalign=0)
        self.caixa.pack_start(self.data, False, False, 0)

        # acerto automático
        linha_auto = Gtk.Box(spacing=12)
        linha_auto.pack_start(Gtk.Label(label="Acertar a hora automaticamente pela internet", xalign=0),
                              True, True, 0)
        self.auto = Gtk.Switch(valign=Gtk.Align.CENTER)
        linha_auto.pack_start(self.auto, False, False, 0)
        self.caixa.pack_start(linha_auto, False, False, 0)

        # fuso horário
        linha_fuso = Gtk.Box(spacing=12)
        linha_fuso.pack_start(Gtk.Label(label="Fuso horário", xalign=0), True, True, 0)
        self.fuso = Gtk.ComboBoxText()
        for chave, nome in FUSOS:
            self.fuso.append(chave, nome)
        linha_fuso.pack_start(self.fuso, False, False, 0)
        self.caixa.pack_start(linha_fuso, False, False, 0)

        # ajuste manual
        self.manual = Gtk.Box(spacing=6)
        self.manual.pack_start(Gtk.Label(label="Ajustar à mão:", xalign=0), False, False, 0)
        agora = time.localtime()
        self.campos = {}
        for chave, minimo, maximo, valor, separador in [
                ("dia", 1, 31, agora.tm_mday, "/"), ("mes", 1, 12, agora.tm_mon, "/"),
                ("ano", 2024, 2099, agora.tm_year, "  "), ("hora", 0, 23, agora.tm_hour, ":"),
                ("minuto", 0, 59, agora.tm_min, "")]:
            campo = Gtk.SpinButton.new_with_range(minimo, maximo, 1)
            campo.set_value(valor)
            campo.set_numeric(True)
            self.manual.pack_start(campo, False, False, 0)
            if separador:
                self.manual.pack_start(Gtk.Label(label=separador), False, False, 0)
            self.campos[chave] = campo
        aplicar = Gtk.Button(label="Aplicar")
        aplicar.connect("clicked", self.ao_aplicar_manual)
        self.manual.pack_start(aplicar, False, False, 6)
        self.caixa.pack_start(self.manual, False, False, 0)

        self._carregar()
        self.auto.connect("notify::active", self.ao_trocar_auto)
        self.fuso.connect("changed", self.ao_trocar_fuso)
        self._tique()
        GLib.timeout_add_seconds(1, self._tique)

    def _carregar(self):
        codigo, ntp = comum.rodar(["timedatectl", "show", "-p", "NTP", "--value"], timeout=10)
        self.auto.set_active(codigo == 0 and ntp.strip() == "yes")
        codigo, fuso = comum.rodar(["timedatectl", "show", "-p", "Timezone", "--value"], timeout=10)
        if not self.fuso.set_active_id(fuso.strip()):
            self.fuso.set_active_id("America/Sao_Paulo")
        self.manual.set_sensitive(not self.auto.get_active())

    def _tique(self):
        self.relogio.set_text(time.strftime("%H:%M:%S"))
        dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
                 "outubro", "novembro", "dezembro"]
        agora = time.localtime()
        self.data.set_text(f"{dias[agora.tm_wday]}, {agora.tm_mday} de {meses[agora.tm_mon - 1]} de {agora.tm_year}")
        return True

    def _pedir(self, *args):
        def terminou(resultado):
            codigo, saida = resultado
            if codigo != 0:
                comum.mensagem(self.janela, "Não deu para ajustar", saida or "Erro desconhecido.", "erro")
            self._carregar()

        comum.em_segundo_plano(lambda: comum.rodar_helper(*args, timeout=60), terminou)

    def ao_trocar_auto(self, *_):
        self.manual.set_sensitive(not self.auto.get_active())
        self._pedir("hora", "auto", "sim" if self.auto.get_active() else "nao")

    def ao_trocar_fuso(self, *_):
        fuso = self.fuso.get_active_id()
        if fuso:
            self._pedir("hora", "fuso", fuso)

    def ao_aplicar_manual(self, _botao):
        c = {k: int(v.get_value()) for k, v in self.campos.items()}
        self._pedir("hora", "definir", f"{c['ano']:04d}-{c['mes']:02d}-{c['dia']:02d} {c['hora']:02d}:{c['minuto']:02d}")


class JanelaCentral(Gtk.Window):
    def __init__(self):
        super().__init__(title="Brisa Suave Central")
        self.set_default_size(880, 560)
        self.set_icon_from_file(str(comum.ICONES / "brisa-central.svg"))
        pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        pilha.add_titled(PaginaModos(self).caixa, "modos", "Modos")
        pilha.add_titled(PaginaAparelho().caixa, "aparelho", "Meu aparelho")
        pilha.add_titled(PaginaAparencia(self).caixa, "aparencia", "Aparência")
        pilha.add_titled(PaginaDataHora(self).caixa, "hora", "Data e hora")
        lateral = Gtk.StackSidebar(stack=pilha)
        lateral.set_size_request(190, -1)
        caixa = Gtk.Box()
        caixa.pack_start(lateral, False, False, 0)
        caixa.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        caixa.pack_start(pilha, True, True, 0)
        self.add(caixa)


def main():
    comum.aplicar_css()
    janela = JanelaCentral()
    janela.connect("destroy", Gtk.main_quit)
    janela.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
