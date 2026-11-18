# Test Guide — measuring alone with the Galaxy Note 9

Follow this from top to bottom. Every step is in the order you do it. Don't skip ahead.
The page and the tools are in Portuguese; the button and field names are quoted exactly as they appear.

## What the whole thing looks like

| When | What | Time (estimate) |
|---|---|---|
| **Day 0** | One-time setup + a rehearsal run | ~1.5 h |
| **Day 1** | Rounds 1–2 (runs 1–16) | ~3 h |
| **Day 2** | Rounds 3–4 (runs 17–32) | ~3 h |
| **Day 3** | Round 5 (runs 33–40) + front 3's four 15-minute runs | ~4.5 h |

Times are guesses: most of each run is waiting for the phone to cool down, and how long that takes depends on the phone and the room. After the first few runs on Day 1 you'll know your real pace.

**Deadline:** the presentation is on **25/11**. Aim to finish measuring by **22/11**, so there are two days left for graphs and the report. If you get behind, you can split a day into two sessions, but **never split a pair** (the `sem-ar` and `ar` runs with the same thread count, which come one after the other).

**The one rule that matters most:** every number in the project must come from your phone. Never type, round or "fix" a measurement by hand. If a run went wrong, run it again.

## What you need

- The Note 9 and its charger + USB cable.
- The PC with this repository folder (`C:\Games(shared)\TrabalhoSO-N2-2026`), where Python is already installed.
- Masking tape (for two marks on the floor) and something to measure 3 m.
- PC speakers (for the metronome — **not** the phone).
- The same room for all days, with the same lights on.

---

# Day 0 — one-time setup (~1.5 h)

### 0.1 Point GitHub Pages at the AR version (5 min)

1. On github.com open the repository `VR-camera-tracking-cost-analysis` → **Settings** → **Pages**.
2. Under *Build and deployment*, set **Branch** to `arcore` and folder to `/docs`. Click **Save**.
3. Wait about 2 minutes. The page address stays the same: `https://catlls.github.io/VR-camera-tracking-cost-analysis/`.

### 0.2 Open PowerShell with the project's adb (5 min)

adb is already inside the project, in `tools\platform-tools\` (Google's official Platform-Tools 37.0.1, signature checked). Nothing gets installed on the PC, and the folder isn't uploaded to GitHub.

1. Open a PowerShell window in the repository folder: in File Explorer, open `C:\Games(shared)\TrabalhoSO-N2-2026`, click the address bar, type `powershell`, Enter.
2. Type this line. It lets this window (and only this window) use `adb` by name:
   ```
   $env:Path = "$PWD\tools\platform-tools;$env:Path"
   ```
3. Type `adb version`. It should print `Android Debug Bridge version 1.0.41` and a path ending in `tools\platform-tools\adb.exe`.

**Keep this PowerShell window open for all measuring days.** Every command in this guide is typed there. If you close it, open a new one and repeat step 2. The Python tools find the project's adb by themselves; the line is only for the `adb …` commands you type directly.

### 0.3 Update the phone's apps, then freeze them (15 min)

The Chrome and ARCore versions must not change between measuring days.

1. Play Store → search **Chrome** → **Atualizar** if available.
2. Play Store → search **Google Play Services for AR** → install or **Atualizar**.
3. Play Store → your profile picture → **Configurações** → **Preferências de rede** → **Atualizar apps automaticamente** → **Não atualizar apps automaticamente**.

### 0.4 Phone settings (10 min) — leave these the same on every day

1. **Developer options:** Configurações → Sobre o telefone → Informações do software → tap **Número de compilação** 7 times (enter your PIN if asked). Then Configurações → Opções do desenvolvedor → turn on **Depuração USB**.
2. **Screen:** Configurações → Visor → **Resolução da tela** → **FHD+** → Aplicar. Turn **off** *Brilho adaptável* and set the brightness slider to about the middle. Remember where it is; keep it there.
3. **Power:** Configurações → Assistência do aparelho → Bateria → **Modo de energia** → **Otimizado**. Make sure no power-saving mode is on.
4. **Screen timeout:** Configurações → Visor → Tempo limite da tela → **10 minutos**.
5. **Do not disturb:** pull down the quick panel → turn on **Não perturbe**.
6. **No case** on the phone.

### 0.5 Write down the device info for the form (5 min)

Fill in the `[PREENCHER]` of the device in `notes/projectForm.md`:
- Configurações → Sobre o telefone: **Número do modelo** (SM-N960…), and in *Informações do software*: **Versão do Android** and **Versão da One UI**.
- Configurações → Assistência do aparelho → Memória: total RAM.
- In Chrome, open `chrome://version` → the first line is the Chrome version.
- Play Store → *Google Play Services for AR* → scroll down to *Sobre este app* → version.

