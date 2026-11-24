#!/usr/bin/env python3
"""Copia para o PC os CSV que a página baixou no celular.

Procura em /sdcard/Download os arquivos resumo_*.csv, quadros_*.csv e
threads_*.csv e copia para dados/pagina/ os que ainda não estão em dados/
(compara o conteúdo, não só o nome).

  python tools/puxar_csv.py

Só usa a biblioteca padrão. Usa o adb de tools/platform-tools (ou, se não existir, o do PATH).
"""

import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile

ORIGEM = "/sdcard/Download"
PADRAO = re.compile(r"^(resumo|quadros|threads)_.*\.csv$")


def adb_exe():
    """adb da pasta tools/platform-tools, se existir; senão, o do PATH."""
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools",
                         "adb.exe" if os.name == "nt" else "adb")
    return local if os.path.exists(local) else "adb"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", default=None)
    ap.add_argument("--destino", default=os.path.join("dados", "pagina"))
    args = ap.parse_args()
    adb = [adb_exe()] + (["-s", args.serial] if args.serial else [])

    try:
        res = subprocess.run(adb + ["shell", "ls", "-1", ORIGEM], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except FileNotFoundError:
        sys.exit("adb não encontrado. Extraia o Android platform-tools em tools/platform-tools (ver TestGuide).")
    nomes = [n.strip() for n in res.stdout.splitlines() if PADRAO.match(n.strip())]
    if not nomes:
        sys.exit(f"Nenhum CSV da página em {ORIGEM}. Toque em 'Baixar todas (CSV)' no celular antes.")

    os.makedirs(args.destino, exist_ok=True)
    # Um arquivo cujo conteúdo já está em qualquer lugar de dados/ (inclusive
    # em dados/descartado/) não é copiado de novo. Compara o conteúdo, não só o
    # nome: o "Baixar todas" do mesmo dia gera sempre o mesmo nome.
    ja_existem = {}
    for pasta, _, arquivos in os.walk("dados"):
        for n in arquivos:
            ja_existem.setdefault(n, []).append(os.path.join(pasta, n))
    temp = tempfile.mkdtemp()
    copiados = 0
    for nome in nomes:
        baixado = os.path.join(temp, nome)
        r = subprocess.run(adb + ["pull", f"{ORIGEM}/{nome}", baixado], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0:
            print(f"  falhou: {nome}: {r.stderr.strip()}")
            continue
        if any(filecmp.cmp(baixado, p, shallow=False) for p in ja_existem.get(nome, [])):
            continue
        # Mesmo nome com conteúdo diferente: grava como "nome (2).csv", "(3)"...
        alvo = os.path.join(args.destino, nome)
        base, ext = os.path.splitext(nome)
        n = 2
        while os.path.exists(alvo):
            alvo = os.path.join(args.destino, f"{base} ({n}){ext}")
            n += 1
        shutil.move(baixado, alvo)
        print(f"  copiado: {os.path.basename(alvo)}")
        copiados += 1
    shutil.rmtree(temp, ignore_errors=True)
    print(f"Pronto: {copiados} arquivo(s) novo(s) em {args.destino} ({len(nomes) - copiados} já estavam em dados/).")


if __name__ == "__main__":
    main()
