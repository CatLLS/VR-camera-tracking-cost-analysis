// Uma thread extra do jogo: alterna trabalho (contas) e pausa, como uma thread de
// física ou IA que faz sua parte a cada quadro e espera o próximo.
//
// Mensagens recebidas:  { cmd: 'start', busyMs, periodMs }
// Mensagens enviadas, a cada ~1 s:  { units, busyMs, wallMs }
//   units  = unidades de trabalho completadas no intervalo
//   busyMs = tempo de relógio que a thread passou na fase de trabalho
//   wallMs = duração real do intervalo
// O fim é feito pela página com worker.terminate().
//
// A fração ocupada (busyMs / periodMs, 50%) é mantida na média: a pausa usa
// setTimeout, que costuma dormir mais que o pedido, então a fase de trabalho
// seguinte se estende até a média voltar a 50%. Se o escalonador tira a thread
// do núcleo no meio do trabalho, o tempo continua contando como fase de trabalho
// e o que cai é `units` — é aí que a disputa por CPU aparece.

let acc = 0;

// Uma unidade de trabalho: contas em ponto flutuante sem memória envolvida,
// então o custo é só tempo de CPU.
function unit() {
  let x = acc + 1.0001;
  for (let i = 0; i < 2000; i++) x = Math.sqrt(x * 1.0001 + i) * 0.999 + Math.sin(i);
  acc = x % 1000;
}

let units = 0;
let busy = 0;
let busyTotal = 0;
let startT = 0;
let lastReport = 0;

function report(now) {
  if (now - lastReport >= 1000) {
    postMessage({ units, busyMs: busy, wallMs: now - lastReport });
    units = 0;
    busy = 0;
    lastReport = now;
  }
}

function cycle(busyMs, periodMs) {
  const duty = busyMs / periodMs;
  const t0 = performance.now();
  // Trabalha pelo menos busyMs e, se a pausa anterior passou do ponto, até
  // recuperar a média (limitado a 4× para não virar uma rajada longa).
  for (;;) {
    unit();
    units++;
    const now = performance.now();
    const phase = now - t0;
    if (phase >= 4 * busyMs) break;
    if (phase >= busyMs && busyTotal + phase >= duty * (now - startT)) break;
  }
  const t1 = performance.now();
  busy += t1 - t0;
  busyTotal += t1 - t0;
  report(t1);
  setTimeout(() => cycle(busyMs, periodMs), Math.max(0, periodMs - busyMs));
}

onmessage = (e) => {
  if (e.data && e.data.cmd === 'start') {
    startT = performance.now();
    lastReport = startT;
    cycle(e.data.busyMs, e.data.periodMs);
  }
};
