#!/usr/bin/env python3
"""Gera os papéis de parede do Brisa Suave OS (um para cada tema de cor).

Uso: python3 build/gerar-papeis-de-parede.py
Os arquivos .svg vão para overlay/usr/share/brisa/wallpapers/.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "overlay" / "usr" / "share" / "brisa" / "wallpapers"

# nome: (cor do topo, cor de baixo, cor das ondas)
TEMAS = {
    "azul": ("#0B2E6B", "#2F86E8", "#7CC0FF"),
    "roxo": ("#2A0F5C", "#7B3FE4", "#C4A2FF"),
    "verde": ("#0B3D2E", "#1F9E6E", "#8EE6C2"),
    "laranja": ("#5C1F05", "#E8742F", "#FFC48C"),
    "escuro": ("#05070D", "#1B2233", "#4FA8FF"),
}

MODELO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="ceu" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{topo}"/>
      <stop offset="1" stop-color="{baixo}"/>
    </linearGradient>
    <radialGradient id="brilho" cx="0.72" cy="0.28" r="0.6">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#ceu)"/>
  <rect width="1920" height="1080" fill="url(#brilho)"/>
  <g fill="none" stroke="{onda}" stroke-linecap="round">
    <path d="M-50 720 C 380 600, 720 860, 1120 720 S 1760 580, 1980 680" stroke-width="3" opacity="0.55"/>
    <path d="M-50 770 C 420 650, 760 910, 1160 770 S 1780 640, 1980 740" stroke-width="2" opacity="0.40"/>
    <path d="M-50 820 C 460 700, 800 960, 1200 820 S 1800 700, 1980 800" stroke-width="1.5" opacity="0.28"/>
  </g>
  <g fill="{onda}" opacity="0.10">
    <path d="M0 880 C 420 800, 820 1000, 1240 900 S 1760 820, 1920 860 V1080 H0 Z"/>
  </g>
  <text x="96" y="1010" font-family="Noto Sans, DejaVu Sans, sans-serif" font-size="34" font-weight="300" fill="#FFFFFF" opacity="0.55" letter-spacing="6">BRISA SUAVE OS</text>
</svg>
"""


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nome, (topo, baixo, onda) in TEMAS.items():
        arquivo = DESTINO / f"brisa-{nome}.svg"
        arquivo.write_text(MODELO.format(topo=topo, baixo=baixo, onda=onda), encoding="utf-8", newline="\n")
        print("criado:", arquivo.relative_to(RAIZ))


if __name__ == "__main__":
    main()
