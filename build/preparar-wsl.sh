#!/bin/bash
# Instala no Ubuntu do WSL as ferramentas que montam o Brisa Suave OS.
# Rode uma vez só, como root.
set -euo pipefail
. "$(dirname "$0")/comum.sh"
exigir_root

passo "Instalando as ferramentas de montagem"
apt-get update
apt-get install -y --no-install-recommends \
    debootstrap debian-archive-keyring \
    squashfs-tools xorriso mtools dosfstools \
    grub-common grub-pc-bin grub-efi-amd64-bin grub-efi-ia32-bin \
    rsync xz-utils parted e2fsprogs fdisk \
    qemu-user-static binfmt-support \
    librsvg2-bin curl unzip python3 ca-certificates \
    dpkg-dev apt-utils gnupg git

passo "Ligando o simulador de processador ARM (para montar a versão do BTV)"
if ligar_simulador_arm; then
    echo "Simulador ARM ligado."
else
    aviso "o simulador ARM não ligou. A versão do BTV não vai ser montada até isso funcionar."
fi

echo
echo "Tudo pronto. Agora rode: build/gerar-tudo.sh  (ou gerar-pc.sh / gerar-btv.sh)"
