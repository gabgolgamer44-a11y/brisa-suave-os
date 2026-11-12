#!/bin/bash
# Gera a imagem do Brisa Suave OS para a TV box BTV 11 (Amlogic S905X3, 2 GB).
#
#   build/gerar-btv.sh <imagem-do-armbian.img.xz | link para baixar>
#
# Use a imagem oficial do Armbian para "aml-s9xx-box", versão Debian (minimal):
# https://www.armbian.com/aml-s9xx-box/
# O resultado vai para saida/brisa-suave-os-btv11.img (grave com o balenaEtcher).
set -euo pipefail
. "$(dirname "$0")/comum.sh"
exigir_root
exigir_comandos losetup parted resize2fs e2fsck rsync curl unzip python3 xz

ORIGEM="${1:-${ARMBIAN_IMAGEM:-}}"
[ -n "$ORIGEM" ] || falha "informe a imagem do Armbian (arquivo .img.xz ou link). Veja docs/BTV11.md."
[ -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ] || falha "o simulador ARM está desligado. Rode build/preparar-wsl.sh."

DTB="amlogic/meson-sm1-sei610.dtb"   # arquivo da placa do BTV 11 (X3BL46), segundo o projeto Educabox
ESPACO_EXTRA="${ESPACO_EXTRA:-3G}"   # espaço a mais para o XFCE e os programas
PASTA="$TRABALHO/btv11"
RAIZ="$PASTA/rootfs"
IMAGEM="$PASTA/brisa-suave-os-btv11.img"
ARQUIVO="$SAIDA/brisa-suave-os-btv11.img"
mkdir -p "$PASTA" "$SAIDA"

LOOP=""
limpar() {
    set +e
    desmontar_chroot "$RAIZ" 2>/dev/null
    mountpoint -q "$RAIZ/boot" && umount "$RAIZ/boot"
    mountpoint -q "$RAIZ" && umount "$RAIZ"
    [ -n "$LOOP" ] && losetup -d "$LOOP"
}
trap limpar EXIT

# ------------------------------------------------------------ imagem base
passo "Pegando a imagem do Armbian"
if [[ "$ORIGEM" =~ ^https?:// ]]; then
    BAIXADA="$PASTA/$(basename "${ORIGEM%%\?*}")"
    [ -f "$BAIXADA" ] || curl -fL --retry 3 -o "$BAIXADA" "$ORIGEM"
    ORIGEM="$BAIXADA"
fi
[ -f "$ORIGEM" ] || falha "arquivo não encontrado: $ORIGEM"
case "$ORIGEM" in
    *.xz) xz -dc "$ORIGEM" > "$IMAGEM" ;;
    *.img) cp "$ORIGEM" "$IMAGEM" ;;
    *) falha "use um arquivo .img ou .img.xz" ;;
esac

passo "Aumentando a imagem em $ESPACO_EXTRA para caber o Brisa"
truncate -s "+$ESPACO_EXTRA" "$IMAGEM"
LOOP="$(losetup -fP --show "$IMAGEM")"
sleep 1
PART_ROOT="" PART_BOOT=""
for parte in "$LOOP"p*; do
    case "$(blkid -o value -s TYPE "$parte" 2>/dev/null)" in
        ext4) PART_ROOT="$parte" ;;
        vfat) [ -z "$PART_BOOT" ] && PART_BOOT="$parte" ;;
    esac
done
[ -n "$PART_ROOT" ] || falha "não achei a partição do sistema (ext4) na imagem do Armbian"
NUM_ROOT="${PART_ROOT##*p}"
parted -s "$LOOP" resizepart "$NUM_ROOT" 100%
partx -u "$LOOP" 2>/dev/null || partprobe "$LOOP" 2>/dev/null || true
e2fsck -fy "$PART_ROOT" || true
resize2fs "$PART_ROOT"

passo "Abrindo a imagem"
mkdir -p "$RAIZ"
mount "$PART_ROOT" "$RAIZ"
if [ -n "$PART_BOOT" ]; then
    mkdir -p "$RAIZ/boot"
    mount "$PART_BOOT" "$RAIZ/boot"
fi
SUITE="$(. "$RAIZ/etc/os-release" && echo "${VERSION_CODENAME:-trixie}")"
ID_BASE="$(. "$RAIZ/etc/os-release" && echo "${ID:-debian}")"
if [ "$ID_BASE" = "ubuntu" ]; then
    aviso "esta imagem do Armbian é baseada em Ubuntu. O Brisa foi feito para a versão Debian; alguns programas podem faltar."
fi

instalar_arquivos_brisa "$RAIZ" "btv11" "Armbian $SUITE"
personalizar "$RAIZ" "btv11" "$SUITE"

# ------------------------------------------------------------ inicialização pelo pendrive
passo "Preparando a inicialização do BTV 11 pelo pendrive"
BOOT="$RAIZ/boot"
[ -f "$BOOT/dtb/$DTB" ] || aviso "o arquivo $DTB não está em /boot/dtb. Confira a imagem do Armbian."

SCRIPTS="$PASTA/bootscripts"
if [ ! -f "$SCRIPTS/s905_autoscript" ]; then
    LINK="$(curl -fsSL https://api.github.com/repos/devmfc/amlogic-bootscripts-Armbian/releases/latest |
        python3 -c 'import json,sys; d=json.load(sys.stdin); print(next(a["browser_download_url"] for a in d["assets"] if a["name"].endswith(".zip")))')"
    mkdir -p "$SCRIPTS"
    curl -fL -o "$PASTA/bootscripts.zip" "$LINK"
    unzip -o -j "$PASTA/bootscripts.zip" -d "$SCRIPTS"
fi
for arquivo in aml_autoscript s905_autoscript; do
    [ -f "$BOOT/$arquivo" ] && mv "$BOOT/$arquivo" "$BOOT/$arquivo.armbian-original"
done
for arquivo in aml_autoscript aml_autoscript.zip s905_autoscript gxl-fixup.scr emmc_autoscript; do
    [ -f "$SCRIPTS/$arquivo" ] && cp "$SCRIPTS/$arquivo" "$BOOT/"
done

UUID_ROOT="$(blkid -s UUID -o value "$PART_ROOT")"
cat > "$BOOT/armbianEnv.txt" <<EOF
extraargs=earlycon rootflags=data=writeback rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 quiet splash loglevel=3
bootlogo=false
verbosity=1
usbstoragequirks=0x2537:0x1066:u,0x2537:0x1068:u
console=both
# Arquivo da placa do BTV 11 (placa X3BL46)
fdtfile=$DTB
rootdev=UUID=$UUID_ROOT
EOF

# ------------------------------------------------------------ fechar
passo "Fechando a imagem"
sync
limpar
trap - EXIT
mv "$IMAGEM" "$ARQUIVO"
( cd "$SAIDA" && sha256sum "$(basename "$ARQUIVO")" > "$(basename "$ARQUIVO").sha256" )
echo
echo "Pronto: $ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"
echo "Grave num pendrive de 8 GB ou mais com o balenaEtcher. Veja docs/BTV11.md."
