#!/bin/bash
# Funções usadas pelos scripts de geração do Brisa Suave OS.
# Rode tudo como root dentro do Ubuntu do WSL (ou de qualquer Debian/Ubuntu).

set -euo pipefail

BRISA_VERSAO="1.0"
PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# O trabalho pesado fica dentro do Linux (no disco do Windows o chroot não funciona).
TRABALHO="${BRISA_TRABALHO:-/root/brisa-build}"
SAIDA="${BRISA_SAIDA:-$PROJETO/saida}"
ESPELHO_DEBIAN="${ESPELHO_DEBIAN:-http://deb.debian.org/debian}"

passo() { echo; echo "==> $*"; }
aviso() { echo "AVISO: $*" >&2; }
falha() { echo "ERRO: $*" >&2; exit 1; }

exigir_root() {
    [ "$(id -u)" -eq 0 ] || falha "rode como root (no WSL: wsl -d PCMClawUbuntu -u root)."
    case "$PROJETO" in
        /mnt/*) aviso "o projeto está no disco do Windows; copie para dentro do Linux (veja docs/COMO-GERAR.md)." ;;
    esac
}

exigir_comandos() {
    local faltando=()
    for cmd in "$@"; do
        command -v "$cmd" >/dev/null 2>&1 || faltando+=("$cmd")
    done
    [ ${#faltando[@]} -eq 0 ] || falha "faltam programas: ${faltando[*]}. Rode antes: build/preparar-wsl.sh"
}

# Monta /proc, /sys, /dev e /run dentro do sistema que está sendo montado.
montar_chroot() {
    local raiz="$1"
    mount --bind /dev "$raiz/dev"
    mount -t devpts devpts "$raiz/dev/pts"
    mount -t proc proc "$raiz/proc"
    mount -t sysfs sysfs "$raiz/sys"
    mount -t tmpfs tmpfs "$raiz/run"
    # internet dentro do chroot
    if [ -L "$raiz/etc/resolv.conf" ] || [ -e "$raiz/etc/resolv.conf" ]; then
        mv "$raiz/etc/resolv.conf" "$raiz/etc/resolv.conf.brisa-original"
    fi
    cp -L /etc/resolv.conf "$raiz/etc/resolv.conf"
    # impede serviços de iniciarem durante a instalação dos pacotes
    printf '#!/bin/sh\nexit 101\n' > "$raiz/usr/sbin/policy-rc.d"
    chmod +x "$raiz/usr/sbin/policy-rc.d"
}

desmontar_chroot() {
    local raiz="$1"
    rm -f "$raiz/usr/sbin/policy-rc.d"
    if [ -e "$raiz/etc/resolv.conf.brisa-original" ] || [ -L "$raiz/etc/resolv.conf.brisa-original" ]; then
        rm -f "$raiz/etc/resolv.conf"
        mv "$raiz/etc/resolv.conf.brisa-original" "$raiz/etc/resolv.conf"
    fi
    for ponto in run sys proc dev/pts dev; do
        mountpoint -q "$raiz/$ponto" && umount -l "$raiz/$ponto"
    done
    return 0
}

# Copia o visual, as configurações e os apps do Brisa para dentro do sistema.
instalar_arquivos_brisa() {
    local raiz="$1" variante="$2" base="$3"
    passo "Copiando o visual e os apps do Brisa ($variante)"

    # Arquivos vindos do Windows podem chegar com permissões erradas;
    # por isso as permissões são definidas aqui, e não copiadas.
    rsync -rlt --chmod=D755,F644 "$PROJETO/overlay/" "$raiz/"
    chmod 755 "$raiz/usr/lib/brisa/brisa-polkit-agente"
    install -D -m 644 "$PROJETO/branding/logo.svg" "$raiz/usr/share/brisa/logo.svg"
    install -D -m 644 "$PROJETO/branding/logo.svg" "$raiz/usr/share/icons/hicolor/scalable/apps/brisa-suave-os.svg"

    # apps
    mkdir -p "$raiz/usr/lib/brisa/brisa"
    install -m 644 "$PROJETO"/apps/brisa/*.py "$raiz/usr/lib/brisa/brisa/"
    install -m 755 "$PROJETO/apps/helper/brisa-helper" "$raiz/usr/lib/brisa/brisa-helper"
    for app in "$PROJETO"/apps/bin/*; do
        install -m 755 "$app" "$raiz/usr/bin/$(basename "$app")"
    done
    install -D -m 644 "$PROJETO/apps/polkit/org.brisa.helper.policy" \
        "$raiz/usr/share/polkit-1/actions/org.brisa.helper.policy"
    install -D -m 644 "$PROJETO/apps/store/catalogo.json" "$raiz/usr/share/brisa/store/catalogo.json"

    # identidade do sistema
    cat > "$raiz/etc/brisa-release" <<EOF
VERSAO="$BRISA_VERSAO"
VARIANTE="$variante"
BASE="$base"
EOF

    # arquivos usados pelo script de personalização
    mkdir -p "$raiz/tmp/brisa"
    cp -r "$PROJETO/config/pacotes" "$raiz/tmp/brisa/"
    install -m 755 "$PROJETO/build/personalizar.sh" "$raiz/tmp/brisa/personalizar.sh"
    if [ -d "$PROJETO/branding/calamares" ]; then
        rsync -rlt --chmod=D755,F644 "$PROJETO/branding/calamares" "$raiz/tmp/brisa/"
        # o instalador usa imagens PNG
        rsvg-convert -w 256 -h 256 "$PROJETO/branding/logo.svg" -o "$raiz/tmp/brisa/calamares/brisa/logo.png"
        rsvg-convert -w 1280 -h 720 "$PROJETO/overlay/usr/share/brisa/wallpapers/brisa-azul.svg" \
            -o "$raiz/tmp/brisa/calamares/brisa/fundo.png"
    fi
}

# Roda a personalização dentro do sistema (em chroot).
personalizar() {
    local raiz="$1" variante="$2" suite="$3" kernel="${4:-}"
    passo "Instalando os programas e ajustando o sistema ($variante). Isso demora."
    montar_chroot "$raiz"
    trap "desmontar_chroot '$raiz'" EXIT
    chroot "$raiz" /usr/bin/env -i \
        HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin TERM="${TERM:-xterm}" \
        VARIANTE="$variante" SUITE="$suite" KERNEL="$kernel" \
        /bin/bash /tmp/brisa/personalizar.sh
    desmontar_chroot "$raiz"
    trap - EXIT
    rm -rf "$raiz/tmp/brisa"
}
