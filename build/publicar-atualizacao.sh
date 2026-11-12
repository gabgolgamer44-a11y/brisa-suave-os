#!/bin/bash
# Publica uma nova versão dos apps do Brisa no repositório de atualizações
# (GitHub Pages, branch gh-pages). Todos os Brisa Suave OS recebem pelo Brisa Suave Update.
#
#   build/publicar-atualizacao.sh 1.0.1
#
# Precisa da chave secreta de assinatura (fica só no computador de quem publica,
# em BRISA_GNUPG, padrão /root/.brisa-gnupg) e do login no GitHub (gh auth login).
set -euo pipefail
. "$(dirname "$0")/comum.sh"
exigir_comandos git gpg apt-ftparchive dpkg-deb gzip

VERSAO="${1:?informe a versão, ex.: build/publicar-atualizacao.sh 1.0.1}"
export GNUPGHOME="${BRISA_GNUPG:-/root/.brisa-gnupg}"
CHAVE="Brisa Suave OS"
gpg --list-secret-keys "$CHAVE" >/dev/null 2>&1 || falha "chave de assinatura não encontrada em $GNUPGHOME"

# confere se a chave pública do projeto é a mesma da chave secreta
cmp -s <(gpg --export "$CHAVE") "$PROJETO/apt/brisa.gpg" || \
    falha "apt/brisa.gpg não bate com a chave secreta. Não publique com chave errada."

passo "Empacotando a versão $VERSAO"
bash "$PROJETO/build/empacotar.sh" "$VERSAO"
DEB="$SAIDA/brisa-suave_${VERSAO}_all.deb"

passo "Preparando a branch gh-pages"
PAGINAS="$TRABALHO/gh-pages"
cd "$PROJETO"
git fetch -q origin gh-pages 2>/dev/null || true
if [ ! -d "$PAGINAS/.git" ] && [ ! -f "$PAGINAS/.git" ]; then
    rm -rf "$PAGINAS"
    if git show-ref -q --verify refs/remotes/origin/gh-pages; then
        git worktree add -f "$PAGINAS" -B gh-pages origin/gh-pages
    else
        git worktree add -f --detach "$PAGINAS"
        ( cd "$PAGINAS" && git checkout -q --orphan gh-pages && git rm -rq . && git clean -fdq )
    fi
else
    ( cd "$PAGINAS" && git checkout -q gh-pages && { git pull -q --ff-only origin gh-pages 2>/dev/null || true; } )
fi

cd "$PAGINAS"
POOL="pool/main/b/brisa-suave"
mkdir -p "$POOL"
[ -f "$POOL/$(basename "$DEB")" ] && falha "a versão $VERSAO já foi publicada. Use um número maior."
cp "$DEB" "$POOL/"

passo "Gerando os índices do repositório"
for arq in amd64 i386 arm64; do
    pasta="dists/estavel/main/binary-$arq"
    mkdir -p "$pasta"
    apt-ftparchive packages pool > "$pasta/Packages"
    gzip -9kf "$pasta/Packages"
done
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin="Brisa Suave OS" \
    -o APT::FTPArchive::Release::Label="Brisa Suave OS" \
    -o APT::FTPArchive::Release::Suite="estavel" \
    -o APT::FTPArchive::Release::Codename="estavel" \
    -o APT::FTPArchive::Release::Architectures="amd64 i386 arm64" \
    -o APT::FTPArchive::Release::Components="main" \
    -o APT::FTPArchive::Release::Description="Apps do Brisa Suave OS" \
    release dists/estavel > /tmp/Release.brisa
mv /tmp/Release.brisa dists/estavel/Release

passo "Assinando"
rm -f dists/estavel/InRelease dists/estavel/Release.gpg
gpg --batch --yes --pinentry-mode loopback --passphrase '' --local-user "$CHAVE" \
    --clearsign -o dists/estavel/InRelease dists/estavel/Release
gpg --batch --yes --pinentry-mode loopback --passphrase '' --local-user "$CHAVE" \
    -abs -o dists/estavel/Release.gpg dists/estavel/Release

cp "$PROJETO/apt/brisa.gpg" "$PROJETO/apt/brisa.asc" .
touch .nojekyll
cat > index.html <<EOF
<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brisa Suave OS: atualizações</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#10203a;background:#f4f8ff}
code,pre{background:#e3edff;border-radius:6px;padding:2px 6px}pre{padding:12px;overflow-x:auto}h1{color:#1257C9}</style></head>
<body><h1>Brisa Suave OS: repositório de atualizações</h1>
<p>Daqui o <b>Brisa Suave Update</b> baixa as novidades do Brisa Suave Central, Update, Store e dos temas.
Quem usa o Brisa Suave OS não precisa fazer nada: já vem configurado.</p>
<p>Versão atual dos apps: <b>$VERSAO</b></p>
<p>Para adicionar à mão num Debian:</p>
<pre>sudo curl -fsSL -o /usr/share/keyrings/brisa.gpg https://gabgolgamer44-a11y.github.io/brisa-suave-os/brisa.gpg
echo "deb [signed-by=/usr/share/keyrings/brisa.gpg] https://gabgolgamer44-a11y.github.io/brisa-suave-os estavel main" | sudo tee /etc/apt/sources.list.d/brisa.list</pre>
<p><a href="https://github.com/gabgolgamer44-a11y/brisa-suave-os">Código do projeto no GitHub</a></p>
</body></html>
EOF

passo "Enviando para o GitHub"
git add -A
git -c user.name="$(git -C "$PROJETO" config user.name)" -c user.email="$(git -C "$PROJETO" config user.email)" \
    commit -q -m "Atualização dos apps do Brisa: versão $VERSAO"
git push -q -u origin gh-pages
echo
echo "Publicado: brisa-suave $VERSAO"
echo "Os Brisa Suave OS recebem a atualização na próxima verificação do Brisa Suave Update."
