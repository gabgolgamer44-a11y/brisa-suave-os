#!/bin/bash
# Gera a ISO do Brisa Suave OS para PC.
#   build/gerar-pc.sh 64   -> saida/brisa-suave-os-pc64.iso  (Debian 13)
#   build/gerar-pc.sh 32   -> saida/brisa-suave-os-pc32.iso  (Debian 12 LTS)
set -euo pipefail
. "$(dirname "$0")/comum.sh"
exigir_root
exigir_comandos debootstrap mksquashfs grub-mkrescue xorriso rsync rsvg-convert

case "${1:-}" in
    64) ARCH=amd64; SUITE=trixie;   VARIANTE=pc64; KERNEL=linux-image-amd64 ;;
    32) ARCH=i386;  SUITE=bookworm; VARIANTE=pc32; KERNEL=linux-image-686 ;;
    *) falha "use: $0 64   ou   $0 32" ;;
esac

PASTA="$TRABALHO/$VARIANTE"
RAIZ="$PASTA/rootfs"
ISO="$PASTA/iso"
ARQUIVO="$SAIDA/brisa-suave-os-$VARIANTE.iso"

if mountpoint -q "$RAIZ/proc" 2>/dev/null; then desmontar_chroot "$RAIZ"; fi
rm -rf "$PASTA"
mkdir -p "$RAIZ" "$ISO/live" "$ISO/boot/grub" "$SAIDA"

passo "Baixando a base do Debian ($SUITE, $ARCH)"
debootstrap --arch="$ARCH" --variant=minbase \
    --components=main,contrib,non-free,non-free-firmware \
    --include=apt-utils,ca-certificates,debconf-i18n \
    "$SUITE" "$RAIZ" "$ESPELHO_DEBIAN"

instalar_arquivos_brisa "$RAIZ" "$VARIANTE" "Debian $SUITE"
personalizar "$RAIZ" "$VARIANTE" "$SUITE" "$KERNEL"

passo "Preparando o pendrive: kernel e sistema compactado"
VMLINUZ="$(ls -1 "$RAIZ"/boot/vmlinuz-* | sort -V | tail -n1)"
INITRD="$(ls -1 "$RAIZ"/boot/initrd.img-* | sort -V | tail -n1)"
[ -f "$VMLINUZ" ] && [ -f "$INITRD" ] || falha "kernel não encontrado em $RAIZ/boot"
cp "$VMLINUZ" "$ISO/live/vmlinuz"
cp "$INITRD" "$ISO/live/initrd.img"
mksquashfs "$RAIZ" "$ISO/live/filesystem.squashfs" -comp xz -b 1M -Xdict-size 100% -noappend \
    -wildcards -e 'proc/*' 'sys/*' 'dev/*' 'run/*' 'tmp/*'
du -sx --block-size=1 "$RAIZ" | cut -f1 > "$ISO/live/filesystem.size"

passo "Menu de inicialização"
cp "$PROJETO/config/grub/grub.cfg" "$ISO/boot/grub/grub.cfg"
rsvg-convert -w 1024 -h 768 "$PROJETO/overlay/usr/share/brisa/wallpapers/brisa-azul.svg" -o "$ISO/boot/grub/fundo.png"
cat > "$ISO/LEIA-ME.txt" <<EOF
Brisa Suave OS $BRISA_VERSAO ($VARIANTE)
Grave este arquivo num pendrive com o balenaEtcher, o Rufus ou o Ventoy.
EOF

passo "Gerando $ARQUIVO"
grub-mkrescue -o "$ARQUIVO" "$ISO" -- -volid BRISA_SUAVE
( cd "$SAIDA" && sha256sum "$(basename "$ARQUIVO")" > "$(basename "$ARQUIVO").sha256" )

echo
echo "Pronto: $ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"
