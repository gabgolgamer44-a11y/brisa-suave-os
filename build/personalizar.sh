#!/bin/bash
# Roda DENTRO do sistema que está sendo montado (chroot).
# Variáveis: VARIANTE (pc64|pc32|btv11), SUITE (trixie|bookworm|...), KERNEL (só PC).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive LC_ALL=C LANG=C
VARIANTE="${VARIANTE:?}"
SUITE="${SUITE:?}"
KERNEL="${KERNEL:-}"
DIR=/tmp/brisa
APT=(apt-get -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold --no-install-recommends)

passo() { echo; echo "  -> $*"; }

existe() {
    # sem pipe: com "pipefail", o grep -q fecharia o pipe cedo e daria falso negativo
    local saida
    saida="$(apt-cache policy "$1" 2>/dev/null)"
    grep -q 'Candidate: [^(]' <<< "$saida"
}

# Lê uma lista de pacotes (veja o formato em config/pacotes/base.list).
pacotes_da_lista() {
    local linha opcao escolhido
    while read -r linha; do
        linha="${linha%%#*}"
        linha="$(echo "$linha" | xargs)"
        [ -z "$linha" ] && continue
        if [[ "$linha" == \?* ]]; then
            existe "${linha#\?}" && echo "${linha#\?}"
        elif [[ "$linha" == *"|"* ]]; then
            escolhido=""
            IFS='|' read -ra opcoes <<< "$linha"
            for opcao in "${opcoes[@]}"; do
                if existe "$opcao"; then escolhido="$opcao"; break; fi
            done
            if [ -n "$escolhido" ]; then echo "$escolhido"; else echo "AVISO: nenhum de '$linha' existe" >&2; fi
        else
            if existe "$linha"; then echo "$linha"; else echo "AVISO: pacote '$linha' não existe aqui" >&2; fi
        fi
    done < "$1"
}

# ------------------------------------------------------------ repositórios
if [[ "$VARIANTE" == pc* ]]; then
    passo "Repositórios do Debian ($SUITE)"
    cat > /etc/apt/sources.list <<EOF
deb http://deb.debian.org/debian $SUITE main contrib non-free non-free-firmware
deb http://deb.debian.org/debian $SUITE-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security $SUITE-security main contrib non-free non-free-firmware
EOF
fi

# Sistema leve: não instala "recomendados" automaticamente.
cat > /etc/apt/apt.conf.d/90brisa-leve <<'EOF'
APT::Install-Recommends "false";
APT::Install-Suggests "false";
EOF

# o firmware pede aceite de licença em alguns pacotes
echo "firmware-ipw2x00 firmware-ipw2x00/license/accepted boolean true" | debconf-set-selections || true

passo "Atualizando a lista de pacotes"
apt-get update

# ------------------------------------------------------------ pacotes
LISTAS=("$DIR/pacotes/base.list")
case "$VARIANTE" in
    pc64|pc32) LISTAS+=("$DIR/pacotes/pc.list") ;;
    btv11) LISTAS+=("$DIR/pacotes/btv.list") ;;
esac

PACOTES=()
for lista in "${LISTAS[@]}"; do
    while read -r pacote; do PACOTES+=("$pacote"); done < <(pacotes_da_lista "$lista")
done
[ -n "$KERNEL" ] && PACOTES+=("$KERNEL")

passo "Instalando ${#PACOTES[@]} pacotes"
"${APT[@]}" install "${PACOTES[@]}"
"${APT[@]}" full-upgrade

# Apps do Brisa como pacote: assim o Brisa Suave Update consegue atualizá-los
# pelo repositório do GitHub (o pacote também liga esse repositório e traz a chave).
passo "Pacote brisa-suave"
dpkg -i "$DIR"/brisa-suave_*_all.deb || "${APT[@]}" -f install

# ------------------------------------------------------------ idioma, teclado, horário
passo "Português do Brasil, teclado ABNT2 e horário de Brasília"
sed -i 's/^# *pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen
grep -q '^pt_BR.UTF-8 UTF-8' /etc/locale.gen || echo "pt_BR.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
update-locale LANG=pt_BR.UTF-8 LANGUAGE=pt_BR:pt:en

cat > /etc/default/keyboard <<'EOF'
XKBMODEL="abnt2"
XKBLAYOUT="br"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF

ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
echo "America/Sao_Paulo" > /etc/timezone

echo "brisa-suave" > /etc/hostname
cat > /etc/hosts <<'EOF'
127.0.0.1   localhost
127.0.1.1   brisa-suave
::1         localhost ip6-localhost ip6-loopback
EOF

