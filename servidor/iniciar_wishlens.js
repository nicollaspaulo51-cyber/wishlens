// Liga e vigia tudo o que o jogo precisa neste PC (Windows + WSL), sem depender de ninguém abrir nada:
//   node iniciar_wishlens.js
// - Uma cópia do projeto em %LOCALAPPDATA%\WishLens\repo, que SEMPRE segue o GitHub (o celular nunca recebe app velho);
// - o juiz no Docker do WSL, atualizado com o GitHub;
// - os dois túneis do Cloudflare (o do juiz roda dentro do WSL e assim o mantém ligado);
// - o servidor do app (Metro, porta 8084) e a ponte do Expo (8083).
// Se algo cai, volta sozinho. Endereços trocam a cada túnel novo: o link atual fica em %LOCALAPPDATA%\WishLens\link.txt.
// Chaves do Supabase: %LOCALAPPDATA%\WishLens\app.env (fora do Git), copiado para app_celular/.env.
const { spawn, execFile } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

const BASE = path.join(process.env.LOCALAPPDATA, 'WishLens');
const REPO = path.join(BASE, 'repo');
const APP = path.join(REPO, 'app_celular');
const GITHUB = 'https://github.com/nicollaspaulo51-cyber/wishlens.git';
const RAMO = 'claude/vibrant-feynman-4fhs11';
const CLOUDFLARED = 'C:\\Program Files (x86)\\cloudflared\\cloudflared.exe';
const LOG = path.join(BASE, 'iniciar.log');
const MINUTOS_ATUALIZAR = 5;

fs.mkdirSync(BASE, { recursive: true });
function log(msg) {
  try {
    if (fs.existsSync(LOG) && fs.statSync(LOG).size > 2_000_000) fs.renameSync(LOG, LOG + '.1');
    fs.appendFileSync(LOG, `${new Date().toISOString()} ${msg}\n`);
  } catch {}
  console.log(msg);
}

function rodar(cmd, args, opcoes = {}) {
  return new Promise((ok, falha) => execFile(cmd, args, { windowsHide: true, maxBuffer: 1 << 24, timeout: 20 * 60_000, ...opcoes },
    (erro, saida, erros) => (erro ? falha(new Error(`${cmd} ${args.join(' ')}: ${String(erros || erro.message).slice(0, 400)}`)) : ok(String(saida)))));
}
const git = (...args) => rodar('git', ['-c', 'core.longpaths=true', '-C', REPO, ...args]);
const wsl = (sh) => rodar('wsl.exe', ['-d', 'Ubuntu', '-u', 'root', '-e', 'sh', '-c', sh]);

// ---------------------------------------------------------------- código sempre igual ao GitHub
// Devolve true quando entraram dependências novas (aí o Metro precisa montar de novo).
async function atualizarRepo() {
  if (!fs.existsSync(path.join(REPO, '.git'))) {
    log('clonando o projeto do GitHub');
    await rodar('git', ['-c', 'core.longpaths=true', 'clone', '--branch', RAMO, GITHUB, REPO]);
    await instalarDependencias();
    return true;
  }
  await git('fetch', '-q', 'origin', RAMO);
  const [antes, depois] = (await Promise.all([git('rev-parse', 'HEAD'), git('rev-parse', 'FETCH_HEAD')])).map((s) => s.trim());
  if (antes === depois) return false;
  const mudou = await git('diff', '--name-only', antes, depois);
  // esta cópia só serve o app (ninguém edita aqui): fica exatamente como o GitHub
  await git('reset', '-q', '--hard', depois);
  log(`projeto atualizado: ${antes.slice(0, 7)} -> ${depois.slice(0, 7)}`);
  const deps = /app_celular\/package(-lock)?\.json/.test(mudou);
  if (deps) await instalarDependencias();
  return deps;
}

async function instalarDependencias() {
  log('instalando as dependências do app');
  await rodar('npm.cmd', ['install', '--no-audit', '--no-fund'], { cwd: APP, shell: true });
}

async function atualizarJuiz() {
  const saida = await wsl('cd /opt/wishlens && antes=$(git rev-parse HEAD) && git pull -q && depois=$(git rev-parse HEAD) && '
    + 'cd servidor && if [ "$antes" != "$depois" ]; then docker compose up -d --build >/dev/null 2>&1 && echo atualizado; '
    + 'else docker compose up -d >/dev/null 2>&1 && echo ok; fi');
  if (saida.includes('atualizado')) log('juiz atualizado com o GitHub');
}

// ---------------------------------------------------------------- processos vigiados
// Cada um volta sozinho se cair. `aoAchar` recebe o endereço do túnel quando ele aparece.
function vigiar(nome, comando, args, opcoes = {}, aoAchar) {
  let filho = null;
  let parar = false;
  const iniciar = () => {
    filho = spawn(comando, args, { windowsHide: true, ...opcoes });
    const ler = (pedaco) => {
      const url = String(pedaco).match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
      if (url && aoAchar) aoAchar(url[0]);
    };
    filho.stdout?.on('data', ler);
    filho.stderr?.on('data', ler);
    filho.on('exit', (codigo) => {
      if (parar) return;
      log(`${nome} parou (código ${codigo}); religando em 5 s`);
      setTimeout(iniciar, 5000);
    });
    log(`${nome} ligado`);
  };
  iniciar();
  return {
    reiniciar() {
      if (!filho) return iniciar();
      // a árvore toda (o npx abre outros processos)
      execFile('taskkill', ['/PID', String(filho.pid), '/T', '/F'], { windowsHide: true }, () => {});
    },
    parar() {
      parar = true;
      if (filho) execFile('taskkill', ['/PID', String(filho.pid), '/T', '/F'], { windowsHide: true }, () => {});
    },
  };
}