### 0.6 Connect adb over Wi-Fi (10 min)

The cable charges the phone, which would ruin the battery numbers, so measurements use adb over Wi-Fi. The phone and the PC must be on the **same Wi-Fi network**.

1. Plug the phone into the PC with the cable. On the phone, a box asks *Permitir depuração USB?* → tick **Sempre permitir neste computador** → **Permitir**.
2. In PowerShell: `adb devices` → you should see one line ending in `device`.
3. `adb tcpip 5555`
4. On the phone: Configurações → Conexões → Wi-Fi → tap the gear next to your network → note the **Endereço IP** (e.g. `192.168.0.23`).
5. `adb connect 192.168.0.23:5555` (with your IP).
6. **Unplug the cable.** Run `adb devices` again: the line should now show `192.168.0.23:5555  device`.

> After a phone **reboot**, Wi-Fi adb is gone: plug the cable in and redo steps 3–6.

### 0.7 Test the collector (3 min)

1. `python tools/coletor_adb.py --rotulo teste --duracao 10`
2. It should print `Coletando 'teste' de SM-N960… por 10 s` and finish with `Pronto: … amostras`.
3. Open the new folder `dados\adb\teste_…\amostras.csv` (Notepad is fine). Check that there are lines starting with a number and then `cpu_uso_pct`, `cpu_freq_mhz`, `temp_c`, `bateria_corrente_ua` and `bateria`.
4. **Send me** (Claude) the lines with `bateria_corrente_ua`. From the size of the number I'll tell you whether Samsung reports mA or µA, which the form needs.
5. Delete the `teste_…` folder.

### 0.8 Feature test on the page (5 min)

1. On the phone, open Chrome with **only one tab** (close the others: tab counter → ⋮ → *Fechar todas as guias*). Open the page address.
2. Check the top of the page says **(versão 2.1.0-ar-threads)**. If it shows an older version or a different page, wait 2 minutes and pull down to reload.
3. Fill **Integrante** with your name. Write it exactly the same way every time.
4. Tap **Testar recursos do AR**. Chrome asks to allow the camera / AR → **Permitir**. Move the phone slowly around the room for the 8 seconds.
5. A table *Recursos do AR neste aparelho* appears. **Take a screenshot and send it to me.** It also fills **Limite de quadros sem AR (fps)** (inside *Carga fixa*) automatically. Open *Carga fixa* and check that the field now has a number (probably 30).

### 0.9 Prepare the room (10 min)

1. Put two tape marks on the floor **3 m apart** (call them A and B). Use a spot where nobody will walk through, with a wall or furniture ahead (ARCore needs things to look at; a blank white wall is bad).
2. On the PC, open a metronome at **60 bpm** (search *metronome* on Google; it has one built in) and test the sound. Keep the PC speakers on during runs.

**How to walk (every run, including "sem AR"):**
- Hold the phone with both hands at chest height, in portrait, screen facing you, rear camera facing forward. Hold it by the edges, without covering the camera (top of the back).
- Start on mark A, facing B. **One step per beat.** At mark B, turn around in place over 2 beats, then walk back to A. Repeat until the page returns to the panel.
- Same speed, same way of holding, every run.

### 0.10 Rehearsal (10 min) — not counted

