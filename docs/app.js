// Custo do rastreamento AR — mede o tempo de quadro de uma cena 3D com e sem o
// rastreamento de posição do ARCore (sessão WebXR "immersive-ar" do Chrome).
//
// Cada execução grava, por quadro: intervalo desde o quadro anterior (frame_ms),
// tempo gasto no callback (work_ms), tempo gasto lendo os recursos extras do ARCore
// (feature_ms) e o estado do rastreamento. Nada é estimado: todo número sai do
// próprio aparelho.

import * as THREE from 'three';

const APP_VERSION = '2.0.0-ar';

// Recursos extras do ARCore que a página sabe pedir e exercitar a cada quadro.
const FEATURES = {
  hit: { xr: 'hit-test', label: 'hit-test' },
  light: { xr: 'light-estimation', label: 'luz' },
  depth: { xr: 'depth-sensing', label: 'depth' },
};
const DEPTH_INIT = {
  usagePreference: ['cpu-optimized'],
  dataFormatPreference: ['luminance-alpha', 'float32'],
};

const MAX_FPS_BUFFER = 250; // quadros por segundo reservados (cobre telas de 240 Hz)

const $ = (id) => document.getElementById(id);
const ui = {
  owner: $('owner'), mode: $('mode'), featHit: $('feat-hit'), featLight: $('feat-light'),
  featDepth: $('feat-depth'), arFeatures: $('ar-features'), condLabel: $('cond-label'),
  rep: $('rep'), duration: $('duration'), warmup: $('warmup'), objects: $('objects'),
  locked: $('locked'), start: $('btn-start'), probe: $('btn-probe'), abort: $('btn-abort'),
  status: $('status'), hud: $('hud'), hudText: $('hud-text'),
  probeBox: $('probe'), probeTable: $('probe-table'),
  last: $('last'), lastTable: $('last-table'), dlLast: $('btn-dl-last'),
  runsTable: $('runs-table'), dlAll: $('btn-dl-all'), clear: $('btn-clear'),
};

// ---------------------------------------------------------------------------
// Preferências locais (só conveniência: lembra os campos entre aberturas)

const PREF_FIELDS = ['owner', 'mode', 'featHit', 'featLight', 'featDepth', 'rep',
  'duration', 'warmup', 'objects', 'locked'];

function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem('prefs-ar') || '{}');
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
    localStorage.setItem('prefs-ar', JSON.stringify(p));
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
        const req = indexedDB.open('custo-rastreamento-ar', 1);
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

