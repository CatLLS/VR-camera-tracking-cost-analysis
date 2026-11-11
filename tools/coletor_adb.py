#!/usr/bin/env python3
"""Coletor de métricas do sistema do celular via adb, para rodar junto com a página.

Lê do aparelho, a cada intervalo:
  - /proc/stat              -> uso de CPU por núcleo (%)
  - scaling_cur_freq        -> frequência atual de cada núcleo (MHz)
  - thermal_zone*/temp      -> temperaturas dos sensores (°C)
  - dumpsys battery         -> nível, temperatura, tensão, contador de carga, se está carregando
  - power_supply/battery    -> corrente instantânea (current_now), quando o aparelho permite

Grava em dados/adb/<rotulo>_<data-hora>/:
  bruto.txt   saída crua de cada amostra (o que o aparelho devolveu)
  amostras.csv  formato longo: epoch_ms, metrica, chave, valor
  meta.txt    rótulo, aparelho, relógios do PC e do celular no início

Uso:
  python tools/coletor_adb.py --rotulo 1080p_r1 --duracao 130
  python tools/coletor_adb.py --rotulo 15min_off --duracao 930 --intervalo 2

Só usa a biblioteca padrão. Precisa do adb no PATH (Android platform-tools).
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from datetime import datetime

SEP = "@@@"

# Um único "adb shell" por amostra, para o próprio coletor pesar pouco no aparelho.
SAMPLE_CMD = (
    "cat /proc/stat | grep '^cpu';"
    f"echo {SEP}freq;"
    "for f in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq; do echo $f $(cat $f 2>/dev/null); done;"
    f"echo {SEP}thermal;"
    "for z in /sys/class/thermal/thermal_zone*; do echo $(cat $z/type 2>/dev/null) $(cat $z/temp 2>/dev/null); done;"
    f"echo {SEP}current;"
    "cat /sys/class/power_supply/battery/current_now 2>/dev/null;"
    f"echo {SEP}battery;"
    "dumpsys battery"
)


def adb(args, serial=None, timeout=15):
    cmd = ["adb"] + (["-s", serial] if serial else []) + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def split_sections(text):
    sections = {"stat": []}
    current = "stat"
    for line in text.splitlines():
        line = line.rstrip("\r")
        if line.startswith(SEP):
            current = line[len(SEP):].strip()
            sections[current] = []
        else:
            sections[current].append(line)
    return sections


def parse_stat(lines):
    """Retorna {nome: (ocioso, total)} para 'cpu' e cada 'cpuN'."""
    out = {}
    for line in lines:
        parts = line.split()
        if not parts or not parts[0].startswith("cpu"):
            continue
        vals = [int(x) for x in parts[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)  # idle + iowait
        out[parts[0]] = (idle, sum(vals[:8]))  # ignora guest/guest_nice (já contados em user)
    return out


def parse_freq(lines):
    out = {}
    for line in lines:
        m = re.search(r"/(cpu\d+)/cpufreq/scaling_cur_freq\s+(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2)) / 1000.0  # kHz -> MHz
    return out


def parse_thermal(lines):
    out = {}
    counts = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        name, raw = " ".join(parts[:-1]), parts[-1]
        try:
            val = int(raw)
        except ValueError:
            continue
        # Os sensores reportam em m°C (a maioria) ou em °C.
        temp = val / 1000.0 if abs(val) > 200 else float(val)
        counts[name] = counts.get(name, 0) + 1
        key = name if counts[name] == 1 else f"{name}#{counts[name]}"
        out[key] = temp
    return out


def parse_battery(lines):
    out = {}
    for line in lines:
        m = re.match(r"\s*([A-Za-z ]+):\s*(\S+)", line)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2)
        if k in ("AC powered", "USB powered", "Wireless powered"):
            out[k.replace(" ", "_").lower()] = 1 if v == "true" else 0
        elif k in ("level", "scale", "voltage", "temperature", "status", "Charge counter"):
            try:
                n = int(v)
            except ValueError:
                continue
            if k == "temperature":
                out["temperature_c"] = n / 10.0
            elif k == "voltage":
                out["voltage_mv"] = n
            elif k == "Charge counter":
                out["charge_counter_uah"] = n
            else:
                out[k] = n
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rotulo", required=True, help="nome da execução, ex.: 1080p_r1 (vira o nome da pasta)")
    ap.add_argument("--duracao", type=float, required=True, help="segundos de coleta")
    ap.add_argument("--intervalo", type=float, default=1.0, help="segundos entre amostras (padrão 1)")
    ap.add_argument("--serial", default=None, help="serial do aparelho, se houver mais de um conectado")
    ap.add_argument("--saida", default=os.path.join("dados", "adb"), help="pasta base de saída")
    args = ap.parse_args()

    try:
        devs = adb(["devices"]).stdout
    except FileNotFoundError:
        sys.exit("adb não encontrado. Instale o Android platform-tools e coloque-o no PATH.")
    if "\tdevice" not in devs:
        sys.exit("Nenhum aparelho autorizado no adb. Saída de 'adb devices':\n" + devs)

    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    outdir = os.path.join(args.saida, f"{args.rotulo}_{stamp}")
    os.makedirs(outdir, exist_ok=True)

    model = adb(["shell", "getprop", "ro.product.model"], args.serial).stdout.strip()
    android = adb(["shell", "getprop", "ro.build.version.release"], args.serial).stdout.strip()
    pc_before = time.time()
    phone_epoch = adb(["shell", "date", "+%s"], args.serial).stdout.strip()
    pc_after = time.time()
    with open(os.path.join(outdir, "meta.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"rotulo={args.rotulo}\n")
        fh.write(f"aparelho={model}\nandroid={android}\n")
        fh.write(f"intervalo_s={args.intervalo}\nduracao_s={args.duracao}\n")
        fh.write(f"pc_epoch_s={(pc_before + pc_after) / 2:.3f}\ncelular_epoch_s={phone_epoch}\n")
        fh.write("obs=epoch_ms das amostras usa o relógio do PC; compare pc_epoch_s e celular_epoch_s para o desvio\n")

    raw_fh = open(os.path.join(outdir, "bruto.txt"), "w", encoding="utf-8")
    csv_fh = open(os.path.join(outdir, "amostras.csv"), "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_fh)
    writer.writerow(["epoch_ms", "metrica", "chave", "valor"])

    print(f"Coletando '{args.rotulo}' de {model} (Android {android}) por {args.duracao:.0f} s em {outdir}")
    print("Ctrl+C encerra antes do tempo (o que já foi coletado fica salvo).")

    prev_stat = None
    start = time.time()
    next_t = start
    samples = 0
    try:
        while time.time() - start < args.duracao:
            t0 = time.time()
            res = adb(["shell", SAMPLE_CMD], args.serial)
            t_ms = int(round((t0 + time.time()) / 2 * 1000))
            raw_fh.write(f"### {t_ms}\n{res.stdout}\n")
            sec = split_sections(res.stdout)
            rows = []

            stat = parse_stat(sec.get("stat", []))
            if prev_stat is not None:
                for name, (idle, total) in stat.items():
                    if name not in prev_stat:
                        continue  # núcleo que acabou de ligar: sem base para a diferença
                    d_total = total - prev_stat[name][1]
                    d_idle = idle - prev_stat[name][0]
                    if d_total > 0:
                        key = "total" if name == "cpu" else name
                        rows.append(("cpu_uso_pct", key, round(100.0 * (d_total - d_idle) / d_total, 2)))
            online = [n for n in stat if n != "cpu"]
            rows.append(("cpu_nucleos_online", "", len(online)))
            prev_stat = stat

            for core, mhz in parse_freq(sec.get("freq", [])).items():
                rows.append(("cpu_freq_mhz", core, mhz))
            for zone, temp in parse_thermal(sec.get("thermal", [])).items():
                rows.append(("temp_c", zone, temp))
            cur = [l.strip() for l in sec.get("current", []) if l.strip()]
            if cur:
                try:
                    rows.append(("bateria_corrente_ua", "", int(cur[0])))
                except ValueError:
                    pass
            for k, v in parse_battery(sec.get("battery", [])).items():
                rows.append(("bateria", k, v))

            for metric, key, val in rows:
                writer.writerow([t_ms, metric, key, val])
            samples += 1
            if samples % 10 == 0:
                csv_fh.flush()
                raw_fh.flush()
                print(f"  {time.time() - start:5.0f} s, {samples} amostras")

            next_t += args.intervalo
            delay = next_t - time.time()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.time()  # amostra demorou mais que o intervalo: não acumula atraso
    except KeyboardInterrupt:
        print("Interrompido.")
    finally:
        raw_fh.close()
        csv_fh.close()

    print(f"Pronto: {samples} amostras em {outdir}")


if __name__ == "__main__":
    main()
