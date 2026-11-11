// Custo do rastreador — mede o tempo de quadro de uma cena 3D com e sem
// rastreador de pose (MediaPipe) rodando na câmera do mesmo aparelho.
//
// Cada execução grava, por quadro: intervalo desde o quadro anterior (frame_ms),
// tempo gasto no callback (work_ms) e, quando o rastreador rodou, quanto ele levou
// (inference_ms). Nada é estimado: todo número sai do próprio aparelho.

import * as THREE from 'three';

const APP_VERSION = '1.0.0';
const MP_VERSION = '0.10.14';
const MP_WASM = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}/wasm`;
const MODEL_URL = (v) =>
  `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_${v}/float16/1/pose_landmarker_${v}.task`;

const CONDITIONS = {
  off: null,
  '480p': { width: 640, height: 480 },
  '1080p': { width: 1920, height: 1080 },
};

const MAX_FPS_BUFFER = 250; // quadros por segundo reservados (cobre telas de 240 Hz)

const $ = (id) => document.getElementById(id);
const ui = {
  owner: $('owner'), condition: $('condition'), rep: $('rep'),
  duration: $('duration'), warmup: $('warmup'), objects: $('objects'),
  stereo: $('stereo'), pixelRatio: $('pixelRatio'), model: $('model'),
  delegate: $('delegate'), facing: $('facing'), camFps: $('camFps'),
  start: $('btn-start'), abort: $('btn-abort'), status: $('status'),
  hud: $('hud'), hudText: $('hud-text'), canvas: $('scene'), video: $('cam'),
  last: $('last'), lastTable: $('last-table'), dlLast: $('btn-dl-last'),
  runsTable: $('runs-table'), dlAll: $('btn-dl-all'), clear: $('btn-clear'),
};

// ---------------------------------------------------------------------------
// Preferências locais (só conveniência: lembra os campos entre aberturas)

const PREF_FIELDS = ['owner', 'condition', 'rep', 'duration', 'warmup', 'objects',
  'stereo', 'pixelRatio', 'model', 'delegate', 'facing', 'camFps'];

function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem('prefs') || '{}');
    for (const k of PREF_FIELDS) {
      if (!(k in p)) continue;
      if (ui[k].type === 'checkbox') ui[k].checked = p[k];
      else ui[k].value = p[k];
    }
  } catch { /* sem armazenamento: segue com os padrões */ }
}

function savePrefs() {
  try {
    const p = {};
    for (const k of PREF_FIELDS) p[k] = ui[k].type === 'checkbox' ? ui[k].checked : ui[k].value;
    localStorage.setItem('prefs', JSON.stringify(p));
  } catch { /* ignora */ }
}

// ---------------------------------------------------------------------------
// Armazenamento das execuções (IndexedDB, com fallback em memória)

const store = {
  db: null,
  mem: new Map(),
  async open() {
    try {
      this.db = await new Promise((resolve, reject) => {
        const req = indexedDB.open('custo-rastreador', 1);
        req.onupgradeneeded = () => req.result.createObjectStore('runs', { keyPath: 'id' });
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    } catch {
      this.db = null;
      setStatus('Aviso: o navegador não permitiu salvar dados. Baixe o CSV ao fim de cada execução.', true);
    }
  },
  _req(mode, fn) {
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('runs', mode);
      const r = fn(tx.objectStore('runs'));
      tx.oncomplete = () => resolve(r && r.result);
      tx.onerror = () => reject(tx.error);
    });
  },
  async put(run) {
    this.mem.set(run.id, run);
    if (this.db) await this._req('readwrite', (s) => s.put(run));
  },
  async all() {
    if (!this.db) return [...this.mem.values()];
    const runs = await this._req('readonly', (s) => s.getAll());
    return runs || [];
  },
  async clear() {
    this.mem.clear();
    if (this.db) await this._req('readwrite', (s) => s.clear());
  },
};

// ---------------------------------------------------------------------------
// Cena 3D: carga sintética fixa e determinística (mesma em todas as condições)

function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildScene(canvas, cfg) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(cfg.pixelRatio);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x101418);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4);
  sun.position.set(5, 10, 7);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(70, 1, 0.1, 200);
  const stereoCam = new THREE.StereoCamera();

  const n = cfg.objects;
  const geo = new THREE.IcosahedronGeometry(0.35, 2);
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.2 });
  const mesh = new THREE.InstancedMesh(geo, mat, n);
  const rand = mulberry32(42);
  const base = new Float32Array(n * 3);
  const spin = new Float32Array(n);
  const color = new THREE.Color();
  for (let i = 0; i < n; i++) {
    // Distribui os objetos numa casca esférica em volta da câmera.
    const r = 4 + rand() * 10;
    const th = rand() * Math.PI * 2;
    const ph = Math.acos(2 * rand() - 1);
    base[i * 3] = r * Math.sin(ph) * Math.cos(th);
    base[i * 3 + 1] = r * Math.cos(ph);
    base[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    spin[i] = 0.5 + rand() * 2;
    mesh.setColorAt(i, color.setHSL(rand(), 0.6, 0.55));
  }
  scene.add(mesh);
  const dummy = new THREE.Object3D();

  function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = cfg.stereo ? (w / 2) / h : w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener('resize', resize);

  // tSec é o tempo desde o início da execução: o conteúdo de cada quadro depende
  // só do relógio, então todas as execuções mostram a mesma coisa.
  function render(tSec) {
    for (let i = 0; i < n; i++) {
      dummy.position.set(base[i * 3], base[i * 3 + 1], base[i * 3 + 2]);
      dummy.rotation.set(tSec * spin[i], tSec * spin[i] * 0.7, 0);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;

    camera.position.set(Math.sin(tSec * 0.2) * 1.5, Math.sin(tSec * 0.3) * 0.5, Math.cos(tSec * 0.2) * 1.5);
    camera.lookAt(Math.sin(tSec * 0.15) * 10, 0, Math.cos(tSec * 0.15) * 10);

    if (cfg.stereo) {
      const size = renderer.getSize(new THREE.Vector2());
      const half = size.x / 2;
      camera.updateMatrixWorld();
      stereoCam.update(camera);
      renderer.setScissorTest(true);
      renderer.setScissor(0, 0, half, size.y);
      renderer.setViewport(0, 0, half, size.y);
      renderer.render(scene, stereoCam.cameraL);
      renderer.setScissor(half, 0, half, size.y);
      renderer.setViewport(half, 0, half, size.y);
      renderer.render(scene, stereoCam.cameraR);
      renderer.setScissorTest(false);
    } else {
      renderer.render(scene, camera);
    }
  }

  function dispose() {
    window.removeEventListener('resize', resize);
    geo.dispose();
    mat.dispose();
    mesh.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
  }

  return { render, dispose, renderer };
}

// ---------------------------------------------------------------------------
// Rastreador: câmera + MediaPipe Pose Landmarker

let visionModule = null;
let visionFileset = null;

async function loadVision() {
  if (!visionModule) visionModule = await import('@mediapipe/tasks-vision');
  if (!visionFileset) visionFileset = await visionModule.FilesetResolver.forVisionTasks(MP_WASM);
  return visionModule;
}

async function startTracker(cfg) {
  const res = CONDITIONS[cfg.condition];
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      facingMode: cfg.facing,
      width: { ideal: res.width },
      height: { ideal: res.height },
      frameRate: { ideal: cfg.camFps },
    },
  });
  const video = ui.video;
  video.srcObject = stream;
  await video.play();
  const settings = stream.getVideoTracks()[0].getSettings();

  const vision = await loadVision();
  const landmarker = await vision.PoseLandmarker.createFromOptions(visionFileset, {
    baseOptions: { modelAssetPath: MODEL_URL(cfg.model), delegate: cfg.delegate },
    runningMode: 'VIDEO',
    numPoses: 1,
  });

  function stop() {
    try { landmarker.close(); } catch { /* ignora */ }
    for (const t of stream.getTracks()) t.stop();
    video.srcObject = null;
  }

  return { video, landmarker, settings, stop };
}

// ---------------------------------------------------------------------------
// Estatística

function percentile(sorted, p) {
  if (!sorted.length) return NaN;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

function stats(values) {
  const v = values.filter(Number.isFinite);
  if (!v.length) return { n: 0, mean: NaN, p50: NaN, p95: NaN, p99: NaN, max: NaN };
  const sorted = Float64Array.from(v).sort();
  const sum = v.reduce((a, b) => a + b, 0);
  return {
    n: v.length,
    mean: sum / v.length,
    p50: percentile(sorted, 50),
    p95: percentile(sorted, 95),
    p99: percentile(sorted, 99),
    max: sorted[sorted.length - 1],
  };
}

function summarize(run) {
  const f = run.frames;
  const warmMs = run.meta.warmup_s * 1000;
  const frameMs = [];
  const infMs = [];
  let trackerFrames = 0;
  let poseFrames = 0;
  for (let i = 0; i < f.n; i++) {
    if (f.t_ms[i] < warmMs) continue;
    frameMs.push(f.frame_ms[i]);
    if (f.tracker_ran[i]) {
      trackerFrames++;
      infMs.push(f.inference_ms[i]);
      if (f.poses[i] > 0) poseFrames++;
    }
  }
  const ft = stats(frameMs);
  const inf = stats(infMs);
  const measuredS = Math.max(0, f.n ? (f.t_ms[f.n - 1] - warmMs) / 1000 : 0);
  return {
    frames_measured: ft.n,
    frame_mean_ms: ft.mean,
    frame_p50_ms: ft.p50,
    frame_p95_ms: ft.p95,
    frame_p99_ms: ft.p99,
    frame_max_ms: ft.max,
    fps_mean: ft.mean ? 1000 / ft.mean : NaN,
    tracker_runs: trackerFrames,
    tracker_hz: measuredS ? trackerFrames / measuredS : NaN,
    inference_mean_ms: inf.mean,
    inference_p95_ms: inf.p95,
    pose_detected_ratio: trackerFrames ? poseFrames / trackerFrames : NaN,
  };
}

// ---------------------------------------------------------------------------
// Uma execução

let abortRequested = false;

function readConfig() {
  return {
    owner: ui.owner.value.trim(),
    condition: ui.condition.value,
    rep: parseInt(ui.rep.value, 10) || 1,
    duration: Math.max(5, parseFloat(ui.duration.value) || 120),
    warmup: Math.max(0, parseFloat(ui.warmup.value) || 0),
    objects: Math.max(1, parseInt(ui.objects.value, 10) || 3000),
    stereo: ui.stereo.checked,
    pixelRatio: parseFloat(ui.pixelRatio.value) || 1,
    model: ui.model.value,
    delegate: ui.delegate.value,
    facing: ui.facing.value,
    camFps: parseFloat(ui.camFps.value) || 30,
  };
}

async function batteryInfo() {
  try {
    if (!navigator.getBattery) return { level: '', charging: '' };
    const b = await navigator.getBattery();
    return { level: b.level, charging: b.charging ? 1 : 0 };
  } catch {
    return { level: '', charging: '' };
  }
}

const nextFrame = () => new Promise((r) => requestAnimationFrame(r));

async function runOnce() {
  const cfg = readConfig();
  if (!cfg.owner) {
    setStatus('Preencha o nome do integrante antes de medir.', true);
    return;
  }
  savePrefs();
  abortRequested = false;
  ui.start.disabled = true;

  // Tela cheia precisa do clique do usuário, então vem antes de qualquer espera.
  let fullscreen = false;
  try {
    await document.documentElement.requestFullscreen({ navigationUI: 'hide' });
    fullscreen = true;
    if (cfg.stereo) await screen.orientation.lock('landscape').catch(() => {});
  } catch { /* segue sem tela cheia */ }

  let tracker = null;
  let world = null;
  let wakeLock = null;
  let pageHidden = 0;
  const onVisibility = () => { if (document.hidden) pageHidden++; };

  try {
    if (CONDITIONS[cfg.condition]) {
      setStatus('Abrindo câmera e carregando o modelo…');
      tracker = await startTracker(cfg);
    }

    try { wakeLock = await navigator.wakeLock?.request('screen'); } catch { /* opcional */ }
    document.addEventListener('visibilitychange', onVisibility);

    document.body.classList.add('running');
    ui.hud.hidden = false;
    await nextFrame();
    await nextFrame();
    world = buildScene(ui.canvas, cfg);

    const batteryStart = await batteryInfo();
    const cap = Math.ceil(cfg.duration * MAX_FPS_BUFFER) + 10;
    const f = {
      n: 0,
      t_ms: new Float64Array(cap),
      epoch_ms: new Float64Array(cap),
      frame_ms: new Float64Array(cap),
      work_ms: new Float64Array(cap),
      tracker_ran: new Uint8Array(cap),
      inference_ms: new Float64Array(cap),
      poses: new Uint8Array(cap),
    };
    const durationMs = cfg.duration * 1000;

    await new Promise((resolve) => {
      let startTs = null;
      let prevTs = null;
      let lastVideoTime = -1;
      let lastHud = 0;
      let hudFrames = 0;

      function frame(ts) {
        const w0 = performance.now();
        if (startTs === null) startTs = ts;
        const t = ts - startTs;

        let ran = 0;
        let infMs = NaN;
        let poses = 0;
        if (tracker) {
          const v = tracker.video;
          if (v.readyState >= 2 && v.currentTime !== lastVideoTime) {
            lastVideoTime = v.currentTime;
            const i0 = performance.now();
            const result = tracker.landmarker.detectForVideo(v, i0);
            infMs = performance.now() - i0;
            ran = 1;
            poses = result.landmarks ? result.landmarks.length : 0;
          }
        }

        world.render(t / 1000);

        const i = f.n;
        if (i < cap) {
          f.t_ms[i] = t;
          f.epoch_ms[i] = performance.timeOrigin + ts;
          f.frame_ms[i] = prevTs === null ? NaN : ts - prevTs;
          f.work_ms[i] = performance.now() - w0;
          f.tracker_ran[i] = ran;
          f.inference_ms[i] = infMs;
          f.poses[i] = poses;
          f.n++;
        }
        prevTs = ts;

        hudFrames++;
        if (ts - lastHud >= 500) {
          const fps = (hudFrames * 1000) / (ts - lastHud || 1);
          const phase = t < cfg.warmup * 1000 ? 'aquecendo' : 'medindo';
          ui.hudText.textContent =
            `${cfg.condition} · rep ${cfg.rep} · ${phase} ${(t / 1000).toFixed(0)}/${cfg.duration}s · ${fps.toFixed(0)} fps` +
            (tracker ? ` · rastreador ${Number.isFinite(infMs) ? infMs.toFixed(1) + ' ms' : '…'}` : '');
          lastHud = ts;
          hudFrames = 0;
        }

        if (t >= durationMs || abortRequested || i >= cap) resolve();
        else requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });

    const batteryEnd = await batteryInfo();
    const cam = tracker ? tracker.settings : {};
    const size = world.renderer.getDrawingBufferSize(new THREE.Vector2());
    const startEpoch = f.n ? f.epoch_ms[0] : Date.now();
    const id = `${new Date(startEpoch).toISOString().replace(/[:.]/g, '-')}_${cfg.condition}_r${cfg.rep}`;

    const run = {
      id,
      meta: {
        run_id: id,
        owner: cfg.owner,
        condition: cfg.condition,
        rep: cfg.rep,
        duration_s: cfg.duration,
        warmup_s: cfg.warmup,
        objects: cfg.objects,
        stereo: cfg.stereo ? 1 : 0,
        pixel_ratio: cfg.pixelRatio,
        canvas_w: size.x,
        canvas_h: size.y,
        device_pixel_ratio: window.devicePixelRatio,
        model: CONDITIONS[cfg.condition] ? cfg.model : '',
        delegate: CONDITIONS[cfg.condition] ? cfg.delegate : '',
        facing: CONDITIONS[cfg.condition] ? cfg.facing : '',
        cam_req_w: CONDITIONS[cfg.condition]?.width ?? '',
        cam_req_h: CONDITIONS[cfg.condition]?.height ?? '',
        cam_req_fps: CONDITIONS[cfg.condition] ? cfg.camFps : '',
        cam_w: cam.width ?? '',
        cam_h: cam.height ?? '',
        cam_fps: cam.frameRate ?? '',
        start_epoch_ms: Math.round(startEpoch),
        end_epoch_ms: Math.round(f.n ? f.epoch_ms[f.n - 1] : Date.now()),
        battery_start: batteryStart.level,
        battery_end: batteryEnd.level,
        charging_start: batteryStart.charging,
        charging_end: batteryEnd.charging,
        aborted: abortRequested ? 1 : 0,
        page_hidden: pageHidden,
        fullscreen: fullscreen ? 1 : 0,
        user_agent: navigator.userAgent,
        app_version: APP_VERSION,
        mediapipe_version: MP_VERSION,
      },
      frames: {
        n: f.n,
        t_ms: f.t_ms.slice(0, f.n),
        epoch_ms: f.epoch_ms.slice(0, f.n),
        frame_ms: f.frame_ms.slice(0, f.n),
        work_ms: f.work_ms.slice(0, f.n),
        tracker_ran: f.tracker_ran.slice(0, f.n),
        inference_ms: f.inference_ms.slice(0, f.n),
        poses: f.poses.slice(0, f.n),
      },
    };
    run.summary = summarize(run);
    await store.put(run);
    lastRun = run;

    const warnings = [];
    if (run.meta.aborted) warnings.push('execução abortada');
    if (pageHidden) warnings.push('a página saiu da tela durante a medição');
    if (batteryStart.charging === 1 || batteryEnd.charging === 1) warnings.push('o aparelho estava carregando');
    if (tracker && cam.width && cam.height) {
      const req = CONDITIONS[cfg.condition];
      const match = (cam.width === req.width && cam.height === req.height) ||
        (cam.width === req.height && cam.height === req.width);
      if (!match) warnings.push(`a câmera entregou ${cam.width}×${cam.height} em vez de ${req.width}×${req.height}`);
    }
    if (tracker && run.summary.pose_detected_ratio < 0.9) {
      warnings.push(`pose encontrada em só ${(run.summary.pose_detected_ratio * 100).toFixed(0)}% dos quadros da câmera`);
    }
    setStatus(warnings.length ? `Salva, com avisos: ${warnings.join('; ')}.` : 'Execução salva.', warnings.length > 0);
    ui.rep.value = String(cfg.rep + 1);
    savePrefs();
  } catch (err) {
    console.error(err);
    setStatus(`Falhou: ${err && err.message ? err.message : err}`, true);
  } finally {
    document.removeEventListener('visibilitychange', onVisibility);
    if (world) world.dispose();
    if (tracker) tracker.stop();
    try { await wakeLock?.release(); } catch { /* ignora */ }
    document.body.classList.remove('running');
    ui.hud.hidden = true;
    if (document.fullscreenElement) {
      try { screen.orientation.unlock(); } catch { /* ignora */ }
      await document.exitFullscreen().catch(() => {});
    }
    ui.start.disabled = false;
    await refreshTables();
  }
}

// ---------------------------------------------------------------------------
// CSV

const FRAME_COLS = ['run_id', 'owner', 'condition', 'rep', 'frame', 't_ms', 'epoch_ms',
  'frame_ms', 'work_ms', 'tracker_ran', 'inference_ms', 'poses', 'warmup'];

function fmt(v, digits = 3) {
  if (v === '' || v === null || v === undefined) return '';
  if (typeof v === 'number') return Number.isFinite(v) ? (Number.isInteger(v) ? String(v) : v.toFixed(digits)) : '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function framesCsv(runs, withHeader = true) {
  const lines = withHeader ? [FRAME_COLS.join(',')] : [];
  for (const run of runs) {
    const m = run.meta;
    const f = run.frames;
    const warmMs = m.warmup_s * 1000;
    const prefix = [fmt(m.run_id), fmt(m.owner), fmt(m.condition), fmt(m.rep)].join(',');
    for (let i = 0; i < f.n; i++) {
      lines.push([
        prefix, i, fmt(f.t_ms[i]), fmt(f.epoch_ms[i], 1), fmt(f.frame_ms[i]), fmt(f.work_ms[i]),
        f.tracker_ran[i], fmt(f.inference_ms[i]), f.poses[i], f.t_ms[i] < warmMs ? 1 : 0,
      ].join(','));
    }
  }
  return lines.join('\n') + '\n';
}

function summaryCsv(runs) {
  if (!runs.length) return '';
  const metaCols = Object.keys(runs[0].meta);
  const sumCols = Object.keys(runs[0].summary);
  const lines = [[...metaCols, ...sumCols].join(',')];
  for (const run of runs) {
    lines.push([...metaCols.map((k) => fmt(run.meta[k])), ...sumCols.map((k) => fmt(run.summary[k]))].join(','));
  }
  return lines.join('\n') + '\n';
}

function download(name, text) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function downloadRuns(runs, tag) {
  download(`resumo_${tag}.csv`, summaryCsv(runs));
  await sleep(600); // alguns navegadores bloqueiam dois downloads no mesmo instante
  download(`quadros_${tag}.csv`, framesCsv(runs));
}

// ---------------------------------------------------------------------------
// Interface

let lastRun = null;
let clearArmed = false;

function setStatus(msg, isError = false) {
  ui.status.textContent = msg;
  ui.status.classList.toggle('error', isError);
}

const n2 = (v) => (Number.isFinite(v) ? v.toFixed(2) : '—');

function showLast(run) {
  if (!run) { ui.last.hidden = true; return; }
  const s = run.summary;
  const m = run.meta;
  const rows = [
    ['Condição', `${m.condition} · rep ${m.rep}`],
    ['Quadros medidos', s.frames_measured],
    ['Tempo de quadro médio', `${n2(s.frame_mean_ms)} ms`],
    ['p50 / p95 / p99', `${n2(s.frame_p50_ms)} / ${n2(s.frame_p95_ms)} / ${n2(s.frame_p99_ms)} ms`],
    ['Pior quadro', `${n2(s.frame_max_ms)} ms`],
    ['FPS médio', n2(s.fps_mean)],
  ];
  if (m.model) {
    rows.push(['Câmera entregue', `${m.cam_w}×${m.cam_h} @ ${n2(m.cam_fps)} fps`]);
    rows.push(['Rastreador', `${n2(s.tracker_hz)} Hz · ${n2(s.inference_mean_ms)} ms médio · p95 ${n2(s.inference_p95_ms)} ms`]);
    rows.push(['Pose encontrada', `${n2(s.pose_detected_ratio * 100)}%`]);
  }
  ui.lastTable.innerHTML = rows.map(([k, v]) => `<tr><th>${k}</th><td class="num">${v}</td></tr>`).join('');
  ui.last.hidden = false;
}

async function refreshTables() {
  const runs = (await store.all()).sort((a, b) => a.meta.start_epoch_ms - b.meta.start_epoch_ms);
  if (!runs.length) {
    ui.runsTable.innerHTML = '<tr><td>Nenhuma execução ainda.</td></tr>';
  } else {
    const head = '<tr><th>Hora</th><th>Quem</th><th>Cond.</th><th class="num">Rep</th><th class="num">p95 ms</th><th class="num">Média ms</th></tr>';
    const body = runs.map((r) => {
      const time = new Date(r.meta.start_epoch_ms).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      const flag = r.meta.aborted ? ' (abortada)' : '';
      return `<tr><td>${time}</td><td>${escapeHtml(r.meta.owner)}</td><td>${r.meta.condition}${flag}</td>` +
        `<td class="num">${r.meta.rep}</td><td class="num">${n2(r.summary.frame_p95_ms)}</td><td class="num">${n2(r.summary.frame_mean_ms)}</td></tr>`;
    }).join('');
    ui.runsTable.innerHTML = head + body;
  }
  ui.dlAll.disabled = !runs.length;
  showLast(lastRun);
  return runs;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

ui.start.addEventListener('click', runOnce);
ui.abort.addEventListener('click', () => { abortRequested = true; });
ui.dlLast.addEventListener('click', () => { if (lastRun) downloadRuns([lastRun], lastRun.id); });
ui.dlAll.addEventListener('click', async () => {
  const runs = (await store.all()).sort((a, b) => a.meta.start_epoch_ms - b.meta.start_epoch_ms);
  if (runs.length) downloadRuns(runs, `todas_${new Date().toISOString().slice(0, 10)}`);
});
ui.clear.addEventListener('click', async () => {
  // Dois toques para apagar, sem caixa de diálogo do navegador.
  if (!clearArmed) {
    clearArmed = true;
    ui.clear.textContent = 'Toque de novo para apagar tudo';
    setTimeout(() => { clearArmed = false; ui.clear.textContent = 'Apagar tudo'; }, 4000);
    return;
  }
  clearArmed = false;
  ui.clear.textContent = 'Apagar tudo';
  await store.clear();
  lastRun = null;
  await refreshTables();
  setStatus('Execuções apagadas.');
});
for (const k of PREF_FIELDS) ui[k].addEventListener('change', savePrefs);

loadPrefs();
await store.open();
await refreshTables();
if (!window.isSecureContext) {
  setStatus('Abra esta página por HTTPS (GitHub Pages) para a câmera funcionar.', true);
}
