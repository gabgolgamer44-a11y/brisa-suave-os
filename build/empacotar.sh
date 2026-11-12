#!/bin/bash
# Empacota os apps do Brisa num pacote .deb, que o Brisa Suave Update sabe atualizar.
#   build/empacotar.sh 1.0.1   ->  saida/brisa-suave_1.0.1_all.deb
#
# O pacote leva: Central, Update, Store, modo gamer, ajudante, catálogo da loja,
# ícones, papéis de parede, a chave pública e o endereço do repositório de atualizações.
set -euo pipefail
. "$(dirname "$0")/comum.sh"
exigir_comandos dpkg-deb rsync

VERSAO="${1:?informe a versão, ex.: build/empacotar.sh 1.0.1}"
[[ "$VERSAO" =~ ^[0-9]+(\.[0-9]+)*$ ]] || falha "versão inválida: $VERSAO"
ENDERECO="${BRISA_REPO_URL:-https://gabgolgamer44-a11y.github.io/brisa-suave-os}"

PACOTE="$TRABALHO/pacote/brisa-suave"
rm -rf "$PACOTE"
mkdir -p "$PACOTE/DEBIAN" "$SAIDA"

# apps
install -d "$PACOTE/usr/lib/brisa/brisa" "$PACOTE/usr/bin"
install -m 644 "$PROJETO"/apps/brisa/*.py "$PACOTE/usr/lib/brisa/brisa/"
install -m 755 "$PROJETO/apps/helper/brisa-helper" "$PACOTE/usr/lib/brisa/brisa-helper"
install -m 755 "$PROJETO/overlay/usr/lib/brisa/brisa-polkit-agente" "$PACOTE/usr/lib/brisa/brisa-polkit-agente"
for app in "$PROJETO"/apps/bin/*; do
    install -m 755 "$app" "$PACOTE/usr/bin/$(basename "$app")"
done
install -D -m 644 "$PROJETO/apps/polkit/org.brisa.helper.policy" \
    "$PACOTE/usr/share/polkit-1/actions/org.brisa.helper.policy"

# visual, catálogo e atalhos do menu
rsync -rlt --chmod=D755,F644 "$PROJETO/overlay/usr/share/brisa/" "$PACOTE/usr/share/brisa/"
install -m 644 "$PROJETO/branding/logo.svg" "$PACOTE/usr/share/brisa/logo.svg"
install -D -m 644 "$PROJETO/apps/store/catalogo.json" "$PACOTE/usr/share/brisa/store/catalogo.json"
install -d "$PACOTE/usr/share/applications" "$PACOTE/etc/xdg/autostart"
install -m 644 "$PROJETO"/overlay/usr/share/applications/brisa-*.desktop "$PACOTE/usr/share/applications/"
install -m 644 "$PROJETO"/overlay/etc/xdg/autostart/brisa-*.desktop "$PACOTE/etc/xdg/autostart/"

# repositório de atualizações: chave pública e endereço
install -D -m 644 "$PROJETO/apt/brisa.gpg" "$PACOTE/usr/share/keyrings/brisa.gpg"
install -d "$PACOTE/etc/apt/sources.list.d"
cat > "$PACOTE/etc/apt/sources.list.d/brisa.sources" <<EOF
# Atualizações dos apps do Brisa Suave OS (Central, Update, Store, temas)
Types: deb
URIs: $ENDERECO
Suites: estavel
Components: main
Signed-By: /usr/share/keyrings/brisa.gpg
EOF

# arquivos de configuração: o usuário pode mudar e a atualização não apaga
( cd "$PACOTE" && find etc -type f | sed 's|^|/|' ) > "$PACOTE/DEBIAN/conffiles"

TAMANHO="$(du -sk --exclude=DEBIAN "$PACOTE" | cut -f1)"
cat > "$PACOTE/DEBIAN/control" <<EOF
Package: brisa-suave
Version: $VERSAO
Architecture: all
Maintainer: Brisa Suave OS <atualizacoes@brisa-suave-os.invalid>
Installed-Size: $TAMANHO
Depends: python3, python3-gi, gir1.2-gtk-3.0, pkexec | policykit-1, libnotify-bin, xfconf, x11-xserver-utils
Recommends: librsvg2-common, gamemode, papirus-icon-theme, arc-theme
Section: misc
Priority: optional
Homepage: https://github.com/gabgolgamer44-a11y/brisa-suave-os
Description: Apps do Brisa Suave OS
 Brisa Suave Central (modos Normal, Economia e Gamer, aparência, data e hora),
 Brisa Suave Update (atualizações) e Brisa Suave Store (loja de aplicativos),
 com os ícones, papéis de parede e o repositório de atualizações do Brisa.
EOF

cat > "$PACOTE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    command -v update-desktop-database >/dev/null && update-desktop-database -q || true
    python3 -m compileall -q /usr/lib/brisa/brisa >/dev/null 2>&1 || true
fi
exit 0
EOF
cat > "$PACOTE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
find /usr/lib/brisa/brisa -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
exit 0
EOF
chmod 755 "$PACOTE/DEBIAN/postinst" "$PACOTE/DEBIAN/prerm"

ARQUIVO="$SAIDA/brisa-suave_${VERSAO}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$PACOTE" "$ARQUIVO" >/dev/null
echo "Pacote pronto: $ARQUIVO"
