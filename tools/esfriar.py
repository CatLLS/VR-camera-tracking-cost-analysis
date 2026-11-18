#!/usr/bin/env python3
"""Espera o celular esfriar antes da próxima execução.

Lê a temperatura da bateria (dumpsys battery) via adb.

  python tools/esfriar.py --repouso
      Mede a temperatura de repouso do dia (celular parado, tela apagada há
      15 min) e grava em dados/repouso_<data>.txt. Fazer uma vez por dia, antes
      da primeira execução.

  python tools/esfriar.py
      Mostra a temperatura a cada 15 s e avisa (com bipe) quando ela voltar a
      no máximo repouso + 1,0 °C. Também avisa se a bateria estiver abaixo de 50%.

  python tools/esfriar.py --alvo 31.5
      Usa um alvo explícito em vez do repouso gravado.

Só usa a biblioteca padrão. Precisa do adb no PATH.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime

TOLERANCIA_C = 1.0
BATERIA_MIN = 50


def bateria(serial=None):
    cmd = ["adb"] + (["-s", serial] if serial else []) + ["shell", "dumpsys", "battery"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    temp = re.search(r"temperature:\s*(-?\d+)", out)
    nivel = re.search(r"level:\s*(\d+)", out)
    carregando = any(re.search(rf"{k} powered:\s*true", out) for k in ("AC", "USB", "Wireless"))
    if not temp:
        sys.exit("Não consegui ler a temperatura. O celular está conectado? Saída do adb:\n" + out)
    return int(temp.group(1)) / 10.0, int(nivel.group(1)) if nivel else None, carregando


def arquivo_repouso(base):
    return os.path.join(base, f"repouso_{date.today().isoformat()}.txt")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repouso", action="store_true", help="mede e grava a temperatura de repouso do dia")
    ap.add_argument("--alvo", type=float, help="temperatura alvo em °C (em vez do repouso + 1,0)")
    ap.add_argument("--serial", default=None)
    ap.add_argument("--dados", default="dados", help="pasta onde fica o repouso do dia")
    args = ap.parse_args()

    try:
        subprocess.run(["adb", "version"], capture_output=True, timeout=15)
    except FileNotFoundError:
        sys.exit("adb não encontrado. Instale o Android platform-tools e coloque-o no PATH.")

    if args.repouso:
        temp, nivel, carregando = bateria(args.serial)
        os.makedirs(args.dados, exist_ok=True)
        with open(arquivo_repouso(args.dados), "w", encoding="utf-8") as fh:
            fh.write(f"{temp}\n# medido em {datetime.now().isoformat(timespec='seconds')}, bateria {nivel}%\n")
        print(f"Repouso de hoje: {temp:.1f} °C (bateria {nivel}%). Gravado em {arquivo_repouso(args.dados)}")
        print(f"Alvo para começar cada execução: até {temp + TOLERANCIA_C:.1f} °C")
        if carregando:
            print("ATENÇÃO: o celular está carregando. Meça o repouso com ele fora do carregador.")
        return

    if args.alvo is not None:
        alvo = args.alvo
    else:
        caminho = arquivo_repouso(args.dados)
        if not os.path.exists(caminho):
            sys.exit(f"Não achei {caminho}. Rode antes: python tools/esfriar.py --repouso")
        with open(caminho, encoding="utf-8") as fh:
            alvo = float(fh.readline().strip()) + TOLERANCIA_C

    print(f"Esperando a bateria chegar a {alvo:.1f} °C ou menos. Deixe a tela do celular apagada. Ctrl+C para sair.")
    inicio = time.time()
    while True:
        temp, nivel, carregando = bateria(args.serial)
        minutos = (time.time() - inicio) / 60
        extra = "  (carregando)" if carregando else ""
        print(f"  {minutos:4.1f} min  bateria {temp:.1f} °C  nível {nivel}%{extra}")
        if temp <= alvo and not carregando:
            print("\aPRONTO: pode fazer a próxima execução.")
            if nivel is not None and nivel < BATERIA_MIN:
                print(f"\aATENÇÃO: bateria em {nivel}%, abaixo de {BATERIA_MIN}%. Carregue antes de medir (ver guia).")
            return
        time.sleep(15)


if __name__ == "__main__":
    main()
