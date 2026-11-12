"""Roda no login: no primeiro, aplica o tema azul e o papel de parede do Brisa."""
import sys
import time

from brisa import comum

MARCA = comum.CONFIG / "primeiro-login-feito"


def main():
    if MARCA.exists():
        # nos próximos logins, só garante que o papel de parede escolhido continua lá
        return 0
    time.sleep(3)  # espera a área de trabalho terminar de abrir
    comum.aplicar_tema("azul")
    comum.CONFIG.mkdir(parents=True, exist_ok=True)
    MARCA.write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
