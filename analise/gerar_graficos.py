#!/usr/bin/env python3
"""Gera as tabelas e os gráficos das 4 frentes a partir de dados/.

  python analise/gerar_graficos.py

Precisa de: pip install matplotlib numpy

Entrada (só leitura, nada em dados/ é alterado):
  dados/pagina/resumo_*.csv, quadros_*.csv, threads_*.csv  (exportados pela página)
  dados/adb/<rotulo>_<data-hora>/amostras.csv, meta.txt      (coletor_adb.py)
  analise/correcoes.csv                                      (rótulos digitados errado)

Saída:
  analise/tabelas/*.csv
  analise/graficos/*.png

Como cada execução é escolhida e como as janelas são recortadas: ver analise/README.md.
"""

import csv
import glob
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "dados")
SAIDA = os.path.dirname(os.path.abspath(__file__))
GRAF = os.path.join(SAIDA, "graficos")
TAB = os.path.join(SAIDA, "tabelas")

THREADS = [0, 2, 4, 6]
TITULO_GRUPO = ("Ligar o ARCore sempre custa caro, mas o custo relativo diminui\n"
                "quando o jogo já ocupa mais threads")
TITULO_F3 = ("Com 6 threads, o clock dos núcleos Gold chega ao teto de ~1460 MHz em 4 min\n"
             "e o p95 sobe até ficar parecido com o de 0 threads")
MODOS = ["sem-ar", "ar"]
NOME_MODO = {"sem-ar": "Sem AR (só a cena)", "ar": "Com AR (ARCore)"}
COR = {"sem-ar": "#4C72B0", "ar": "#DD8452"}
SILVER = [f"cpu{i}" for i in range(4)]
GOLD = [f"cpu{i}" for i in range(4, 8)]
DURACAO_PRINCIPAL = 120
DURACAO_LONGA = 900
# Página e coletor alinhados pelo relógio quando começam a menos disso um do outro.
ALINHAMENTO_MAX_S = 30
# Janela fixa (s desde o início do coletor) quando o relógio da página não serve.
JANELA_FIXA_S = (15, 120)


# ---------------------------------------------------------------------------
# Leitura