// xr = true monta o renderizador para a sessão WebXR (fundo transparente: atrás
// da cena aparece a imagem da câmera, desenhada pelo próprio Chrome).
function buildScene(cfg, xr) {
  // Um canvas novo a cada execução: o contexto WebGL anterior é descartado.
  const canvas = document.createElement('canvas');
  canvas.id = 'scene';
  document.getElementById('scene')?.remove();
  document.body.prepend(canvas);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: xr, powerPreference: 'high-performance' });
  renderer.setPixelRatio(window.devicePixelRatio); // resolução nativa, como na sessão AR
  if (xr) {
    renderer.xr.enabled = true;
    renderer.xr.setReferenceSpaceType('local');
  }

  const scene = new THREE.Scene();
  scene.background = xr ? null : new THREE.Color(0x101418);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4);
  sun.position.set(5, 10, 7);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 100);
  scene.add(camera);

  const n = cfg.objects;
  const geo = new THREE.IcosahedronGeometry(0.08, 2);
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.2 });
  const mesh = new THREE.InstancedMesh(geo, mat, Math.max(1, n));
  mesh.count = n;
  mesh.frustumCulled = false; // a nuvem inteira é desenhada em todo quadro
  const rand = mulberry32(42);
  const base = new Float32Array(n * 3);
  const spin = new Float32Array(n);
  const color = new THREE.Color();
  for (let i = 0; i < n; i++) {
    // Nuvem de objetos à frente da câmera, entre 0,5 m e 4 m de distância,
    // espalhada dentro do campo de visão.
    const z = -(0.5 + rand() * 3.5);
    base[i * 3] = (rand() * 2 - 1) * 0.45 * -z;
    base[i * 3 + 1] = (rand() * 2 - 1) * 0.8 * -z;
    base[i * 3 + 2] = z;
    spin[i] = 0.5 + rand() * 2;
    mesh.setColorAt(i, color.setHSL(rand(), 0.6, 0.55));
  }
  // Presa à câmera: os objetos são filhos da câmera e acompanham o celular.
  // Solta: ficam no espaço do ambiente, à frente de onde a sessão começou.
  if (cfg.locked) camera.add(mesh);
  else scene.add(mesh);
  const dummy = new THREE.Object3D();

  function resize() {
    if (renderer.xr.isPresenting) return;
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener('resize', resize);

  // tSec é o tempo desde o início da execução: a animação depende só do relógio.
  function render(tSec) {
    for (let i = 0; i < n; i++) {
      dummy.position.set(base[i * 3], base[i * 3 + 1], base[i * 3 + 2]);
      dummy.rotation.set(tSec * spin[i], tSec * spin[i] * 0.7, 0);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    // O three.js atualiza a posição dos filhos da câmera antes de aplicar a pose
    // do AR; aplicar a pose antes evita que a cena presa fique um quadro atrasada.
    if (renderer.xr.isPresenting) renderer.xr.updateCamera(camera);
    renderer.render(scene, camera);
  }

  function dispose() {
    window.removeEventListener('resize', resize);
    renderer.setAnimationLoop(null);
    geo.dispose();
    mat.dispose();
    mesh.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
    canvas.remove();
  }

  return { render, dispose, renderer };
}

// ---------------------------------------------------------------------------
// Sessão AR (ARCore via WebXR)

function sessionInit(featureKeys, required) {
  const xrNames = featureKeys.map((k) => FEATURES[k].xr);
  const init = {
    requiredFeatures: ['local', ...(required ? xrNames : [])],
    optionalFeatures: ['dom-overlay', ...(required ? [] : xrNames)],
    domOverlay: { root: ui.hud },
  };
  if (featureKeys.includes('depth')) init.depthSensing = DEPTH_INIT;
  return init;
}

function describeSession(session) {
  let enabled = '';
  try { enabled = session.enabledFeatures ? [...session.enabledFeatures].join(' ') : 'desconhecido'; } catch { enabled = 'desconhecido'; }
  let depthUsage = '';
  let depthFormat = '';
  try { depthUsage = session.depthUsage || ''; depthFormat = session.depthDataFormat || ''; } catch { /* sem depth */ }
  let frameRate = '';
  try { frameRate = session.frameRate ?? ''; } catch { /* não exposto */ }
  let fbW = '';
  let fbH = '';
  try {
    const layer = session.renderState.baseLayer;
    fbW = layer.framebufferWidth;
    fbH = layer.framebufferHeight;
  } catch { /* sem camada ainda */ }
  return { enabled, depthUsage, depthFormat, frameRate, fbW, fbH };
}

// Prepara o que cada recurso extra precisa e devolve a função que o exercita
// num quadro. Os recursos só custam algo para o ARCore se a página os usar.
async function prepareFeatures(session, featureKeys) {
  const ctx = { hitSource: null, lightProbe: null, depth: featureKeys.includes('depth') };
  if (featureKeys.includes('hit')) {
    const viewer = await session.requestReferenceSpace('viewer');
    ctx.hitSource = await session.requestHitTestSource({ space: viewer });
  }
  if (featureKeys.includes('light')) {
    ctx.lightProbe = await session.requestLightProbe();
  }
  return function exercise(frame, pose) {
    let hits = 0;
    if (ctx.hitSource) hits = frame.getHitTestResults(ctx.hitSource).length;
    if (ctx.lightProbe) frame.getLightEstimate(ctx.lightProbe);
    if (ctx.depth && pose) {
      for (const view of pose.views) {
        const d = frame.getDepthInformation(view);
        if (d) d.getDepthInMeters(0.5, 0.5);
      }
    }
    return hits;
  };
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
  const featMs = [];
  let full = 0;
  let counted = 0;
  for (let i = 0; i < f.n; i++) {
    if (f.t_ms[i] < warmMs) continue;
    frameMs.push(f.frame_ms[i]);
    featMs.push(f.feature_ms[i]);
    counted++;
    if (f.tracking[i] === 2) full++;
  }
  const ft = stats(frameMs);
  const fe = stats(featMs);
  const isAr = run.meta.mode === 'ar';
  return {
    frames_measured: ft.n,
    frame_mean_ms: ft.mean,
    frame_p50_ms: ft.p50,
    frame_p95_ms: ft.p95,
    frame_p99_ms: ft.p99,
    frame_max_ms: ft.max,
    fps_mean: ft.mean ? 1000 / ft.mean : NaN,
    feature_mean_ms: fe.mean,
    feature_p95_ms: fe.p95,
    tracking_full_ratio: isAr && counted ? full / counted : NaN,
  };
}

// ---------------------------------------------------------------------------
// Uma execução

let abortRequested = false;

function selectedFeatures() {
  const keys = [];
  if (ui.featHit.checked) keys.push('hit');
  if (ui.featLight.checked) keys.push('light');
  if (ui.featDepth.checked) keys.push('depth');
  return keys;
}

function conditionLabel(mode, featureKeys) {
  if (mode !== 'ar') return 'sem-ar';
  return ['ar', ...featureKeys.map((k) => FEATURES[k].label)].join('+');
}

function readConfig() {
  const mode = ui.mode.value;
  const features = mode === 'ar' ? selectedFeatures() : [];
  return {
    owner: ui.owner.value.trim(),
    mode,
    features,
    condition: conditionLabel(mode, features),
    rep: parseInt(ui.rep.value, 10) || 1,
    duration: Math.max(5, parseFloat(ui.duration.value) || 120),
    warmup: Math.max(0, parseFloat(ui.warmup.value) || 0),
    objects: Math.max(0, parseInt(ui.objects.value, 10) || 0),
    locked: ui.locked.checked,
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

function newFrameBuffers(cap) {
  return {
    n: 0,
    t_ms: new Float64Array(cap),
    epoch_ms: new Float64Array(cap),
    frame_ms: new Float64Array(cap),
    work_ms: new Float64Array(cap),
    feature_ms: new Float64Array(cap),
    tracking: new Uint8Array(cap),
    hits: new Uint16Array(cap),
  };
}

async function runOnce() {
  const cfg = readConfig();
  if (!cfg.owner) {
    setStatus('Preencha o nome do integrante antes de medir.', true);
    return;
  }
  savePrefs();
  abortRequested = false;
  ui.start.disabled = true;
  ui.probe.disabled = true;

  let session = null;
  let world = null;
  let wakeLock = null;
  let pageHidden = 0;
  let sessionInfo = { enabled: '', depthUsage: '', depthFormat: '', frameRate: '', fbW: '', fbH: '' };
  const onVisibility = () => { if (document.hidden) pageHidden++; };
  ui.hud.hidden = false;

  try {
    // A sessão AR (e a tela cheia) precisam do toque do usuário: vêm antes de
    // qualquer outra espera.
    if (cfg.mode === 'ar') {
      session = await navigator.xr.requestSession('immersive-ar', sessionInit(cfg.features, true));
    } else {
      await document.documentElement.requestFullscreen({ navigationUI: 'hide' }).catch(() => {});
    }

    try { wakeLock = await navigator.wakeLock?.request('screen'); } catch { /* opcional */ }
    document.addEventListener('visibilitychange', onVisibility);
    document.body.classList.add('running');
    await nextFrame();

    world = buildScene(cfg, cfg.mode === 'ar');
    let exercise = null;
    if (session) {
      await world.renderer.xr.setSession(session);
      exercise = await prepareFeatures(session, cfg.features);
      sessionInfo = describeSession(session);
    }

    const batteryStart = await batteryInfo();
    const cap = Math.ceil(cfg.duration * MAX_FPS_BUFFER) + 10;
    const f = newFrameBuffers(cap);
    const durationMs = cfg.duration * 1000;
    let endedByUser = false;

    await new Promise((resolve) => {
      let startTs = null;
      let prevTs = null;
      let lastHud = 0;
      let hudFrames = 0;
      let done = false;
      const finish = () => { if (!done) { done = true; resolve(); } };
      if (session) session.addEventListener('end', () => { endedByUser = true; finish(); });

      function frame(ts, xrFrame) {
        if (done) return;
        const w0 = performance.now();
        if (startTs === null) startTs = ts;
        const t = ts - startTs;

        let tracking = 0;
        let hits = 0;
        let featMs = 0;
        if (xrFrame) {
          const pose = xrFrame.getViewerPose(world.renderer.xr.getReferenceSpace());
          tracking = !pose ? 0 : pose.emulatedPosition ? 1 : 2;
          const f0 = performance.now();
          hits = exercise(xrFrame, pose);
          featMs = performance.now() - f0;
        }

        world.render(t / 1000);

        const i = f.n;
        if (i < cap) {
          f.t_ms[i] = t;
          f.epoch_ms[i] = performance.timeOrigin + ts;
          f.frame_ms[i] = prevTs === null ? NaN : ts - prevTs;
          f.work_ms[i] = performance.now() - w0;
          f.feature_ms[i] = featMs;
          f.tracking[i] = tracking;
          f.hits[i] = Math.min(hits, 65535);
          f.n++;
        }
        prevTs = ts;

        hudFrames++;
        if (ts - lastHud >= 500) {
          const fps = (hudFrames * 1000) / (ts - lastHud || 1);
          const phase = t < cfg.warmup * 1000 ? 'aquecendo' : 'medindo';
          const track = xrFrame ? ` · rastreio ${['perdido', 'só rotação', 'ok'][tracking]}` : '';
          ui.hudText.textContent =
            `${cfg.condition} · rep ${cfg.rep} · ${phase} ${(t / 1000).toFixed(0)}/${cfg.duration}s · ${fps.toFixed(0)} fps${track}`;
          lastHud = ts;
          hudFrames = 0;
        }

        if (t >= durationMs || abortRequested || i >= cap) finish();
        else if (!session) requestAnimationFrame(frame);
      }

      // Na sessão AR quem dita o ritmo dos quadros é o WebXR (setAnimationLoop).
      if (session) world.renderer.setAnimationLoop(frame);
      else requestAnimationFrame(frame);
    });

    world.renderer.setAnimationLoop(null);
    if (session && !endedByUser) await session.end().catch(() => {});

    const batteryEnd = await batteryInfo();
    const size = world.renderer.getDrawingBufferSize(new THREE.Vector2());
    const startEpoch = f.n ? f.epoch_ms[0] : Date.now();
    const id = `${new Date(startEpoch).toISOString().replace(/[:.]/g, '-')}_${cfg.condition}_r${cfg.rep}`;
    const lastT = f.n ? f.t_ms[f.n - 1] : 0;
    const aborted = abortRequested || (endedByUser && lastT < durationMs);

    const run = {
      id,
      meta: {
        run_id: id,
        owner: cfg.owner,
        condition: cfg.condition,
        mode: cfg.mode,
        features_requested: cfg.features.map((k) => FEATURES[k].xr).join(' '),
        features_enabled: sessionInfo.enabled,
        depth_usage: sessionInfo.depthUsage,
        depth_format: sessionInfo.depthFormat,
        xr_frame_rate: sessionInfo.frameRate,
        rep: cfg.rep,
        duration_s: cfg.duration,
        warmup_s: cfg.warmup,
        objects: cfg.objects,
        locked_to_camera: cfg.locked ? 1 : 0,
        // Na sessão AR a cena é desenhada no framebuffer do WebXR, não no canvas.
        render_w: cfg.mode === 'ar' ? sessionInfo.fbW : size.x,
        render_h: cfg.mode === 'ar' ? sessionInfo.fbH : size.y,
        device_pixel_ratio: window.devicePixelRatio,
        start_epoch_ms: Math.round(startEpoch),
        end_epoch_ms: Math.round(f.n ? f.epoch_ms[f.n - 1] : Date.now()),
        battery_start: batteryStart.level,
        battery_end: batteryEnd.level,
        charging_start: batteryStart.charging,
        charging_end: batteryEnd.charging,
        aborted: aborted ? 1 : 0,
        page_hidden: pageHidden,
        user_agent: navigator.userAgent,
        app_version: APP_VERSION,
      },
      frames: {
        n: f.n,
        t_ms: f.t_ms.slice(0, f.n),
        epoch_ms: f.epoch_ms.slice(0, f.n),
        frame_ms: f.frame_ms.slice(0, f.n),
        work_ms: f.work_ms.slice(0, f.n),
        feature_ms: f.feature_ms.slice(0, f.n),
        tracking: f.tracking.slice(0, f.n),
        hits: f.hits.slice(0, f.n),
      },
    };
    run.summary = summarize(run);
    await store.put(run);
    lastRun = run;

    const warnings = [];
    if (aborted) warnings.push('execução interrompida antes do fim');
    if (pageHidden && cfg.mode !== 'ar') warnings.push('a página saiu da tela durante a medição');
    if (batteryStart.charging === 1 || batteryEnd.charging === 1) warnings.push('o aparelho estava carregando');
    if (cfg.mode === 'ar' && run.summary.tracking_full_ratio < 0.9) {
      warnings.push(`rastreamento completo em só ${(run.summary.tracking_full_ratio * 100).toFixed(0)}% dos quadros`);
    }
    setStatus((warnings.length ? `Salva, com avisos: ${warnings.join('; ')}.` : 'Execução salva.') +
      '\nRecarregue a página antes da próxima execução.', warnings.length > 0);
    ui.rep.value = String(cfg.rep + 1);
    savePrefs();
  } catch (err) {
    console.error(err);
    const unsupported = err && (err.name === 'NotSupportedError' || /not supported|feature/i.test(err.message || ''));
    setStatus(`Falhou: ${err && err.message ? err.message : err}` +
      (unsupported ? '\nUm dos recursos pedidos pode não existir neste aparelho: use "Testar recursos do AR".' : ''), true);
    if (session) await session.end().catch(() => {});
  } finally {
    document.removeEventListener('visibilitychange', onVisibility);
    if (world) world.dispose();
    try { await wakeLock?.release(); } catch { /* ignora */ }
    document.body.classList.remove('running');
    ui.hud.hidden = true;
    if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
    ui.start.disabled = false;
    ui.probe.disabled = false;
    await refreshTables();
  }
}

// ---------------------------------------------------------------------------
// Teste de recursos: abre uma sessão AR pedindo tudo como opcional, mede o
// ritmo dos quadros por alguns segundos e mostra o que o aparelho concedeu.

const PROBE_SECONDS = 8;

async function runProbe() {
  ui.start.disabled = true;
  ui.probe.disabled = true;
  ui.hud.hidden = false;
  let session = null;
  let world = null;
  const rows = [];
  try {
    if (!navigator.xr) throw new Error('este navegador não tem WebXR');
    const arOk = await navigator.xr.isSessionSupported('immersive-ar');
    rows.push(['immersive-ar suportado', arOk ? 'sim' : 'não']);
    if (!arOk) throw new Error('o Chrome deste aparelho não oferece sessão AR');

    session = await navigator.xr.requestSession('immersive-ar', sessionInit(Object.keys(FEATURES), false));
    world = buildScene({ objects: 0, locked: true }, true);
    const sz = world.renderer.getDrawingBufferSize(new THREE.Vector2()); // antes do AR assumir o canvas
    await world.renderer.xr.setSession(session);
    const info = describeSession(session);
    rows.push(['Recursos concedidos', info.enabled || '—']);
    if (info.depthUsage) rows.push(['Depth', `${info.depthUsage} · ${info.depthFormat}`]);
    rows.push(['frameRate informado', info.frameRate === '' ? 'não exposto' : String(info.frameRate)]);
    rows.push(['Resolução de desenho do AR', info.fbW ? `${info.fbW}×${info.fbH}` : '—']);
    rows.push(['Resolução de desenho sem AR', `${sz.x}×${sz.y}`]);

    const intervals = [];
    const states = [0, 0, 0];
    await new Promise((resolve) => {
      let start = null;
      let prev = null;
      session.addEventListener('end', resolve);
      world.renderer.setAnimationLoop((ts, xrFrame) => {
        if (start === null) start = ts;
        if (prev !== null) intervals.push(ts - prev);
        prev = ts;
        const pose = xrFrame.getViewerPose(world.renderer.xr.getReferenceSpace());
        states[!pose ? 0 : pose.emulatedPosition ? 1 : 2]++;
        world.render((ts - start) / 1000);
        ui.hudText.textContent = `Testando recursos… ${((ts - start) / 1000).toFixed(0)}/${PROBE_SECONDS}s (mova o celular devagar)`;
        if (ts - start >= PROBE_SECONDS * 1000 || abortRequested) resolve();
      });
    });
    world.renderer.setAnimationLoop(null);
    await session.end().catch(() => {});

    const s = stats(intervals);
    const total = states[0] + states[1] + states[2] || 1;
    rows.push(['Quadros medidos', String(s.n)]);
    rows.push(['Intervalo mediano', `${n2(s.p50)} ms (≈ ${n2(1000 / s.p50)} fps)`]);
    rows.push(['Rastreamento ok / só rotação / perdido',
      `${n2((states[2] / total) * 100)}% / ${n2((states[1] / total) * 100)}% / ${n2((states[0] / total) * 100)}%`]);
    setStatus('Teste concluído. Recarregue a página antes de medir.');
  } catch (err) {
    console.error(err);
    rows.push(['Erro', err && err.message ? err.message : String(err)]);
    setStatus(`Teste falhou: ${err && err.message ? err.message : err}`, true);
    if (session) await session.end().catch(() => {});
  } finally {
    if (world) world.dispose();
    ui.hud.hidden = true;
    ui.probeTable.innerHTML = rows.map(([k, v]) => `<tr><th>${k}</th><td>${escapeHtml(v)}</td></tr>`).join('');
    ui.probeBox.hidden = false;
    ui.start.disabled = false;
    ui.probe.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// CSV

const FRAME_COLS = ['run_id', 'owner', 'condition', 'rep', 'frame', 't_ms', 'epoch_ms',
  'frame_ms', 'work_ms', 'feature_ms', 'tracking', 'hits', 'warmup'];

function fmt(v, digits = 3) {
  if (v === '' || v === null || v === undefined) return '';
  if (typeof v === 'number') return Number.isFinite(v) ? (Number.isInteger(v) ? String(v) : v.toFixed(digits)) : '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function framesCsv(runs) {
  const lines = [FRAME_COLS.join(',')];
  for (const run of runs) {
    const m = run.meta;
    const f = run.frames;
    const warmMs = m.warmup_s * 1000;
    const prefix = [fmt(m.run_id), fmt(m.owner), fmt(m.condition), fmt(m.rep)].join(',');
    for (let i = 0; i < f.n; i++) {
      lines.push([
        prefix, i, fmt(f.t_ms[i]), fmt(f.epoch_ms[i], 1), fmt(f.frame_ms[i]), fmt(f.work_ms[i]),
        fmt(f.feature_ms[i]), f.tracking[i], f.hits[i], f.t_ms[i] < warmMs ? 1 : 0,
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

function updateCondition() {
  ui.arFeatures.disabled = ui.mode.value !== 'ar';
  ui.condLabel.textContent = conditionLabel(ui.mode.value, ui.mode.value === 'ar' ? selectedFeatures() : []);
}

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
  if (m.mode === 'ar') {
    rows.push(['Rastreamento completo', `${n2(s.tracking_full_ratio * 100)}%`]);
    if (m.features_requested) rows.push(['Recursos extras', `${n2(s.feature_mean_ms)} ms médio · p95 ${n2(s.feature_p95_ms)} ms`]);
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
      const flag = r.meta.aborted ? ' (interrompida)' : '';
      return `<tr><td>${time}</td><td>${escapeHtml(r.meta.owner)}</td><td>${escapeHtml(r.meta.condition)}${flag}</td>` +
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
ui.probe.addEventListener('click', () => { abortRequested = false; runProbe(); });
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
for (const k of PREF_FIELDS) ui[k].addEventListener('change', () => { savePrefs(); updateCondition(); });

loadPrefs();
updateCondition();
await store.open();
await refreshTables();
if (!window.isSecureContext) {
  setStatus('Abra esta página por HTTPS (GitHub Pages) para o AR funcionar.', true);
} else if (!navigator.xr) {
  setStatus('Este navegador não tem WebXR: o modo AR não vai funcionar.', true);
}
