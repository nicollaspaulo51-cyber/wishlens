// Ponte entre o juiz (Docker no WSL) e o Ollama do Windows, que roda a IA de visão na placa de vídeo.
//   node ponte_gpu.js
// - Escuta só no adaptador virtual do WSL (o Ollama não fica visível para a rede de casa) e repassa a 127.0.0.1:11434.
// - O IP do WSL muda quando o PC reinicia: a ponte acha o novo, escuta nele e atualiza VISAO_URL no servidor/.env do juiz.
// - Se a placa passa de LIMITE % de uso na média de 1 minuto (jogo, vídeo, muitas fotos seguidas), a IA pausa por
//   PAUSA_MIN minutos: o modelo sai da memória da placa e o juiz recebe 503, então julga só com o CLIP.
const { execFile } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const os = require('os');
const path = require('path');

const PORTA = 11434;
const MODELO = 'qwen2.5vl:7b';
const LIMITE = 85;        // % de uso da placa (média de 1 minuto)
const PAUSA_MIN = 10;
const AMOSTRAS = 4;       // uma a cada 15 s = 1 minuto
const PASTA_JUIZ = '/opt/wishlens/servidor';
const LOG = path.join(process.env.LOCALAPPDATA || os.tmpdir(), 'WishLens', 'ponte_gpu.log');

fs.mkdirSync(path.dirname(LOG), { recursive: true });
function log(msg) {
  try {
    if (fs.existsSync(LOG) && fs.statSync(LOG).size > 1_000_000) fs.renameSync(LOG, LOG + '.1');
    fs.appendFileSync(LOG, `${new Date().toISOString()} ${msg}\n`);
  } catch {}
  console.log(msg);
}

// ---------------------------------------------------------------- uso da placa
const usos = [];
let pausadaAte = 0;

// Maior uso entre os motores da placa (3D, cópia, compute...), somando todos os programas
const MEDIR = "$s=(Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples;" +
  "($s | Group-Object { $_.InstanceName -replace '^pid_\\d+_','' } | ForEach-Object { ($_.Group | Measure-Object CookedValue -Sum).Sum } | Measure-Object -Maximum).Maximum";

function medir() {
  execFile('powershell.exe', ['-NoProfile', '-Command', MEDIR], { timeout: 20000, windowsHide: true }, (erro, saida) => {
    const uso = parseFloat(String(saida).trim().replace(',', '.'));
    if (erro || Number.isNaN(uso)) return;
    usos.push(Math.min(uso, 100));
    if (usos.length > AMOSTRAS) usos.shift();
    const media = usos.reduce((a, b) => a + b, 0) / usos.length;
    if (usos.length === AMOSTRAS && media >= LIMITE && Date.now() >= pausadaAte) {
      pausadaAte = Date.now() + PAUSA_MIN * 60_000;
      usos.length = 0;
      log(`placa em ${media.toFixed(0)}% no último minuto: IA pausada por ${PAUSA_MIN} min`);
      descarregar();
    } else if (pausadaAte && Date.now() >= pausadaAte) {
      pausadaAte = 0;
      log('pausa acabou: IA de volta');
    }
  });
}

// Tira o modelo da memória da placa (keep_alive 0)
function descarregar() {
  const corpo = JSON.stringify({ model: MODELO, keep_alive: 0 });
  const req = http.request({ host: '127.0.0.1', port: PORTA, path: '/api/generate', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(corpo) } }, (r) => r.resume());
  req.on('error', () => {});
  req.end(corpo);
}

// ---------------------------------------------------------------- repasse
function atender(cliente) {
  cliente.on('error', () => {});
  if (Date.now() < pausadaAte) {  // resposta HTTP pronta: o juiz mostra o motivo e usa só o CLIP
    const min = Math.ceil((pausadaAte - Date.now()) / 60_000);
    const corpo = JSON.stringify({ error: { message: `placa de vídeo ocupada, IA pausada por mais ${min} min` } });
    cliente.end(`HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: ${Buffer.byteLength(corpo)}\r\nConnection: close\r\n\r\n${corpo}`);
    return;
  }
  const ollama = net.connect(PORTA, '127.0.0.1');
  ollama.on('error', () => cliente.destroy());
  cliente.on('error', () => ollama.destroy());
  cliente.pipe(ollama).pipe(cliente);
}

// ---------------------------------------------------------------- IP do WSL
function ipDoWsl() {
  for (const [nome, enderecos] of Object.entries(os.networkInterfaces())) {
    if (!/WSL/i.test(nome)) continue;
    const v4 = (enderecos || []).find((e) => e.family === 'IPv4' && !e.internal);
    if (v4) return v4.address;
  }
  return null;
}

// Põe VISAO_URL com o IP novo no .env do juiz e reinicia só o juiz (se já estiver certo, não mexe)
function avisarJuiz(ip) {
  const url = `http://${ip}:${PORTA}/v1`;
  const sh = `cd ${PASTA_JUIZ} && touch .env && (grep -qx 'VISAO_URL=${url}' .env || ` +
    `(sed -i '/^VISAO_URL=/d' .env && echo 'VISAO_URL=${url}' >> .env && docker compose up -d juiz))`;
  execFile('wsl.exe', ['-d', 'Ubuntu', '-u', 'root', '-e', 'sh', '-c', sh], { timeout: 180000, windowsHide: true },
    (erro) => log(erro ? `não consegui atualizar o juiz: ${erro.message.split('\n')[0]}` : `juiz usando ${url}`));
}

let servidor = null;
let ipAtual = null;
function conferirIp() {
  const ip = ipDoWsl();
  if (!ip || ip === ipAtual) return;
  if (servidor) servidor.close();
  ipAtual = ip;
  servidor = net.createServer(atender);
  servidor.on('error', (e) => { log(`erro ao escutar em ${ip}: ${e.message}`); ipAtual = null; });
  servidor.listen(PORTA, ip, () => { log(`ponte ${ip}:${PORTA} -> 127.0.0.1:${PORTA}`); avisarJuiz(ip); });
}

conferirIp();
setInterval(conferirIp, 30_000);  // o WSL pode subir depois do Windows, e o IP muda a cada reinício
setInterval(medir, 15_000);