let urlJuiz = null;
let urlCelular = null;
let metro = null;

function escreverEnv() {
  const chaves = fs.existsSync(path.join(BASE, 'app.env')) ? fs.readFileSync(path.join(BASE, 'app.env'), 'utf8') : '';
  const linhas = chaves.split(/\r?\n/).filter((l) => l && !l.startsWith('EXPO_PUBLIC_SERVIDOR_URL='));
  fs.writeFileSync(path.join(APP, '.env'), [`EXPO_PUBLIC_SERVIDOR_URL=${urlJuiz}`, ...linhas, ''].join('\n'));
}

// O Metro guarda o endereço do juiz e o do túnel dentro do app montado: muda um, monta de novo
function ligarMetro() {
  if (!urlJuiz || !urlCelular) return;
  escreverEnv();
  fs.writeFileSync(path.join(BASE, 'link.txt'), `exps://${new URL(urlCelular).host}\n`);
  log(`LINK DO CELULAR: exps://${new URL(urlCelular).host}`);
  const env = { ...process.env, EXPO_PACKAGER_PROXY_URL: urlCelular };
  if (metro) metro.parar();
  metro = vigiar('servidor do app (Metro)', 'npx.cmd', ['expo', 'start', '--no-dev', '--minify', '--clear', '--port', '8084'],
    { cwd: APP, env, shell: true });
  aquecer();
}

// Monta o app uma vez antes de alguém abrir: a 1ª abertura no celular não espera ~1 min
function aquecer(tentativa = 0) {
  setTimeout(() => {
    http.get({ host: '127.0.0.1', port: 8083, path: '/', headers: { 'expo-platform': 'android', accept: 'application/expo+json' } }, (r) => {
      let corpo = '';
      r.on('data', (p) => { corpo += p; });
      r.on('end', () => {
        const url = corpo.match(/"launchAsset":\{[^}]*"url":"(https?:\/\/[^"]+)"/);
        if (!url) return tentativa < 20 && aquecer(tentativa + 1);
        const local = url[1].replace(/^https?:\/\/[^/]+/, '');
        http.get({ host: '127.0.0.1', port: 8084, path: local, timeout: 600_000 }, (b) => {
          b.resume();
          b.on('end', () => log('app montado e pronto para abrir'));
        }).on('error', () => {});
      });
    }).on('error', () => tentativa < 20 && aquecer(tentativa + 1));
  }, 15000);
}

// ---------------------------------------------------------------- início
async function main() {
  // só um ligador por vez (abrir duas vezes não duplica servidores)
  await new Promise((ok) => {
    const trava = net.createServer().once('error', () => { log('outro ligador já está rodando; saindo'); process.exit(0); });
    trava.listen(8089, '127.0.0.1', ok);
  });
  log('ligando o WishLens');
  try { await atualizarRepo(); } catch (e) { log(`não consegui atualizar o projeto: ${e.message}`); }
  // O atalho do Windows roda a cópia em %LOCALAPPDATA%\WishLens; a versão do GitHub vale a partir do próximo início
  try {
    const novo = path.join(REPO, 'servidor', 'iniciar_wishlens.js');
    if (fs.existsSync(novo) && path.resolve(__filename) !== path.resolve(novo)
        && fs.readFileSync(novo, 'utf8') !== fs.readFileSync(__filename, 'utf8')) {
      fs.copyFileSync(novo, __filename);
      log('ligador atualizado: a versão nova vale a partir do próximo início');
    }
  } catch {}
  try { await atualizarJuiz(); } catch (e) { log(`não consegui ligar o juiz: ${e.message}`); }

  // A ponte da placa de vídeo (Ollama): se ela cai, o juiz espera à toa e a foto demora. Aqui ela volta sozinha.
  vigiar('ponte da placa de vídeo', process.execPath, [path.join(REPO, 'servidor', 'ponte_gpu.js')]);
  vigiar('ponte do Expo', process.execPath, [path.join(REPO, 'servidor', 'ponte_expo.js'), '8083', '8084', '0.0.0.0', APP]);
  // dentro do WSL: além do túnel, mantém o WSL (e o juiz) ligado
  vigiar('túnel do juiz', 'wsl.exe', ['-d', 'Ubuntu', '-u', 'root', '-e', '/opt/cloudflared/cloudflared', 'tunnel',
    '--no-autoupdate', '--url', 'http://localhost:7860'], {}, (url) => {
    if (url === urlJuiz) return;
    urlJuiz = url;
    log(`juiz em ${url}`);
    ligarMetro();
  });
  vigiar('túnel do celular', CLOUDFLARED, ['tunnel', '--no-autoupdate', '--url', 'http://localhost:8083'], {}, (url) => {
    if (url === urlCelular) return;
    urlCelular = url;
    ligarMetro();
  });

  setInterval(async () => {
    try {
      const deps = await atualizarRepo();
      // o Metro vê os arquivos novos sozinho; só dependências novas pedem montar de novo
      if (deps && metro) ligarMetro();
      await atualizarJuiz();
    } catch (e) {
      log(`atualização falhou (tento de novo em ${MINUTOS_ATUALIZAR} min): ${e.message}`);
    }
  }, MINUTOS_ATUALIZAR * 60_000);
}

main().catch((e) => { log(`erro: ${e.stack || e}`); process.exit(1); });
