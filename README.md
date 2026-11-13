# Brisa Suave OS

Sistema operacional leve, baseado em Linux (Debian), feito para dar vida nova a
computadores fracos e à TV box **BTV 11**.

- Visual no estilo Windows: barra de tarefas embaixo, menu iniciar e os mesmos atalhos.
- Cor principal azul, com temas roxo, verde, laranja e escuro.
- Roda com 2 GB de RAM.
- Já vem em português do Brasil, com teclado ABNT2 e horário de Brasília.
- Tem três apps próprios: **Brisa Suave Central**, **Brisa Suave Update** e **Brisa Suave Store**.

## Versões

| Versão | Para quê | Base | Arquivo gerado |
|---|---|---|---|
| PC 64 bits | Computadores e notebooks de 2008 em diante | Debian 13 | `brisa-suave-os-pc64.iso` |
| PC 32 bits | Computadores bem antigos | Debian 12 LTS | `brisa-suave-os-pc32.iso` |
| BTV 11 | TV box BTV 11 (Amlogic S905X3) | Armbian (Debian) | `brisa-suave-os-btv11.img` |

## Programas que já vêm instalados

Navegador (Firefox), gerenciador de arquivos (Thunar), visualizador de imagens
(Ristretto), player de vídeo e música (VLC), editor de texto (Mousepad),
gerenciador de tarefas, e os drivers de Wi-Fi e de placa de vídeo.

## Apps do Brisa

| App | O que faz | Atalho |
|---|---|---|
| Brisa Suave Central | Modos Normal, Economia e Gamer, informações do aparelho, aparência, data e hora | Windows + C |
| Modo Gamer | Liga ou desliga o modo gamer direto | Windows + G |
| Brisa Suave Update | Procura e instala atualizações | — |
| Brisa Suave Store | Loja de aplicativos | — |
| Boas-vindas | Assistente da primeira vez: Wi-Fi, cor, atalhos e apps. Abre sozinho no primeiro login depois de instalar | — |

## Atalhos de teclado

| Atalho | Ação |
|---|---|
| Windows | Abre o menu iniciar |
| Windows + E | Abre os arquivos |
| Windows + R | Procura e abre um aplicativo |
| Windows + D | Mostra a área de trabalho |
| Windows + L | Bloqueia a tela |
| Windows + setas | Encaixa a janela à esquerda, à direita, em cima ou embaixo |
| Ctrl + Shift + Esc | Gerenciador de tarefas |
| Alt + F4 | Fecha a janela |
| Print Screen | Tira um print da tela |

## Como gerar o sistema

O sistema é montado dentro do Ubuntu do WSL. Veja [docs/COMO-GERAR.md](docs/COMO-GERAR.md).

## Como gravar e usar

- No PC: [docs/COMO-GRAVAR-PC.md](docs/COMO-GRAVAR-PC.md)
- No BTV 11: [docs/BTV11.md](docs/BTV11.md)

## Organização das pastas

```
apps/       os apps do Brisa (Central, Update, Store e o ajudante do sistema)
overlay/    arquivos copiados para dentro do sistema (visual, atalhos, configurações)
branding/   logo, papéis de parede e o visual do instalador
config/     listas de pacotes e o menu de inicialização
build/      scripts que geram os arquivos .iso e .img
docs/       guias em português
```
