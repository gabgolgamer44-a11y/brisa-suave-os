# Como gerar o Brisa Suave OS

O sistema é montado dentro do **Ubuntu do WSL** (no seu PC ele se chama `PCMClawUbuntu`).
Todos os comandos abaixo são digitados no **PowerShell** do Windows.

No seu Ubuntu do WSL o acesso aos discos do Windows está desligado (`/mnt/c` vazio).
Por isso o projeto é **copiado para dentro do Ubuntu** antes de montar, e os arquivos
prontos são buscados pelo Explorador de Arquivos, sem mudar nenhuma configuração do WSL.

## 0. Copiar o projeto para dentro do Ubuntu (repita sempre que mudar algo)

```powershell
robocopy C:\Users\User\claude\brisa-suave-os \\wsl.localhost\PCMClawUbuntu\root\brisa-suave-os /MIR /XD saida
```

## 1. Preparar as ferramentas (só uma vez)

```powershell
wsl -d PCMClawUbuntu -u root -- bash /root/brisa-suave-os/build/preparar-wsl.sh
```

## 2. Gerar a versão de PC 64 bits

```powershell
wsl -d PCMClawUbuntu -u root -- bash /root/brisa-suave-os/build/gerar-pc.sh 64
```

Leva de 20 a 40 minutos, dependendo da internet.

## 3. Gerar a versão de PC 32 bits

```powershell
wsl -d PCMClawUbuntu -u root -- bash /root/brisa-suave-os/build/gerar-pc.sh 32
```

## 4. Gerar a versão do BTV 11

1. Baixe a imagem do Armbian para TV box Amlogic em https://www.armbian.com/aml-s9xx-box/.
   Escolha a versão **Debian**, do tipo **Minimal** (o Brisa coloca a área de trabalho).
2. Copie o arquivo `.img.xz` para `\\wsl.localhost\PCMClawUbuntu\root\`.
3. Rode (troque o nome do arquivo):

```powershell
wsl -d PCMClawUbuntu -u root -- bash /root/brisa-suave-os/build/gerar-btv.sh /root/NOME-DO-ARQUIVO.img.xz
```

## Onde ficam os arquivos prontos

Abra no Explorador de Arquivos:

```
\\wsl.localhost\PCMClawUbuntu\root\brisa-suave-os\saida
```

Lá estão `brisa-suave-os-pc64.iso`, `brisa-suave-os-pc32.iso` e `brisa-suave-os-btv11.img`.
Dá para gravar direto dali com o balenaEtcher ou o Rufus, ou copiar para o Windows.

## O que cada script faz

| Script | O que faz |
|---|---|
| `build/preparar-wsl.sh` | Instala as ferramentas de montagem no Ubuntu do WSL |
| `build/gerar-pc.sh 64` ou `32` | Baixa o Debian, instala o XFCE, os programas e os apps do Brisa, e gera a ISO |
| `build/gerar-btv.sh` | Pega a imagem do Armbian, coloca o Brisa dentro e prepara a inicialização do BTV 11 |
| `build/gerar-tudo.sh` | Gera as três versões, uma depois da outra |
| `build/personalizar.sh` | Roda dentro do sistema que está sendo montado: idioma, teclado, programas, visual |
| `build/gerar-papeis-de-parede.py` | Recria os papéis de parede, se as cores forem mudadas |

## Mudando o sistema

- **Programas que já vêm instalados:** `config/pacotes/base.list`
- **Apps da Brisa Suave Store:** `apps/store/catalogo.json`
- **Atalhos de teclado:** `overlay/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml`
- **Barra de tarefas:** `overlay/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml`
- **Cores dos temas:** `build/gerar-papeis-de-parede.py` e `apps/brisa/comum.py`
