// Ponte 8083 -> Metro (8081) para o túnel HTTPS: junta a resposta inteira (o Tunnelmole não repassa
// respostas "chunked") e tira o cabeçalho que expõe o caminho das pastas do PC.
const fs = require('fs');
const http = require('http');
const path = require('path');
// uso: node ponte_expo.js [porta_de_fora=8083] [porta_do_metro=8081] [endereco=127.0.0.1] [pasta_do_app]
const [FORA_PORTA = 8083, METRO = 8081, ENDERECO = '127.0.0.1', PROJETO] = process.argv.slice(2);
const FORA = new Set(['transfer-encoding', 'connection', 'keep-alive', 'x-react-native-project-root']);

// Versão do app = a última mudança em src/ ou no .env. No modo --no-dev o manifesto chama o app sempre de
// "bundle", e o Expo Go reaproveitava a cópia velha guardada; com a versão no nome, ele baixa quando o código muda.
function versao() {
  if (!PROJETO) return null;
  let ultima = 0;
  const andar = (pasta) => {
    for (const e of fs.readdirSync(pasta, { withFileTypes: true })) {
      const caminho = path.join(pasta, e.name);
      if (e.isDirectory()) andar(caminho);
      else ultima = Math.max(ultima, fs.statSync(caminho).mtimeMs);
    }
  };
  andar(path.join(PROJETO, 'src'));
  // o estilo também mora fora de src/ (NativeWind, Babel, Metro, entradas)
  for (const arquivo of ['.env', 'tailwind.config.js', 'global.css', 'babel.config.js', 'metro.config.js', 'index.js', 'package.json', 'app.json']) {
    try { ultima = Math.max(ultima, fs.statSync(path.join(PROJETO, arquivo)).mtimeMs); } catch {}
  }
  return Math.floor(ultima).toString(36);
}

http.createServer((req, res) => {
  const ida = http.request({ host: '127.0.0.1', port: Number(METRO), path: req.url, method: req.method, headers: req.headers }, (resp) => {
    const partes = [];
    resp.on('data', (p) => partes.push(p));
    resp.on('end', () => {
      let corpo = Buffer.concat(partes);
      // O manifesto também traz o caminho das pastas do PC no corpo (projectRoot): troca por um nome neutro
      if (/json|multipart|text\/plain/.test(resp.headers['content-type'] || '') && corpo.length < 200000)
      {
        let texto = corpo.toString('utf8').replace(/[A-Za-z]:\\\\+Users\\\\+[^"]*/g, '/app');
        const v = texto.includes('"launchAsset"') ? versao() : null;
        if (v) texto = texto.replace('"key":"bundle"', `"key":"bundle-${v}"`).replace('/entry.bundle?', `/entry.bundle?v=${v}&`);
        corpo = Buffer.from(texto);
      }
      const cab = {};
      for (const [k, v] of Object.entries(resp.headers)) if (!FORA.has(k)) cab[k] = v;
      cab['content-length'] = corpo.length;
      res.writeHead(resp.statusCode, cab);
      res.end(corpo);
      // só o caminho, o status e a plataforma: nada de IP
      console.log(new Date().toISOString().slice(11, 19), req.method, req.url.slice(0, 90), resp.statusCode,
        req.headers['expo-platform'] || '', corpo.length);
    });
  });
  ida.on('error', () => { res.writeHead(502); res.end('Metro fora do ar'); });
  req.pipe(ida);
}).listen(Number(FORA_PORTA), ENDERECO, () => console.log(`ponte do Expo pronta em ${ENDERECO}:${FORA_PORTA} -> Metro ${METRO}`));
