#!/usr/bin/env python3
"""Copia para o PC os CSV que a página baixou no celular.

Procura em /sdcard/Download os arquivos resumo_*.csv, quadros_*.csv e
threads_*.csv e copia para dados/pagina/ os que ainda não estão lá.

  python tools/puxar_csv.py

Só usa a biblioteca padrão. Precisa do adb no PATH.
"""

import argparse
import os
import re
import subprocess
import sys

ORIGEM = "/sdcard/Download"
PADRAO = re.compile(r"^(resumo|quadros|threads)_.*\.csv$")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", default=None)
    ap.add_argument("--destino", default=os.path.join("dados", "pagina"))
    args = ap.parse_args()
    adb = ["adb"] + (["-s", args.serial] if args.serial else [])

    try:
        res = subprocess.run(adb + ["shell", "ls", "-1", ORIGEM], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        sys.exit("adb não encontrado. Instale o Android platform-tools e coloque-o no PATH.")
    nomes = [n.strip() for n in res.stdout.splitlines() if PADRAO.match(n.strip())]
    if not nomes:
        sys.exit(f"Nenhum CSV da página em {ORIGEM}. Toque em 'Baixar todas (CSV)' no celular antes.")

    os.makedirs(args.destino, exist_ok=True)
    copiados = 0
    for nome in nomes:
        alvo = os.path.join(args.destino, nome)
        if os.path.exists(alvo):
            continue
        r = subprocess.run(adb + ["pull", f"{ORIGEM}/{nome}", alvo], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  falhou: {nome}: {r.stderr.strip()}")
            continue
        print(f"  copiado: {nome}")
        copiados += 1
    print(f"Pronto: {copiados} arquivo(s) novo(s) em {args.destino} ({len(nomes) - copiados} já existiam).")


if __name__ == "__main__":
    main()