This is to practice the routine once. Its data will be deleted.

1. Pull down on the page to reload it.
2. Set: **Modo** = *AR (ARCore)*, **Threads extras do jogo** = 6, **Repetição nº** = 1, **Duração (s)** = 30.
3. In PowerShell: `python tools/coletor_adb.py --rotulo ensaio --duracao 50`
4. Right away, tap **Iniciar execução** on the phone and walk the path until the page comes back (~30 s).
5. Read the gray/red text under the buttons. Then delete the rehearsal: scroll down, tap **Apagar tudo** twice (the second tap confirms). Delete the `dados\adb\ensaio_…` folder.
6. **Set Duração (s) back to 120.**

Day 0 is done. Charge the phone to ~90% for Day 1.

---

# Day 1 — Rounds 1 and 2

### Start of every measuring day (~25 min)

Do this at the start of Day 1, Day 2 and Day 3.

1. Charge the phone to about 90%, then **unplug it**.
2. On the phone: turn on **Modo avião**, then turn **Wi-Fi** back on (same network as the PC). Check *Não perturbe* is on. Close all other apps (recent apps button → *Fechar todos*). Chrome must have only the measurement page open.
3. Check the settings from 0.4 are unchanged (brightness, FHD+, power mode).
4. Reconnect adb: in PowerShell (if it's a new window, first run the `$env:Path = …` line from step 0.2), `adb connect <IP>:5555` then `adb devices` (must say `device`). If it fails, see the troubleshooting table at the end.
5. Turn the phone's screen off and leave it still on the table for **15 minutes**.
6. Then: `python tools/esfriar.py --repouso`. It records today's resting temperature (e.g. `Repouso de hoje: 29.8 °C`) and prints the target for starting each run (resting + 1 °C).
7. Set up the room: lights on as usual, metronome open.

### The run routine (repeat for every run in the list)

Each run takes about 2½ minutes plus the cool-down.

1. **Cool down.** `python tools/esfriar.py` and wait for `PRONTO`. (Before the very first run of the day you can skip this, since the phone is at rest.) Keep the screen off while waiting.
   - If it warns that the battery is **below 50%**: plug the charger in, charge to ~90%, unplug, and run `python tools/esfriar.py` again. Charging heats the battery, so this wait is longer.
2. **Reload the page.** Unlock the phone, pull down on the page. **Always.** Without reloading, the Note 9 fails on the second run with `Cannot read properties of null (reading 'precision')`.
3. **Set the fields** to the values in the run list:
   - **Modo**: *Sem AR (só a cena)* or *AR (ARCore)*
   - **Threads extras do jogo**: 0, 2, 4 or 6
   - **Repetição nº**: the round number
   - Check **Integrante** (your name), **Duração (s)** = 120, **Aquecimento descartado (s)** = 5.
   - Check that **Condição** shows exactly the condition in the list (e.g. `ar_t4`).
   - Don't touch *Carga fixa* (3000 objects, *Cena presa à câmera* ticked, the fps limit from the feature test).
4. **Start the collector:** `python tools/coletor_adb.py --rotulo <label> --duracao 140`, with the label from the list (e.g. `ar_t4_r1`). In PowerShell, the ↑ key brings back the previous command so you only edit the label.
5. **Within 10 seconds,** tap **Iniciar execução**, go to mark A and start walking with the metronome.
   - In AR mode the camera image appears with colored balls in front. If Chrome shows a prompt about entering AR, accept it.
   - In *sem AR* mode you see only the balls on a dark background. **Walk anyway**, exactly the same way.
   - Don't touch the screen while walking. Don't press the back button (it ends the AR session and the run is marked *interrompida*).
6. **When the page returns to the panel** (after ~2 min), stop walking. The collector finishes about 20 s later with `Pronto`.
7. **Read the message** under the buttons:
   - `Execução salva.` → good. Tick the run in the list.
   - `Salva, com avisos: …` → the run is saved but must be **repeated** (see below). Write the warning in the *Notes* column.
8. Turn the screen off and go back to step 1 for the next run.

**Repeating a run with a warning:** don't repeat it straight away. Finish the current round, then run it again at the end of that round with the **same** condition, repetition number and collector label. For a pair, repeat both runs of the pair (the `sem-ar` and the `ar` with that thread count), one after the other. The failed run stays in the data with its warning; that's fine, the analysis leaves it out.

### Run list — Day 1

| # | Condição (page) | Modo | Threads | Repetição | Collector label | Done | Notes |
|---|---|---|---|---|---|---|---|
| 1 | sem-ar_t0 | Sem AR | 0 | 1 | `sem-ar_t0_r1` | ☐ | |
| 2 | ar_t0 | AR | 0 | 1 | `ar_t0_r1` | ☐ | |
| 3 | sem-ar_t2 | Sem AR | 2 | 1 | `sem-ar_t2_r1` | ☐ | |
| 4 | ar_t2 | AR | 2 | 1 | `ar_t2_r1` | ☐ | |
| 5 | sem-ar_t6 | Sem AR | 6 | 1 | `sem-ar_t6_r1` | ☐ | |
| 6 | ar_t6 | AR | 6 | 1 | `ar_t6_r1` | ☐ | |
| 7 | sem-ar_t4 | Sem AR | 4 | 1 | `sem-ar_t4_r1` | ☐ | |
| 8 | ar_t4 | AR | 4 | 1 | `ar_t4_r1` | ☐ | |
| 9 | ar_t2 | AR | 2 | 2 | `ar_t2_r2` | ☐ | |
| 10 | sem-ar_t2 | Sem AR | 2 | 2 | `sem-ar_t2_r2` | ☐ | |
| 11 | ar_t4 | AR | 4 | 2 | `ar_t4_r2` | ☐ | |
| 12 | sem-ar_t4 | Sem AR | 4 | 2 | `sem-ar_t4_r2` | ☐ | |
| 13 | ar_t0 | AR | 0 | 2 | `ar_t0_r2` | ☐ | |
| 14 | sem-ar_t0 | Sem AR | 0 | 2 | `sem-ar_t0_r2` | ☐ | |
| 15 | ar_t6 | AR | 6 | 2 | `ar_t6_r2` | ☐ | |
| 16 | sem-ar_t6 | Sem AR | 6 | 2 | `sem-ar_t6_r2` | ☐ | |

The order looks shuffled on purpose: across the 5 rounds each thread count appears in every position, so the heat left over from the previous run doesn't favor any condition.

### End of every measuring day (~10 min)

1. On the phone, scroll down and tap **Baixar todas (CSV)**. Chrome saves three files (`resumo_…`, `quadros_…`, `threads_…`). If it asks about downloading several files, tap **Permitir**.
2. In PowerShell: `python tools/puxar_csv.py`. It copies the files to `dados\pagina\` and lists them.
3. Check that `dados\adb\` has one folder per run you did today.
4. **Never** tap *Apagar tudo* from now on. The phone keeps all runs; each day's download includes the previous days too, which is fine.
5. Tell me you've finished the day and how many runs had warnings. Charge the phone for the next day.

---

# Day 2 — Rounds 3 and 4

Start with **Start of every measuring day**, then the run routine for each line.

| # | Condição (page) | Modo | Threads | Repetição | Collector label | Done | Notes |
|---|---|---|---|---|---|---|---|
| 17 | sem-ar_t4 | Sem AR | 4 | 3 | `sem-ar_t4_r3` | ☐ | |
| 18 | ar_t4 | AR | 4 | 3 | `ar_t4_r3` | ☐ | |
| 19 | sem-ar_t6 | Sem AR | 6 | 3 | `sem-ar_t6_r3` | ☐ | |
| 20 | ar_t6 | AR | 6 | 3 | `ar_t6_r3` | ☐ | |
| 21 | sem-ar_t2 | Sem AR | 2 | 3 | `sem-ar_t2_r3` | ☐ | |
| 22 | ar_t2 | AR | 2 | 3 | `ar_t2_r3` | ☐ | |
| 23 | sem-ar_t0 | Sem AR | 0 | 3 | `sem-ar_t0_r3` | ☐ | |
| 24 | ar_t0 | AR | 0 | 3 | `ar_t0_r3` | ☐ | |
| 25 | ar_t6 | AR | 6 | 4 | `ar_t6_r4` | ☐ | |
| 26 | sem-ar_t6 | Sem AR | 6 | 4 | `sem-ar_t6_r4` | ☐ | |
| 27 | ar_t0 | AR | 0 | 4 | `ar_t0_r4` | ☐ | |
| 28 | sem-ar_t0 | Sem AR | 0 | 4 | `sem-ar_t0_r4` | ☐ | |
| 29 | ar_t4 | AR | 4 | 4 | `ar_t4_r4` | ☐ | |
| 30 | sem-ar_t4 | Sem AR | 4 | 4 | `sem-ar_t4_r4` | ☐ | |
| 31 | ar_t2 | AR | 2 | 4 | `ar_t2_r4` | ☐ | |
| 32 | sem-ar_t2 | Sem AR | 2 | 4 | `sem-ar_t2_r4` | ☐ | |

End with **End of every measuring day**.

After Day 2 you have repetitions 1–3 of `sem-ar_t0` and `ar_t0`. That's the *Primeira medição* table in the form. You can fill it from `resumo_….csv` (columns `condition`, `rep`, `frame_p95_ms`) and the collector folders, or send me the files and I'll help.

---

# Day 3 — Round 5 and front 3

Start with **Start of every measuring day**, then the run routine for runs 33–40.

| # | Condição (page) | Modo | Threads | Repetição | Collector label | Done | Notes |
|---|---|---|---|---|---|---|---|
| 33 | sem-ar_t0 | Sem AR | 0 | 5 | `sem-ar_t0_r5` | ☐ | |
| 34 | ar_t0 | AR | 0 | 5 | `ar_t0_r5` | ☐ | |
| 35 | sem-ar_t2 | Sem AR | 2 | 5 | `sem-ar_t2_r5` | ☐ | |
| 36 | ar_t2 | AR | 2 | 5 | `ar_t2_r5` | ☐ | |
| 37 | sem-ar_t6 | Sem AR | 6 | 5 | `sem-ar_t6_r5` | ☐ | |
| 38 | ar_t6 | AR | 6 | 5 | `ar_t6_r5` | ☐ | |
| 39 | sem-ar_t4 | Sem AR | 4 | 5 | `sem-ar_t4_r5` | ☐ | |
| 40 | ar_t4 | AR | 4 | 5 | `ar_t4_r5` | ☐ | |

### Front 3 — the four 15-minute runs (~40 min each)

These are the same routine with three differences:
- **Duração (s)** = **900** (15 minutes).
- Collector: `--duracao 920` and the label from the table below.
- Before each one, the phone must be fully back to resting temperature (`esfriar.py` says `PRONTO`) and the battery **at least 80%**. A 15-minute run with AR uses a lot of battery, and it must not drop under 50% during the run.

You walk the path for the full 15 minutes. Take a short break before each one.

| # | Condição (page) | Modo | Threads | Repetição | Duração | Collector command | Done | Notes |
|---|---|---|---|---|---|---|---|---|
| 41 | ar_t0 | AR | 0 | 1 | 900 | `python tools/coletor_adb.py --rotulo 15min_ar_t0_r1 --duracao 920` | ☐ | |
| 42 | ar_t6 | AR | 6 | 1 | 900 | `python tools/coletor_adb.py --rotulo 15min_ar_t6_r1 --duracao 920` | ☐ | |
| 43 | ar_t6 | AR | 6 | 2 | 900 | `python tools/coletor_adb.py --rotulo 15min_ar_t6_r2 --duracao 920` | ☐ | |
| 44 | ar_t0 | AR | 0 | 2 | 900 | `python tools/coletor_adb.py --rotulo 15min_ar_t0_r2 --duracao 920` | ☐ | |

(The order 0, 6, 6, 0 keeps the time of day from favoring one of the two.)

After run 44: set **Duração (s)** back to 120, then do **End of every measuring day**. That's all the data. Send me the `dados` folder (or push it to the repo) and we'll make the graphs.

---

# When something goes wrong

| What you see | What to do |
|---|---|
| `Falhou: Cannot read properties of null (reading 'precision')` | You didn't reload the page. Reload and redo the run. |
| `Sem o limite de quadros, "sem AR" não é comparável…` | Tap **Testar recursos do AR** once (it refills the limit), reload, continue. |
| `Salva, com avisos: rastreamento completo em só …%` | ARCore lost its position. Check the lights, the camera isn't covered, and you're not facing a blank wall. Repeat the run at the end of the round. |
| `Salva, com avisos: o aparelho estava carregando` | The cable/charger was connected. Unplug it, wait for `esfriar.py`, repeat at the end of the round. |
| `Salva, com avisos: execução interrompida antes do fim` | The AR session was closed (back button, a call, the screen locked). Repeat at the end of the round. |
| `Salva, com avisos: as threads extras não mandaram nenhum relatório` | Stop and send me a screenshot. |
| `adb` *não é reconhecido como nome de cmdlet…* | This PowerShell window doesn't know the project's adb yet: run the `$env:Path = …` line from step 0.2. |
| With the cable plugged in, `adb devices` shows nothing (or *unauthorized*) | Unlock the phone and look for the *Permitir depuração USB?* box. Try another USB port/cable, and set the USB mode in the phone's notification to *Transferir arquivos*. If it still shows nothing, Windows is missing the Samsung USB driver. That **is** a system-wide install (it needs admin rights), so ask me before doing it. |
| AR doesn't start / error mentioning *not supported* | Open Play Store and check *Google Play Services for AR* is installed. Run **Testar recursos do AR** again. |
| The collector says `Nenhum aparelho autorizado no adb` | `adb connect <IP>:5555`. If that fails, the phone probably rebooted or changed IP: cable in, `adb tcpip 5555`, check the IP again, `adb connect`, cable out. Redo the run (the page data alone isn't enough; fronts 2 and 4 need the collector). |
| You forgot to start the collector, or started it with the wrong label | Repeat the run at the end of the round. If only the label was wrong, tell me which folder it is; don't rename it. |
| The phone shows a temperature warning, or feels very hot | Stop. Let it cool well beyond `PRONTO` (at least 20 min, screen off). Tell me in the notes. |
| The page shows an older version number | Wait a few minutes, then reload. Check the GitHub Pages branch is `arcore` (step 0.1). |
| Chrome or ARCore updated by itself | Write down the date and the new version and tell me. Don't uninstall anything. |
| Anything else | Write down what happened, take a screenshot, and ask me before continuing. |

# Cleaning up after the project

Only after the data is safely in `dados\` and the report is done.

1. In PowerShell: `adb kill-server` (adb leaves a background process running; while it runs, Windows won't let you delete its folder).
2. Delete `tools\platform-tools\`.
3. Delete `C:\Users\<this Windows user>\.android\` — the folder adb creates in the user profile with its authorization key.
4. On the phone: Opções do desenvolvedor → **Revogar autorizações de depuração USB**, turn off **Depuração USB**, then turn off *Opções do desenvolvedor* at the top of that screen. Turn Play Store auto-updates back on if you want them.

# Rules that never change

1. Reload the page before **every** run.
2. Collector first, then **Iniciar execução** within 10 seconds.
3. Walk the same path at the same pace in **every** run, AR or not.
4. No cable during runs; battery at 50% or more; wait for `PRONTO` between runs.
5. Never change *Carga fixa*, the room, the brightness or the phone settings between runs or days.
6. Never type or edit a measurement by hand. A bad run is repeated, never fixed.
7. Never tap *Apagar tudo* after Day 0.