# ------------------------------------------------------------ identidade
passo "Nome do sistema: Brisa Suave OS"
# shellcheck disable=SC1091
. /etc/brisa-release
BASE_NOME="$(. /usr/lib/os-release && echo "$PRETTY_NAME")"
sed -i "s|^BASE=.*|BASE=\"$BASE_NOME\"|" /etc/brisa-release
rm -f /etc/os-release
sed -e 's/^PRETTY_NAME=.*/PRETTY_NAME="Brisa Suave OS '"$VERSAO"'"/' \
    -e 's/^NAME=.*/NAME="Brisa Suave OS"/' \
    -e 's|^HOME_URL=.*|HOME_URL="https://github.com/"|' \
    /usr/lib/os-release > /etc/os-release
echo "Brisa Suave OS $VERSAO \\n \\l" > /etc/issue
echo "Brisa Suave OS $VERSAO" > /etc/issue.net
mkdir -p /etc/default/grub.d
echo 'GRUB_DISTRIBUTOR="Brisa Suave OS"' > /etc/default/grub.d/90-brisa.cfg
echo 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash loglevel=3"' >> /etc/default/grub.d/90-brisa.cfg

# ------------------------------------------------------------ serviços e ajustes
passo "Serviços"
systemctl enable NetworkManager.service 2>/dev/null || true
systemctl enable lightdm.service 2>/dev/null || true
systemctl enable zramswap.service 2>/dev/null || true
systemctl set-default graphical.target
# NetworkManager cuida de toda a rede
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
    sed -i 's/^managed=false/managed=true/' /etc/NetworkManager/NetworkManager.conf
fi

# toque no touchpad = clique, rolagem natural desligada (igual ao Windows)
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/40-brisa-touchpad.conf <<'EOF'
Section "InputClass"
    Identifier "Brisa touchpad"
    MatchIsTouchpad "on"
    Driver "libinput"
    Option "Tapping" "on"
    Option "TappingButtonMap" "lrm"
    Option "NaturalScrolling" "false"
    Option "DisableWhileTyping" "on"
    Option "ClickMethod" "clickfinger"
EndSection
EOF
cat > /etc/X11/xorg.conf.d/00-brisa-teclado.conf <<'EOF'
Section "InputClass"
    Identifier "Brisa teclado ABNT2"
    MatchIsKeyboard "on"
    Option "XkbLayout" "br"
    Option "XkbModel" "abnt2"
EndSection
EOF

# acerto automático da hora pela internet
systemctl enable systemd-timesyncd.service 2>/dev/null || true

# pasta de estado do modo (Normal/Economia/Gamer); /run é apagado a cada boot
cat > /usr/lib/tmpfiles.d/brisa.conf <<'EOF'
d /run/brisa 0755 root root -
f /run/brisa/modo 0644 root root - normal
EOF

# ------------------------------------------------------------ por versão
case "$VARIANTE" in
pc64|pc32)
    passo "Sessão do pendrive e instalador"
    mkdir -p /etc/live/config.conf.d
    cat > /etc/live/config.conf.d/brisa.conf <<'EOF'
LIVE_HOSTNAME="brisa-suave"
LIVE_USERNAME="brisa"
LIVE_USER_FULLNAME="Brisa Suave"
LIVE_USER_DEFAULT_GROUPS="audio cdrom dip floppy video plugdev netdev powerdev scanner bluetooth sudo"
LIVE_LOCALES="pt_BR.UTF-8"
LIVE_KEYBOARD_MODEL="abnt2"
LIVE_KEYBOARD_LAYOUTS="br"
LIVE_TIMEZONE="America/Sao_Paulo"
EOF
    # No pendrive: sem bloqueio de tela (a senha do pendrive é "live") e ícone "Instalar".
    mkdir -p /usr/lib/live/config
    cat > /usr/lib/live/config/2000-brisa <<'EOF'
#!/bin/sh
USUARIO="brisa"
CASA="/home/$USUARIO"
[ -d "$CASA" ] || exit 0
mkdir -p "$CASA/.config/autostart"
printf '[Desktop Entry]\nType=Application\nName=light-locker\nHidden=true\n' > "$CASA/.config/autostart/light-locker.desktop"
chown -R "$USUARIO:$USUARIO" "$CASA/.config"
# cria as pastas do usuário em português e descobre o nome da pasta da área de trabalho
su "$USUARIO" -c "LANG=pt_BR.UTF-8 xdg-user-dirs-update" 2>/dev/null || true
MESA="$(su "$USUARIO" -c 'xdg-user-dir DESKTOP' 2>/dev/null)"
[ -n "$MESA" ] && [ "$MESA" != "$CASA" ] || MESA="$CASA/Área de trabalho"
mkdir -p "$MESA"
for arquivo in /usr/share/applications/install-debian.desktop /usr/share/applications/calamares.desktop; do
    if [ -f "$arquivo" ]; then
        sed -e 's/^Name=.*/Name=Instalar o Brisa Suave OS/' -e '/^Name\[/d' \
            -e '/^Comment\[/d' -e 's/^Comment=.*/Comment=Instala o Brisa Suave OS no HD/' \
            -e 's|^Icon=.*|Icon=/usr/share/brisa/logo.svg|' "$arquivo" \
            > "$MESA/instalar-brisa.desktop"
        chmod +x "$MESA/instalar-brisa.desktop"
        break
    fi
