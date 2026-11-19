// Checagens do app contra bugs que já aconteceram e voltaram (roda no CI e com `npm run checar` em app_celular).
//   node scripts/checar_app.js
// Cada regra diz qual bug ela impede. Para uma regra nova: um bug corrigido = uma linha aqui ou um teste.
const fs = require('fs');
const path = require('path');

const RAIZ = path.resolve(__dirname, '..');
const SRC = path.join(RAIZ, 'app_celular', 'src');
const erros = [];

function arquivos(pasta) {
  return fs.readdirSync(pasta, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? arquivos(path.join(pasta, e.name)) : /\.tsx?$/.test(e.name) ? [path.join(pasta, e.name)] : []);
}
const fontes = arquivos(SRC).map((f) => ({ f: path.relative(RAIZ, f), texto: fs.readFileSync(f, 'utf8') }));

// 1. Botão da câmera invisível e sem toque; linhas do placar tortas: com o NativeWind, um Pressable com
//    style em FUNÇÃO perde o estilo no celular. Use estilo fixo + classes `active:`.
for (const { f, texto } of fontes) {
  texto.split('\n').forEach((linha, i) => {
    if (/style=\{\s*\(\s*\{\s*pressed/.test(linha)) erros.push(`${f}:${i + 1}: style em função num Pressable (some no celular com o NativeWind)`);
  });
}

// 2. Ícones trocados por emoji ou sumindo: todo tema e toda aba do juiz (src/temas.py) precisa de desenho em Icone.tsx.
const temas = [...fs.readFileSync(path.join(RAIZ, 'src', 'temas.py'), 'utf8').matchAll(/Tema\("([a-z_]+)"/g)].map((m) => m[1]);
const icone = fs.readFileSync(path.join(SRC, 'componentes', 'icones', 'Icone.tsx'), 'utf8');
for (const id of new Set(temas)) {
  if (!new RegExp(`^\\s+${id}: \\[`, 'm').test(icone)) erros.push(`Icone.tsx: falta o ícone do tema "${id}" (apareceria um emoji)`);
}

// 3. Pulso do mapa de outra cor: o pulso e a borda de cada marcador usam a cor do próprio tema.
const mapa = fs.readFileSync(path.join(SRC, 'componentes', 'Mapa.tsx'), 'utf8');
if (/<Pulso[^>]*cor=\{[^}]*c\.destaque/.test(mapa)) erros.push('Mapa.tsx: o pulso do marcador não usa a cor do tema');

// 4. Chaves que vazariam para o GitHub: o .env do app nunca entra no Git.
const ignorados = fs.readFileSync(path.join(RAIZ, '.gitignore'), 'utf8') + fs.readFileSync(path.join(RAIZ, 'app_celular', '.gitignore'), 'utf8');
if (!/^\.env/m.test(ignorados) && !/app_celular\/\.env/.test(ignorados)) erros.push('.gitignore: o .env do app não está ignorado');

if (erros.length) {
  console.error(`checar_app: ${erros.length} problema(s)\n- ${erros.join('\n- ')}`);
  process.exit(1);
}
console.log(`checar_app: ok (${fontes.length} arquivos, ${new Set(temas).size} temas com ícone)`);
