import type { Region } from 'react-native-maps';
import type { Lugar } from './api';

type ItemMapa = { tipo: 'lugar'; lugar: Lugar }
  | { tipo: 'grupo'; lat: number; lon: number; quantos: number; tema: string; lugares: Lugar[] };

export function agrupar(lugares: Lugar[], regiao: Region, larguraTelaPx: number, tamanhoPx = 48): ItemMapa[] {
  const passo = (regiao.longitudeDelta / larguraTelaPx) * tamanhoPx;
  if (!Number.isFinite(passo) || passo <= 0) return lugares.map((lugar) => ({ tipo: 'lugar', lugar }));

  const passoLat = passo * Math.max(0.01, Math.cos(regiao.latitude * Math.PI / 180));
  const celulas = new Map<string, Lugar[]>();
  for (const lugar of lugares) {
    const chave = `${Math.floor(lugar.lat / passoLat)}:${Math.floor(lugar.lon / passo)}`;
    const celula = celulas.get(chave);
    if (celula) celula.push(lugar);
    else celulas.set(chave, [lugar]);
  }

  return Array.from(celulas.values(), (celula) => {
    if (celula.length === 1) return { tipo: 'lugar', lugar: celula[0] };
    const contagem = new Map<string, number>();
    let lat = 0;
    let lon = 0;
    for (const lugar of celula) {
      lat += lugar.lat;
      lon += lugar.lon;
      contagem.set(lugar.tema, (contagem.get(lugar.tema) ?? 0) + 1);
    }
    const tema = [...contagem].reduce((maior, atual) => atual[1] > maior[1] ? atual : maior)[0];
    return { tipo: 'grupo', lat: lat / celula.length, lon: lon / celula.length, quantos: celula.length, tema, lugares: celula };
  });
}

export function checarAgrupar() {
  const regiao = { latitude: 0, longitude: 0, latitudeDelta: 0.02, longitudeDelta: 0.02 };
  const lugares = [0, 0.00002, 0.00004, 0.045].map((lon, indice): Lugar => ({
    lat: 0, lon, mapa: String(indice), tema: indice === 0 ? 'outro' : 'plantas', nome: '', tipo: null, distancia_km: lon * 111,
  }));
  const [grupo, isolado, ...extras] = agrupar(lugares, regiao, 400);
  console.assert(grupo?.tipo === 'grupo' && grupo.quantos === 3 && grupo.tema === 'plantas'
    && Math.abs(grupo.lon - 0.00002) < 1e-10, 'Três pontos próximos devem formar um grupo no centro, com o tema mais comum');
  console.assert(isolado?.tipo === 'lugar' && isolado.lugar === lugares[3] && !extras.length, 'O ponto a 5 km deve ficar separado');
}
