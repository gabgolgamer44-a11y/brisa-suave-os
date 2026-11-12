# Brisa Suave OS na TV box BTV 11

## O aparelho

| Item | BTV 11 (modelo B11) |
|---|---|
| Placa | X3BL46_V2.0 |
| Processador | Amlogic S905X3 (4 núcleos, 64 bits) |
| Vídeo | Mali-G31 |
| Memória | 2 GB de RAM, 16 GB de armazenamento |
| Wi-Fi | AP6212 (funciona no Linux) |
| Arquivo da placa | `meson-sm1-sei610.dtb` |

Fonte: projeto Educabox, https://github.com/educabox/educabox/blob/main/boxes/btv11.md

## O que você precisa

- Pendrive de **8 GB ou mais**
- **Teclado e mouse USB** (o controle remoto não funciona no Linux)
- Um **clipe** de papel
- O programa **balenaEtcher** no Windows

## 1. Gravar no pendrive

Abra o balenaEtcher, escolha `brisa-suave-os-btv11.img`, escolha o pendrive e clique em "Flash".
Se o Windows pedir para formatar o pendrive depois, clique em **Cancelar**.

## 2. Ligar pelo pendrive (primeira vez)

1. Com o BTV **desligado da tomada**, coloque o pendrive numa das portas USB.
2. Coloque o clipe no furinho **reset** (dentro da entrada AV) e segure.
3. Ainda segurando, ligue o BTV na tomada.
4. Solte quando a tela apagar e o aparelho reiniciar (uns 5 a 10 segundos).
5. O Brisa Suave OS abre pelo pendrive. Nas próximas vezes, com o pendrive conectado, ele abre sozinho.

Se não funcionar pelo clipe: no Android do BTV, abra o app **"Atualização"** ou **"Update & Backup"**,
escolha **Local**, entre no pendrive e selecione **aml_autoscript.zip**.

## 3. Usuário e senha

O Brisa entra direto. Se pedir senha, é: usuário **brisa**, senha **brisa**.
Troque a senha depois, em Configurações > Usuários, ou no terminal com o comando `passwd`.

## 4. Instalar na memória interna (opcional, cuidado)

**Isso apaga o Android do BTV.** Faça só se o Brisa funcionou bem pelo pendrive.

1. Abra o terminal e digite `sudo /root/install-aml.sh` (o script vem com o Armbian).
2. Siga o guia do Educabox, parte "Instalação do Armbian do pendrive para o eMMC":
   https://github.com/educabox/educabox/blob/main/boxes/btv11.md
3. Nunca use o comando `armbian-install`: ele não funciona nas TV boxes Amlogic.

## Atualizações no BTV

O Brisa Suave Update atualiza os programas normalmente. O kernel e a inicialização ficam
**travados** de propósito: uma atualização deles pode deixar a TV box com tela preta.