def ler_csv(caminho):
    with open(caminho, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def ler_correcoes():
    pag, col = {}, {}
    caminho = os.path.join(SAIDA, "correcoes.csv")
    if os.path.exists(caminho):
        for r in ler_csv(caminho):
            (pag if r["tipo"] == "pagina" else col).setdefault(r["id"], {})[r["campo"]] = r["valor_correto"]
    return pag, col


def ler_pagina(prefixo):
    """Linhas de todos os <prefixo>_*.csv, sem repetir run_id.

    "Baixar todas" exporta tudo o que está no celular, então os arquivos se
    sobrepõem. Os arquivos maiores são lidos primeiro e um run_id só é aceito do
    primeiro arquivo em que aparece.
    """
    arquivos = sorted(glob.glob(os.path.join(DADOS, "pagina", f"{prefixo}_*.csv")),
                      key=os.path.getsize, reverse=True)
    vistos, linhas = set(), []
    for arq in arquivos:
        novos = set()
        for r in ler_csv(arq):
            if r["run_id"] in vistos:
                continue
            novos.add(r["run_id"])
            linhas.append(r)
        vistos |= novos
    return linhas


def ler_coletor(pasta):
    meta = {}
    with open(os.path.join(pasta, "meta.txt"), encoding="utf-8") as fh:
        for linha in fh:
            if "=" in linha:
                k, v = linha.rstrip("\n").split("=", 1)
                meta.setdefault(k, v)
    serie = defaultdict(list)  # (metrica, chave) -> [(epoch_ms, valor)]
    for r in ler_csv(os.path.join(pasta, "amostras.csv")):
        serie[(r["metrica"], r["chave"])].append((int(r["epoch_ms"]), num(r["valor"])))
    tempos = sorted({t for pts in serie.values() for t, _ in pts})
    return {"pasta": os.path.basename(pasta), "meta": meta, "serie": serie,
            "inicio": tempos[0] if tempos else None, "fim": tempos[-1] if tempos else None,
            "amostras": int(meta.get("amostras", 0) or 0)}


# ---------------------------------------------------------------------------
# Escolha das execuções

def escolher_execucoes():
    corr_pag, corr_col = ler_correcoes()
    resumo = ler_pagina("resumo")
    for r in resumo:
        for campo, valor in corr_pag.get(r["run_id"], {}).items():
            r[campo] = valor
            r["corrigido"] = "sim"

    coletores = []
    for pasta in sorted(glob.glob(os.path.join(DADOS, "adb", "*", ""))):
        c = ler_coletor(pasta.rstrip("\\/"))
        c["rotulo"] = corr_col.get(c["pasta"], {}).get("rotulo", c["meta"].get("rotulo", ""))
        coletores.append(c)

    def valida(r, duracao):
        return (int(num(r["duration_s"])) == duracao and r["aborted"] == "0"
                and num(r["frames_measured"]) > 0)

    escolhidas = {}
    for duracao, prefixo in ((DURACAO_PRINCIPAL, ""), (DURACAO_LONGA, "15min_")):
        grupos = defaultdict(list)
        for r in resumo:
            if valida(r, duracao):
                grupos[(r["condition"], int(r["rep"]))].append(r)
        for (cond, rep), rs in grupos.items():
            # Execução repetida: vale a última (o guia manda refazer no fim da rodada).
            rs.sort(key=lambda r: int(r["start_epoch_ms"]))
            r = dict(rs[-1])
            r["descartadas_mesma_cond"] = len(rs) - 1
            rotulo = f"{prefixo}{cond}_r{rep}"
            minimo = 0.7 * (duracao + 20)
            cands = [c for c in coletores if c["rotulo"] == rotulo and c["amostras"] >= minimo]
            r["coletor"] = cands[-1] if cands else None
            escolhidas[(duracao, cond, rep)] = r
    return escolhidas, resumo, coletores


def janela_coletor(r):
    """(ini_ms, fim_ms, como) da parte do coletor que corresponde à medição."""
    c = r["coletor"]
    ini_pag = int(r["start_epoch_ms"]) + 1000 * num(r["warmup_s"])
    fim_pag = int(r["end_epoch_ms"])
    if abs(int(r["start_epoch_ms"]) - c["inicio"]) < ALINHAMENTO_MAX_S * 1000:
        return ini_pag, fim_pag, "relogio"
    # O relógio da página (performance.timeOrigin) para quando o celular dorme
    # com a tela apagada entre execuções, então fica atrasado. Aí usa-se uma
    # janela fixa a partir do início do coletor (o guia manda iniciar a página
    # até 10 s depois do coletor).
    a, b = JANELA_FIXA_S
    if int(num(r["duration_s"])) == DURACAO_LONGA:
        b = DURACAO_LONGA
    return c["inicio"] + a * 1000, c["inicio"] + b * 1000, "janela_fixa"


def p95(valores):
    """Percentil 95 pelo posto mais próximo, igual ao da página."""
    v = np.sort(np.asarray(valores, dtype=float))
    return float(v[min(len(v) - 1, int(np.ceil(0.95 * len(v))) - 1)]) if len(v) else float("nan")


def media_janela(c, metrica, chave, ini, fim):
    v = [x for t, x in c["serie"].get((metrica, chave), []) if ini <= t <= fim and np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def metricas_coletor(r):
    c = r["coletor"]
    out = {"coletor_pasta": "", "coletor_janela": "", "coletor_cobertura": float("nan")}
    if c is None:
        return out
    ini, fim, como = janela_coletor(r)
    pts = [t for t, _ in c["serie"].get(("cpu_uso_pct", "total"), []) if ini <= t <= fim]
    esperado = (fim - ini) / 1000.0
    out.update({"coletor_pasta": c["pasta"], "coletor_janela": como,
                "coletor_cobertura": min(1.0, len(pts) / esperado) if esperado > 0 else float("nan")})
    out["cpu_total_pct"] = media_janela(c, "cpu_uso_pct", "total", ini, fim)
    for core in SILVER + GOLD:
        out[f"cpu_{core}_pct"] = media_janela(c, "cpu_uso_pct", core, ini, fim)
        out[f"freq_{core}_mhz"] = media_janela(c, "cpu_freq_mhz", core, ini, fim)
    out["cpu_silver_pct"] = float(np.nanmean([out[f"cpu_{k}_pct"] for k in SILVER]))
    out["cpu_gold_pct"] = float(np.nanmean([out[f"cpu_{k}_pct"] for k in GOLD]))
    out["freq_silver_mhz"] = float(np.nanmean([out[f"freq_{k}_mhz"] for k in SILVER]))
    out["freq_gold_mhz"] = float(np.nanmean([out[f"freq_{k}_mhz"] for k in GOLD]))
    corrente = media_janela(c, "bateria_corrente_ma", "", ini, fim)
    tensao = media_janela(c, "bateria", "voltage_mv", ini, fim)
    out["descarga_ma"] = -corrente  # current_now é negativo descarregando
    out["potencia_mw"] = -corrente * tensao / 1000.0
    bt = [x for t, x in c["serie"].get(("bateria", "temperature_c"), []) if ini <= t <= fim]
    out["temp_bateria_ini_c"] = bt[0] if bt else float("nan")
    out["temp_bateria_fim_c"] = bt[-1] if bt else float("nan")
    return out


# ---------------------------------------------------------------------------
# Tabelas

COLS_PAGINA = ["condition", "mode", "threads", "rep", "run_id", "owner", "frames_measured",
               "frame_mean_ms", "frame_p50_ms", "frame_p95_ms", "frame_p99_ms", "fps_mean",
               "tracking_full_ratio", "threads_units_per_s", "threads_min_units_per_s",
               "threads_busy_ratio", "battery_start", "battery_end", "charging_start",
               "charging_end", "page_hidden", "app_version"]


def montar_tabela(escolhidas, duracao):
    linhas = []
    for (d, cond, rep), r in sorted(escolhidas.items(), key=lambda kv: (kv[0][1], kv[0][2])):
        if d != duracao:
            continue
        linha = {k: r.get(k, "") for k in COLS_PAGINA}
        linha["mode"] = "ar" if r["mode"] == "ar" else "sem-ar"
        linha["corrigido"] = r.get("corrigido", "")
        linha["descartadas_mesma_cond"] = r["descartadas_mesma_cond"]
        linha.update(metricas_coletor(r))
        linhas.append(linha)
    return linhas


def gravar(nome, linhas):
    if not linhas:
        return
    cols = list(dict.fromkeys(k for l in linhas for k in l))
    with open(os.path.join(TAB, nome), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for l in linhas:
            w.writerow({k: (f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else v)
                        for k, v in l.items()})


def valores(linhas, modo, t, campo):
    return [num(l[campo]) for l in linhas
            if l["mode"] == modo and int(num(l["threads"])) == t and np.isfinite(num(l[campo]))]


def pares(linhas, t, campo):
    """Custo do AR por repetição: valor(ar) − valor(sem-ar) com mesmo nº de threads e repetição."""
    por = {(l["mode"], int(num(l["rep"]))): num(l[campo]) for l in linhas if int(num(l["threads"])) == t}
    reps = sorted({rep for (_, rep) in por})
    return [(rep, por[("ar", rep)] - por[("sem-ar", rep)]) for rep in reps
            if ("ar", rep) in por and ("sem-ar", rep) in por
            and np.isfinite(por[("ar", rep)]) and np.isfinite(por[("sem-ar", rep)])]


METRICAS_RESUMO = [("frame_p95_ms", "p95 do tempo de quadro (ms)"),
                   ("frame_mean_ms", "tempo de quadro médio (ms)"),
                   ("fps_mean", "fps médio"),
                   ("cpu_total_pct", "CPU total (%)"),
                   ("cpu_silver_pct", "CPU núcleos Silver 0-3 (%)"),
                   ("cpu_gold_pct", "CPU núcleos Gold 4-7 (%)"),
                   ("freq_gold_mhz", "frequência Gold (MHz)"),
                   ("threads_units_per_s", "vazão por thread do jogo (unidades/s)"),
                   ("descarga_ma", "corrente de descarga (mA)"),
                   ("potencia_mw", "potência (mW)")]


def tabela_resumo(linhas):
    out = []
    for modo in MODOS:
        for t in THREADS:
            linha = {"condicao": f"{modo}_t{t}", "modo": modo, "threads": t}
            for campo, _ in METRICAS_RESUMO:
                v = valores(linhas, modo, t, campo)
                linha[f"{campo}_n"] = len(v)
                linha[f"{campo}_media"] = float(np.mean(v)) if v else float("nan")
                linha[f"{campo}_dp"] = float(np.std(v, ddof=1)) if len(v) > 1 else float("nan")
            out.append(linha)
    return out


def tabela_custo(linhas):
    out = []
    for t in THREADS:
        linha = {"threads": t}
        for campo, _ in METRICAS_RESUMO:
            d = [x for _, x in pares(linhas, t, campo)]
            linha[f"{campo}_custo_n"] = len(d)
            linha[f"{campo}_custo_media"] = float(np.mean(d)) if d else float("nan")
            linha[f"{campo}_custo_dp"] = float(np.std(d, ddof=1)) if len(d) > 1 else float("nan")
        out.append(linha)
    return out


# ---------------------------------------------------------------------------
# Gráficos

def rodape(fig, texto):
    fig.text(0.01, -0.01, texto, fontsize=7, color="#666", ha="left", va="top", wrap=True)


def rotulos_finais(ax, itens, folga):
    """Escreve o nome de cada série ao lado do último ponto, afastando os que ficariam sobrepostos.

    itens = [(texto, x, y, cor)]; folga = distância mínima entre rótulos, nas unidades do eixo y.
    """
    itens = sorted(itens, key=lambda i: i[2])
    ys = [i[2] for i in itens]
    for k in range(1, len(ys)):
        ys[k] = max(ys[k], ys[k - 1] + folga)
    for (texto, x, _, cor), y in zip(itens, ys):
        ax.annotate(texto, (x, y), xytext=(12, 0), textcoords="offset points", va="center",
                    fontsize=12, color=cor, fontweight="bold", annotation_clip=False)


def salvar(fig, nome):
    fig.savefig(os.path.join(GRAF, nome), dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("  " + nome)


def grafico_modos(linhas, campo, titulo, ylabel, nome, nota, ylim0=False):
    """Pontos de cada repetição + média ± desvio padrão, sem AR e com AR lado a lado."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    desl = {"sem-ar": -0.25, "ar": 0.25}
    rng = np.random.default_rng(0)
    for modo in MODOS:
        xs, ms, dps = [], [], []
        for t in THREADS:
            v = valores(linhas, modo, t, campo)
            if not v:
                continue
            x = t + desl[modo]
            ax.scatter(x + rng.uniform(-0.08, 0.08, len(v)), v, s=14, color=COR[modo], alpha=0.45, zorder=2)
            xs.append(x)
            ms.append(np.mean(v))
            dps.append(np.std(v, ddof=1) if len(v) > 1 else 0)
        ax.errorbar(xs, ms, yerr=dps, fmt="o-", color=COR[modo], capsize=4, lw=1.8, ms=7,
                    label=NOME_MODO[modo], zorder=3)
    ax.set_xticks(THREADS)
    ax.set_xlabel("Threads extras ocupadas do jogo")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    if ylim0:
        ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    rodape(fig, nota)
    return fig, ax


def grafico_custo(linhas, campo, titulo, ylabel, nome, nota, cor="#C44E52"):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    rng = np.random.default_rng(1)
    for t in THREADS:
        d = [x for _, x in pares(linhas, t, campo)]
        if not d:
            continue
        m = np.mean(d)
        dp = np.std(d, ddof=1) if len(d) > 1 else 0
        ax.bar(t, m, width=1.2, color=cor, alpha=0.75, yerr=dp, capsize=5)
        ax.scatter(t + rng.uniform(-0.25, 0.25, len(d)), d, s=16, color="black", alpha=0.6, zorder=3)
        topo = max(m + dp, max(d)) if m >= 0 else min(m - dp, min(d))
        ax.annotate(f"{m:+.1f}".replace(".", ","), (t, topo), textcoords="offset points",
                    xytext=(0, 5 if m >= 0 else -14), ha="center", fontsize=9, fontweight="bold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(THREADS)
    ax.set_xlabel("Threads extras ocupadas do jogo")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.3)
    rodape(fig, nota)
    salvar(fig, nome)


def quadros_por_execucao(run_ids):
    """{run_id: np.array(frame_ms fora do aquecimento)} para as execuções pedidas."""
    out = defaultdict(list)
    for r in ler_pagina("quadros"):
        if r["run_id"] in run_ids and r["warmup"] == "0" and r["frame_ms"] != "":
            out[r["run_id"]].append(float(r["frame_ms"]))
    return {k: np.array(v) for k, v in out.items()}


def grafico_cdf(linhas, quadros):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    cores_t = {0: "#1b9e77", 2: "#7570b3", 4: "#e7298a", 6: "#d95f02"}
    for ax, modo in zip(axs, MODOS):
        for t in THREADS:
            ids = [l["run_id"] for l in linhas if l["mode"] == modo and int(num(l["threads"])) == t]
            v = np.concatenate([quadros[i] for i in ids if i in quadros]) if ids else np.array([])
            if not len(v):
                continue
            v = np.sort(v)
            ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=cores_t[t], lw=1.6, label=f"{t} threads")
        ax.axhline(0.95, color="#999", ls="--", lw=0.8)
        ax.text(ax.get_xlim()[0] if False else 20, 0.955, "p95", fontsize=8, color="#666")
        ax.axvline(1000 / 30, color="#999", ls=":", lw=0.8)
        ax.set_xlim(20, 100)
        ax.set_title(NOME_MODO[modo])
        ax.set_xlabel("Tempo de quadro (ms)")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right")
    axs[0].set_ylabel("Fração dos quadros com tempo ≤ x")
    fig.suptitle("Frente 1 — Distribuição do tempo de quadro (todas as repetições juntas)")
    rodape(fig, "Linha pontilhada: 33,3 ms (30 fps, o limite do modo sem AR). Linha tracejada: 95% dos quadros. "
                "Eixo cortado em 100 ms.")
    salvar(fig, "F1_3_distribuicao_tempo_quadro.png")


def grafico_heatmap(linhas):
    conds = [(m, t) for m in MODOS for t in THREADS]
    nucleos = SILVER + GOLD
    mat = np.array([[np.mean(valores(linhas, m, t, f"cpu_{k}_pct") or [np.nan]) for k in nucleos]
                    for m, t in conds])
    fig, ax = plt.subplots(figsize=(8.5, 5))
    im = ax.imshow(mat, cmap="viridis", vmin=0, vmax=100, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if mat[i, j] < 60 else "black")
    ax.set_xticks(range(len(nucleos)))
    ax.set_xticklabels([f"{k}\n{'Silver' if k in SILVER else 'Gold'}" for k in nucleos], fontsize=8)
    ax.set_yticks(range(len(conds)))
    ax.set_yticklabels([f"{'AR' if m == 'ar' else 'sem AR'}, {t} threads" for m, t in conds])
    ax.axvline(3.5, color="white", lw=2)
    ax.axhline(3.5, color="white", lw=2)
    fig.colorbar(im, ax=ax, label="Uso médio do núcleo (%)")
    ax.set_title("Frente 2 — Uso de CPU por núcleo (média das repetições)")
    rodape(fig, "Fonte: /proc/stat pelo coletor adb, ~1 amostra/s, só a janela de medição.")
    salvar(fig, "F2_1_cpu_por_nucleo.png")


def grafico_clusters(linhas):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    for ax, (campo, nome) in zip(axs, (("cpu_silver_pct", "Núcleos Silver (0-3, econômicos)"),
                                        ("cpu_gold_pct", "Núcleos Gold (4-7, rápidos)"))):
        for modo in MODOS:
            ms = [np.mean(valores(linhas, modo, t, campo) or [np.nan]) for t in THREADS]
            dps = [np.std(valores(linhas, modo, t, campo), ddof=1) if len(valores(linhas, modo, t, campo)) > 1
                   else 0 for t in THREADS]
            ax.errorbar(THREADS, ms, yerr=dps, fmt="o-", color=COR[modo], capsize=4, label=NOME_MODO[modo])
        ax.set_title(nome)
        ax.set_xticks(THREADS)
        ax.set_xlabel("Threads extras ocupadas do jogo")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
    axs[0].set_ylabel("Uso médio de CPU (%)")
    fig.suptitle("Frente 2 — Uso de CPU por grupo de núcleos")
    rodape(fig, "Média ± desvio padrão entre as repetições.")
    salvar(fig, "F2_2_cpu_silver_gold.png")


def grafico_freq(linhas):
    FREQ_MAX = {"freq_silver_mhz": max(num(l["freq_silver_mhz"]) for l in linhas),
                "freq_gold_mhz": max(num(l["freq_gold_mhz"]) for l in linhas)}
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, (campo, nome) in zip(axs, (("freq_silver_mhz", "Silver (0-3)"), ("freq_gold_mhz", "Gold (4-7)"))):
        for modo in MODOS:
            ms = [np.mean(valores(linhas, modo, t, campo) or [np.nan]) for t in THREADS]
            dps = [np.std(valores(linhas, modo, t, campo), ddof=1) if len(valores(linhas, modo, t, campo)) > 1
                   else 0 for t in THREADS]
            ax.errorbar(THREADS, ms, yerr=dps, fmt="o-", color=COR[modo], capsize=4, label=NOME_MODO[modo])
        ax.set_ylim(0, FREQ_MAX[campo] * 1.08)
        ax.set_title(f"Frequência média — {nome}")
        ax.set_xticks(THREADS)
        ax.set_xlabel("Threads extras ocupadas do jogo")
        ax.set_ylabel("MHz")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(loc="lower right")
    rodape(fig, "Fonte: scaling_cur_freq pelo coletor adb. Média ± desvio padrão entre as repetições. Eixo começa em 0.")
    salvar(fig, "F2_5_frequencia_cpu.png")


# ---------------------------------------------------------------------------
# Gráfico do grupo (Ficha 4)

def grafico_grupo(linhas):
    """Custo do ARCore em % de cada frente: (com AR − sem AR) / sem AR × 100, por nº de threads."""
    frentes = [("descarga_ma", "Bateria (corrente)", "#55A868"),
               ("cpu_total_pct", "CPU (uso total)", "#8172B2"),
               ("frame_p95_ms", "p95 do tempo de quadro", "#C44E52")]
    fig, ax = plt.subplots(figsize=(9, 5.8))
    tab = []
    finais = []
    for campo, nome, cor in frentes:
        medias, mins, maxs = [], [], []
        for t in THREADS:
            sem = np.mean(valores(linhas, "sem-ar", t, campo))
            com = np.mean(valores(linhas, "ar", t, campo))
            por_rep = []
            for rep in sorted({int(num(l["rep"])) for l in linhas}):
                a = [num(l[campo]) for l in linhas if l["mode"] == "ar" and int(num(l["threads"])) == t and int(num(l["rep"])) == rep]
                b = [num(l[campo]) for l in linhas if l["mode"] == "sem-ar" and int(num(l["threads"])) == t and int(num(l["rep"])) == rep]
                if a and b and np.isfinite(a[0]) and np.isfinite(b[0]):
                    por_rep.append(100 * (a[0] - b[0]) / b[0])
            m = 100 * (com - sem) / sem
            medias.append(m)
            mins.append(min(por_rep))
            maxs.append(max(por_rep))
            ax.scatter([t] * len(por_rep), por_rep, s=14, color=cor, alpha=0.35, zorder=2)
            tab.append({"frente": nome, "metrica": campo, "threads": t, "sem_ar_media": sem, "com_ar_media": com,
                        "custo_pct_das_medias": m, "custo_pct_min_rep": min(por_rep),
                        "custo_pct_max_rep": max(por_rep), "n_pares": len(por_rep),
                        "custo_pct_por_rep": " ".join(f"{x:.1f}" for x in por_rep)})
        ax.errorbar(THREADS, medias, yerr=[np.array(medias) - mins, np.array(maxs) - medias],
                    fmt="o-", color=cor, lw=2.5, ms=8, capsize=5, zorder=3)
        abaixo = campo == "frame_p95_ms"
        for t, m in zip(THREADS, medias):
            ax.annotate(f"{m:.0f}%", (t, m), xytext=(-8, -16 if abaixo else 8), textcoords="offset points",
                        ha="right", fontsize=10, color=cor, fontweight="bold")
        finais.append((nome, THREADS[-1], medias[-1], cor))
    rotulos_finais(ax, finais, 22)
    ax.axhline(0, color="black", lw=1.2)
    ax.text(0, 6, "0% = sem AR (mesma cena e mesmas threads, sem o ARCore)", fontsize=10, color="#333")
    ax.set_xticks(THREADS)
    ax.set_xlim(-0.6, 8.6)
    ax.set_ylim(bottom=-15)
    ax.set_xlabel("Threads extras ocupadas pelo jogo", fontsize=12)
    ax.set_ylabel("Custo do ARCore: aumento em relação ao sem AR (%)", fontsize=12)
    ax.tick_params(labelsize=11)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(TITULO_GRUPO, fontsize=13)
    rodape(fig, "Linha = custo calculado com as médias de 5 repetições; pontos claros = custo em cada repetição "
                "(par sem AR / com AR medido em seguida); barra = do menor ao maior valor. Galaxy Note 9.")
    salvar(fig, "GRUPO_custo_do_arcore.png")
    gravar("grupo_custo_pct.csv", tab)


# ---------------------------------------------------------------------------
# Frente 3 (execuções de 15 min)

def frente3(escolhidas):
    longas = [(cond, rep, r) for (d, cond, rep), r in escolhidas.items() if d == DURACAO_LONGA]
    if not longas:
        print("  Frente 3: ainda não há execuções de 15 min (duração 900 s) nos dados. Gráficos pulados.")
        return
    longas.sort()
    estilos = {1: "-", 2: "--"}
    cores = {"ar_t0": "#1b9e77", "ar_t6": "#d95f02"}
    quadros = {}
    for r in ler_pagina("quadros"):
        if r["run_id"] in {x[2]["run_id"] for x in longas} and r["frame_ms"] != "":
            quadros.setdefault(r["run_id"], []).append((float(r["t_ms"]), float(r["frame_ms"])))

    # p95 a cada 30 s
    fig, ax = plt.subplots(figsize=(9, 4.5))
    linhas_tab = []
    for cond, rep, r in longas:
        q = quadros.get(r["run_id"], [])
        if not q:
            continue
        t = np.array([a for a, _ in q]) / 1000.0
        f = np.array([b for _, b in q])
        bordas = np.arange(num(r["warmup_s"]), t.max() + 30, 30)
        xs, ys = [], []
        for a, b in zip(bordas[:-1], bordas[1:]):
            sel = f[(t >= a) & (t < b)]
            if len(sel):
                xs.append((a + b) / 2 / 60)
                ys.append(p95(sel))
                linhas_tab.append({"condicao": cond, "rep": rep, "minuto_meio": (a + b) / 2 / 60, "p95_ms": ys[-1]})
        ax.plot(xs, ys, estilos.get(rep, "-"), color=cores.get(cond, "gray"), label=f"{cond} rep {rep}")
    ax.set_xlabel("Minutos desde o início")
    ax.set_ylabel("p95 do tempo de quadro em janelas de 30 s (ms)")
    ax.set_title("Frente 3 — Degradação ao longo de 15 minutos")
    ax.grid(alpha=0.3)
    ax.legend()
    salvar(fig, "F3_1_p95_ao_longo_do_tempo.png")
    gravar("frente3_p95_janelas_30s.csv", linhas_tab)

    # Por minuto: temperatura e frequência (média de cada minuto)
    def por_minuto_coletor(c, metrica, filtro):
        """Média de cada minuto. Minuto k = [início do coletor + 5 s + 60(k-1), +60 s]."""
        out = []
        for k in range(1, 16):
            ini = c["inicio"] + 5000 + 60000 * (k - 1)
            v = [x for (m, kk), pts in c["serie"].items() if m == metrica and filtro(kk)
                 for tt, x in pts if ini <= tt < ini + 60000 and np.isfinite(x)]
            out.append(float(np.mean(v)) if v else float("nan"))
        return np.array(out)

    def p95_por_minuto(r):
        q = quadros.get(r["run_id"], [])
        t = np.array([a for a, _ in q]) / 1000.0
        f = np.array([b for _, b in q])
        aq = num(r["warmup_s"])
        return np.array([p95(f[(t >= max(aq, 60 * (k - 1))) & (t < 60 * k)]) for k in range(1, 16)])

    minutos = np.arange(1, 16)
    metr = {"p95": ("p95 do tempo de quadro (ms)", None),
            "freq_gold": ("Frequência média dos núcleos Gold (MHz)", ("cpu_freq_mhz", lambda k: k in GOLD)),
            "temp_gold": ("Temperatura dos núcleos Gold (°C)", ("temp_c", lambda k: "gold" in k)),
            "temp_bateria": ("Temperatura da bateria (°C)", ("bateria", lambda k: k == "temperature_c"))}
    series = defaultdict(dict)  # cond -> metrica -> [array por repetição]
    linhas_tab = []
    for cond, rep, r in longas:
        if r["coletor"] is None:
            continue
        vals = {"p95": p95_por_minuto(r)}
        for nome, (_, fonte) in metr.items():
            if fonte:
                vals[nome] = por_minuto_coletor(r["coletor"], *fonte)
        for nome, v in vals.items():
            series[cond].setdefault(nome, []).append(v)
        for i, k in enumerate(minutos):
            linhas_tab.append({"condicao": cond, "rep": rep, "minuto": int(k),
                               **{f"{n}": vals[n][i] for n in vals}})
    gravar("frente3_por_minuto.csv", linhas_tab)

    fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
    for ax, nome in zip(axs, ("temp_bateria", "temp_gold", "freq_gold")):
        for cond, rep, r in longas:
            i = [x[1] for x in longas if x[0] == cond].index(rep)
            ax.plot(minutos, series[cond][nome][i], "o" + estilos.get(rep, "-"), ms=3,
                    color=cores.get(cond, "gray"), label=f"{cond} rep {rep}")
        ax.set_title(metr[nome][0])
        ax.set_xlabel("Minuto da execução")
        ax.set_xticks([1, 5, 10, 15])
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Frente 3 — Aquecimento e frequência da CPU minuto a minuto (15 min com AR)")
    rodape(fig, "Cada ponto = média de 1 minuto (coletor adb, ~60 amostras). Minutos contados a partir de 5 s "
                "depois do início do coletor.")
    salvar(fig, "F3_2_temperatura_e_frequencia.png")

    # Gráfico principal da frente 3: p95, frequência e temperatura no mesmo eixo de tempo
    fig, axs = plt.subplots(3, 1, figsize=(9, 10), sharex=True)
    nomes_cond = {"ar_t0": "0 threads", "ar_t6": "6 threads"}
    folgas = {"p95": 4, "freq_gold": 180, "temp_bateria": 0.8}
    for ax, nome in zip(axs, ("p95", "freq_gold", "temp_bateria")):
        finais = []
        for cond in sorted(series):
            arr = np.array(series[cond][nome])
            for v in arr:
                ax.plot(minutos, v, "-", color=cores.get(cond, "gray"), alpha=0.25, lw=1)
            m = np.nanmean(arr, axis=0)
            ax.plot(minutos, m, "o-", color=cores.get(cond, "gray"), lw=2.2, ms=4)
            finais.append((nomes_cond.get(cond, cond), minutos[-1], m[-1], cores.get(cond, "gray")))
        rotulos_finais(ax, finais, folgas[nome])
        ax.set_ylabel(metr[nome][0].replace(" dos núcleos", "\ndos núcleos").replace(" do tempo", "\ndo tempo"),
                      fontsize=11)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=10)
    axs[0].axhline(1000 / 30, color="#999", ls=":", lw=1)
    axs[0].text(1, 1000 / 30 + 0.6, "33,3 ms = 30 fps", fontsize=9, color="#666")
    axs[1].axhline(2803.2, color="#999", ls=":", lw=1)
    axs[1].text(1, 2803.2 - 140, "frequência máxima dos Gold (2803 MHz)", fontsize=9, color="#666")
    axs[1].set_ylim(0, 3000)
    axs[0].set_ylim(0, 70)
    axs[2].set_xlabel("Minuto da execução (AR ligado o tempo todo)", fontsize=11)
    axs[2].set_xticks([1, 3, 5, 7, 9, 11, 13, 15])
    axs[2].set_xlim(0.5, 16.3)
    fig.suptitle(TITULO_F3, fontsize=13)
    rodape(fig, "Linha grossa = média das 2 repetições; linhas claras = cada repetição. p95 calculado em cada minuto "
                "(página); frequência e temperatura = média de cada minuto (coletor adb).")
    salvar(fig, "F3_3_frente3_principal.png")

    # 1º minuto x 15º minuto
    resumo = []
    for cond, rep, r in longas:
        q = quadros.get(r["run_id"], [])
        t = np.array([a for a, _ in q]) / 1000.0
        f = np.array([b for _, b in q])
        aq = num(r["warmup_s"])
        linha = {"condicao": cond, "rep": rep, "run_id": r["run_id"],
                 "coletor_pasta": r["coletor"]["pasta"] if r["coletor"] else "",
                 "p95_min1_ms": p95(f[(t >= aq) & (t < 60)]),
                 "p95_min15_ms": p95(f[(t >= 840) & (t < 900)]),
                 "p95_total_ms": num(r["frame_p95_ms"]),
                 "bateria_ini": num(r["battery_start"]), "bateria_fim": num(r["battery_end"])}
        linha["aumento_p95_ms"] = linha["p95_min15_ms"] - linha["p95_min1_ms"]
        c = r["coletor"]
        if c is not None:
            # Minuto k do coletor: [início + 5 s + 60(k-1), início + 5 s + 60k]. Os 5 s
            # aproximam o tempo entre iniciar o coletor e tocar em Iniciar.
            for nome_min, k in (("min1", 1), ("min15", 15)):
                ini = c["inicio"] + 5000 + 60000 * (k - 1)
                fim = ini + 60000
                def med(metrica, filtro):
                    v = [x for (m, kk), pts in c["serie"].items() if m == metrica and filtro(kk)
                         for tt, x in pts if ini <= tt <= fim and np.isfinite(x)]
                    return float(np.mean(v)) if v else float("nan")
                linha[f"temp_bateria_{nome_min}_c"] = med("bateria", lambda k_: k_ == "temperature_c")
                linha[f"temp_gold_{nome_min}_c"] = med("temp_c", lambda k_: "gold" in k_)
                linha[f"temp_silver_{nome_min}_c"] = med("temp_c", lambda k_: "silver" in k_)
                linha[f"freq_gold_{nome_min}_mhz"] = med("cpu_freq_mhz", lambda k_: k_ in GOLD)
                linha[f"freq_silver_{nome_min}_mhz"] = med("cpu_freq_mhz", lambda k_: k_ in SILVER)
                linha[f"cpu_total_{nome_min}_pct"] = med("cpu_uso_pct", lambda k_: k_ == "total")
                linha[f"descarga_{nome_min}_ma"] = -med("bateria_corrente_ma", lambda k_: k_ == "")
        resumo.append(linha)
        print(f"    {cond}_r{rep}: p95 {linha['p95_min1_ms']:.1f} -> {linha['p95_min15_ms']:.1f} ms; "
              f"bateria {linha.get('temp_bateria_min1_c', float('nan')):.1f} -> "
              f"{linha.get('temp_bateria_min15_c', float('nan')):.1f} °C; Gold "
              f"{linha.get('freq_gold_min1_mhz', float('nan')):.0f} -> {linha.get('freq_gold_min15_mhz', float('nan')):.0f} MHz")
    gravar("frente3_minuto1_x_minuto15.csv", resumo)


# ---------------------------------------------------------------------------

def main():
    os.makedirs(GRAF, exist_ok=True)
    os.makedirs(TAB, exist_ok=True)
    escolhidas, resumo, coletores = escolher_execucoes()
    linhas = montar_tabela(escolhidas, DURACAO_PRINCIPAL)
    if not linhas:
        sys.exit("Nenhuma execução principal (120 s) encontrada em dados/pagina.")

    # Avisos de qualidade
    faltando = [f"{m}_t{t}_r{rep}" for m in MODOS for t in THREADS for rep in range(1, 6)
                if not any(l["mode"] == m and int(num(l["threads"])) == t and int(num(l["rep"])) == rep for l in linhas)]
    print(f"Execuções principais escolhidas: {len(linhas)} (esperado 40)")
    if faltando:
        print("  faltando: " + ", ".join(faltando))
    for l in linhas:
        avisos = []
        if not l["coletor_pasta"]:
            avisos.append("sem coletor")
        elif l["coletor_cobertura"] < 0.9:
            avisos.append(f"coletor cobre {100 * l['coletor_cobertura']:.0f}% da janela")
        if l["charging_start"] == "1" or l["charging_end"] == "1":
            avisos.append("carregando")
        if l["mode"] == "ar" and num(l["tracking_full_ratio"]) < 0.9:
            avisos.append("rastreamento < 90%")
        if l["page_hidden"] == "1":
            avisos.append("página escondida")
        l["avisos"] = "; ".join(avisos)
        if avisos:
            print(f"  {l['condition']}_r{l['rep']}: {l['avisos']}")

    gravar("execucoes.csv", linhas)
    gravar("resumo_por_condicao.csv", tabela_resumo(linhas))
    gravar("custo_do_ar.csv", tabela_custo(linhas))
    print("Tabelas em analise/tabelas/. Gráficos:")

    n = len(linhas) // 8
    nota_reps = f"Cada ponto = 1 execução de 120 s ({n} repetições por condição). Barras = média ± desvio padrão."

    grafico_grupo(linhas)

    # Frente 1
    fig, ax = grafico_modos(linhas, "frame_p95_ms", "Frente 1 — p95 do tempo de quadro",
                            "p95 do tempo de quadro (ms)", "", nota_reps + " Sem AR limitado a 30 fps.")
    ax.axhline(1000 / 30, color="#999", ls=":", lw=0.8)
    salvar(fig, "F1_1_p95_por_threads.png")
    grafico_custo(linhas, "frame_p95_ms", "Frente 1 — Custo do ARCore no p95 = p95(AR) − p95(sem AR)",
                  "Custo no p95 do tempo de quadro (ms)", "F1_2_custo_ar_p95.png",
                  "Diferença dentro de cada repetição (pares feitos um logo após o outro). Barra = média ± dp; pontos = repetições.")
    run_ids = {l["run_id"] for l in linhas}
    grafico_cdf(linhas, quadros_por_execucao(run_ids))
    fig, _ = grafico_modos(linhas, "fps_mean", "Frente 1 — fps médio", "fps médio", "", nota_reps)
    salvar(fig, "F1_4_fps_medio.png")

    # Frente 2
    grafico_heatmap(linhas)
    grafico_clusters(linhas)
    grafico_custo(linhas, "cpu_total_pct", "Frente 2 — Custo do ARCore na CPU = CPU(AR) − CPU(sem AR)",
                  "Diferença no uso total de CPU (pontos percentuais)", "F2_3_custo_ar_cpu.png",
                  "CPU total = média dos 8 núcleos. Diferença dentro de cada repetição.", cor="#8172B2")
    linhas_t = [l for l in linhas if int(num(l["threads"])) > 0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for modo in MODOS:
        ts = [t for t in THREADS if t > 0]
        ms = [np.mean(valores(linhas_t, modo, t, "threads_units_per_s") or [np.nan]) for t in ts]
        dps = [np.std(valores(linhas_t, modo, t, "threads_units_per_s"), ddof=1) for t in ts]
        ax.errorbar(ts, ms, yerr=dps, fmt="o-", color=COR[modo], capsize=4, label=NOME_MODO[modo])
    ax.set_xticks([2, 4, 6])
    ax.set_xlabel("Threads extras ocupadas do jogo")
    ax.set_ylabel("Trabalho feito por thread (unidades/s)")
    ax.set_ylim(bottom=0)
    ax.set_title("Frente 2 — Quanto trabalho cada thread do jogo consegue fazer")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    rodape(fig, "Cada thread fica 5 ms ocupada / 5 ms parada. Menos unidades/s = a thread rodou mais devagar "
                "(núcleo mais lento ou disputado).")
    salvar(fig, "F2_4_vazao_threads_do_jogo.png")
    grafico_freq(linhas)

    # Frente 3
    frente3(escolhidas)

    # Frente 4
    fig, _ = grafico_modos(linhas, "descarga_ma", "Frente 4 — Corrente de descarga da bateria",
                           "Corrente média de descarga (mA)", "",
                           nota_reps + " Fonte: current_now pelo coletor adb.", ylim0=True)
    salvar(fig, "F4_1_corrente_bateria.png")
    grafico_custo(linhas, "descarga_ma", "Frente 4 — Custo do ARCore na bateria = corrente(AR) − corrente(sem AR)",
                  "Corrente extra (mA)", "F4_2_custo_ar_bateria.png",
                  "Diferença dentro de cada repetição. Barra = média ± dp; pontos = repetições.", cor="#55A868")
    fig, _ = grafico_modos(linhas, "potencia_mw", "Frente 4 — Potência média (corrente × tensão da bateria)",
                           "Potência média (mW)", "", nota_reps, ylim0=True)
    salvar(fig, "F4_3_potencia.png")


if __name__ == "__main__":
    main()