done
chown -R "$USUARIO:$USUARIO" "$MESA"
# o live-config cria pastas soltas quando o nome tem espaço ("Área", "de", "trabalho")
for solta in "Área" "de" "trabalho"; do rmdir "$CASA/$solta" 2>/dev/null || true; done
# o Xfce só abre atalhos da área de trabalho marcados como confiáveis
su "$USUARIO" -c "gio set '$MESA/instalar-brisa.desktop' metadata::xfce-exe-checksum \"\$(sha256sum '$MESA/instalar-brisa.desktop' | cut -d' ' -f1)\"" 2>/dev/null || true
EOF
    chmod +x /usr/lib/live/config/2000-brisa

    # instalador Calamares com a cara do Brisa
    if [ -d /etc/calamares ] && [ -d "$DIR/calamares" ]; then
        mkdir -p /etc/calamares/branding/brisa
        cp -r "$DIR/calamares/brisa/." /etc/calamares/branding/brisa/
        sed -i 's/^branding:.*/branding: brisa/' /etc/calamares/settings.conf
        if [ -f /etc/calamares/modules/users.conf ]; then
            sed -i 's/^doAutologin:.*/doAutologin: true/' /etc/calamares/modules/users.conf
            grep -q '^doAutologin:' /etc/calamares/modules/users.conf || echo "doAutologin: true" >> /etc/calamares/modules/users.conf
        fi
        cat > /etc/calamares/modules/locale.conf <<'EOF'
---
region: "America"
zone: "Sao_Paulo"
localeGenPath: "/etc/locale.gen"
geoip:
    style: "none"
EOF
        cat > /etc/calamares/modules/keyboard.conf <<'EOF'
---
xOrgConfFileName: "/etc/X11/xorg.conf.d/00-keyboard.conf"
convertedKeymapPath: "/lib/kbd/keymaps/xkb"
writeEtcDefaultKeyboard: true
EOF
    fi
    ;;
btv11)
    passo "Usuário e entrada automática no BTV"
    if ! id brisa >/dev/null 2>&1; then
        useradd -m -s /bin/bash -c "Brisa Suave" brisa
    fi
    echo "brisa:brisa" | chpasswd
    for grupo in sudo audio video plugdev netdev bluetooth input render; do
        getent group "$grupo" >/dev/null && usermod -aG "$grupo" brisa
    done
    mkdir -p /etc/lightdm/lightdm.conf.d
    cat > /etc/lightdm/lightdm.conf.d/50-brisa-autologin.conf <<'EOF'
[Seat:*]
autologin-user=brisa
autologin-user-timeout=0
user-session=xfce
EOF
    groupadd -f autologin
    usermod -aG autologin brisa
    # pula o assistente de primeiro acesso do Armbian (o Brisa já criou o usuário)
    rm -f /root/.not_logged_in_yet
    # trava o kernel e a inicialização: uma atualização deles pode deixar a TV box com tela preta
    TRAVAR="$(dpkg-query -W -f='${Package}\n' 'linux-image-*' 'linux-dtb-*' 'linux-u-boot-*' 'armbian-bsp-*' 2>/dev/null || true)"
    if [ -n "$TRAVAR" ]; then
        # shellcheck disable=SC2086
        apt-mark hold $TRAVAR
    fi
    ;;
esac

# ------------------------------------------------------------ apps do Brisa
passo "Apps do Brisa"
chmod 755 /usr/lib/brisa/brisa-helper /usr/bin/brisa-*
python3 -m compileall -q /usr/lib/brisa/brisa || true
command -v update-desktop-database >/dev/null && update-desktop-database -q || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true

# Some apps do menu que confundem (configurações duplicadas, avançadas demais)
for escondido in xfce4-about debian-xterm debian-uxterm vim; do
    [ -f "/usr/share/applications/$escondido.desktop" ] && \
        echo "NoDisplay=true" >> "/usr/share/applications/$escondido.desktop"
done

# ------------------------------------------------------------ limpeza
passo "Limpando"
apt-get -y autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/* /var/cache/apt/*.bin /var/tmp/*
find /tmp -mindepth 1 -maxdepth 1 ! -name brisa -exec rm -rf {} +
: > /etc/machine-id
rm -f /var/lib/dbus/machine-id
find /var/log -type f -exec truncate -s 0 {} \;
echo "  -> Pronto: $VARIANTE"
