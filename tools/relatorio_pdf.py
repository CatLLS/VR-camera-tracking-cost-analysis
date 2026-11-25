#!/usr/bin/env python3
"""Gera RELATORIO.pdf a partir de RELATORIO.md (Markdown -> HTML -> PDF pelo Chrome sem janela).

  pip install markdown
  python tools/relatorio_pdf.py

Os links relativos do relatório viram links para o repositório no GitHub, para funcionarem no PDF.
"""

import os
import pathlib
import re
import subprocess
import sys
import tempfile

import markdown

RAIZ = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/CatLLS/VR-camera-tracking-cost-analysis"
CHROMES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
           "google-chrome", "chromium"]

CSS = """
@page { size: A4; margin: 14mm 15mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.6pt; line-height: 1.38; color: #111; }
h1 { font-size: 16pt; margin: 0 0 4pt; }
h2 { font-size: 12.5pt; margin: 13pt 0 4pt; border-bottom: 1px solid #bbb; padding-bottom: 2pt;
     break-after: avoid; }
h3 { font-size: 10.5pt; margin: 9pt 0 3pt; break-after: avoid; }
p { margin: 3pt 0 5pt; }
ul { margin: 2pt 0 5pt; padding-left: 16pt; }
li { margin: 1pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 6pt; font-size: 8.4pt; break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 2.5pt 4pt; vertical-align: top; }
th { background: #f0f0f0; }
img { max-width: 100%; }
p > img { display: block; margin: 4pt auto; max-height: 92mm; }
td img { width: 100%; }
code { font-family: Consolas, monospace; font-size: 8.5pt; background: #f4f4f4; padding: 0 2pt; }
a { color: #0645ad; text-decoration: none; }
hr { border: 0; border-top: 1px solid #ddd; margin: 6pt 0; }
"""


def link_github(m):
    attr, alvo = m.group(1), m.group(2)
    if re.match(r"^[a-z]+:", alvo) or alvo.startswith("#"):
        return m.group(0)
    tipo = "tree" if alvo.endswith("/") else "blob"
    return f'{attr}="{REPO}/{tipo}/main/{alvo}"'


def main():
    md = (RAIZ / "RELATORIO.md").read_text(encoding="utf-8")
    corpo = markdown.markdown(md, extensions=["tables"])
    corpo = re.sub(r'(href)="([^"]+)"', link_github, corpo)
    base = (RAIZ.as_uri() + "/")
    html = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><base href="{base}">'
            f"<title>Relatório — Custo do ARCore</title><style>{CSS}</style></head><body>{corpo}</body></html>")
    tmp = pathlib.Path(tempfile.mkdtemp())
    pagina = tmp / "relatorio.html"
    pagina.write_text(html, encoding="utf-8")
    saida = RAIZ / "RELATORIO.pdf"
    chrome = next((c for c in CHROMES if os.path.exists(c)), None)
    if chrome is None:
        sys.exit("Não achei o Chrome/Edge. Abra o HTML gerado e imprima em PDF: " + str(pagina))
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={tmp / 'perfil'}", f"--print-to-pdf={saida}", pagina.as_uri()],
                   check=True, capture_output=True, timeout=120)
    print(f"Pronto: {saida}")


if __name__ == "__main__":
    main()
