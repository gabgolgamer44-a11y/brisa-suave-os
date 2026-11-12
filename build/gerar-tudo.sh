#!/bin/bash
# Gera as três versões do Brisa Suave OS, uma depois da outra.
#   build/gerar-tudo.sh <imagem-do-armbian para o BTV>
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

"$DIR/gerar-pc.sh" 64
"$DIR/gerar-pc.sh" 32
if [ -n "${1:-${ARMBIAN_IMAGEM:-}}" ]; then
    "$DIR/gerar-btv.sh" "${1:-$ARMBIAN_IMAGEM}"
else
    echo "Versão do BTV pulada: informe a imagem do Armbian (veja docs/BTV11.md)."
fi
