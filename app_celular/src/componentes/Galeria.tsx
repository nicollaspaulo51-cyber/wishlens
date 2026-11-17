// Galeria do Museu, como um corredor de museu: cada foto salva fica num totem com plaquinha, e totens de câmera e
// troféu decoram o caminho. Arrastar para o lado passa as fotos; a do centro fica grande e as dos lados viram de leve.
import { useMemo, useRef, useState, type ReactNode } from 'react';
import { Animated, FlatList, Image, Modal, Pressable, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { FONTE_TITULO, useCores } from '../lib/cores';
import { apagarDaGaleria, enderecoDa, useGaleria, type FotoGaleria } from '../lib/galeria';
import { useEntrada, useLaco } from '../lib/movimento';
import { Holografico as Brilho } from './efeitos/Holografico';
import { CompartilharFoto } from './CompartilharFoto';
import { Apagado, Botao } from './ui';
import { Icone } from './icones/Icone';

type Item = { tipo: 'foto'; foto: FotoGaleria; n: number } | { tipo: 'camera' | 'trofeu'; chave: string };

// A fila do museu: câmera na entrada, troféu na saída e um totem a cada 3 fotos, alternando
function montarFila(fotos: FotoGaleria[]): Item[] {
  if (!fotos.length) return [];
  const fila: Item[] = [{ tipo: 'camera', chave: 'entrada' }];
  fotos.forEach((foto, n) => {
    fila.push({ tipo: 'foto', foto, n });
    if ((n + 1) % 3 === 0 && n < fotos.length - 1) fila.push({ tipo: n % 2 ? 'camera' : 'trofeu', chave: `meio-${n}` });
  });
  fila.push({ tipo: 'trofeu', chave: 'saida' });
  return fila;
}

const quando = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
};

export function Galeria({ visita }: { visita: number }) {
  const c = useCores();
  const { width } = useWindowDimensions();
  const fotos = useGaleria();
  const fila = useMemo(() => montarFila(fotos), [fotos]);
  const item = Math.round(Math.min(width * 0.62, 300));
  const lado = (width - item) / 2;
  const x = useRef(new Animated.Value(0)).current;
  const [centro, setCentro] = useState(1); // índice da fila no centro (começa na 1ª foto, depois do totem de entrada)
  const centroRef = useRef(1);
  const larguraRef = useRef(item);
  larguraRef.current = item;
  // Criado uma vez: um onScroll novo a cada render solta e religa a rolagem nativa no Android
  const aoRolar = useRef(Animated.event([{ nativeEvent: { contentOffset: { x } } }], {
    useNativeDriver: true,
    listener: (e: { nativeEvent: { contentOffset: { x: number } } }) => {
      const i = Math.round(e.nativeEvent.contentOffset.x / larguraRef.current);
      if (i !== centroRef.current) {
        centroRef.current = i;
        setCentro(i);
      }
    },
  })).current;
  const [aberta, setAberta] = useState<number | null>(null); // índice em `fotos` na tela cheia
  const [opcoes, setOpcoes] = useState<FotoGaleria | null>(null);

  if (!fotos.length) {
    return (
      <View className="items-center gap-[8px] py-[8px]">
        <Totem tipo="camera" chave={visita} />
        <Apagado estilo={{ textAlign: 'center' }}>Tire uma foto e toque em Salvar para ela aparecer aqui.</Apagado>
      </View>
    );
  }

  const fotoNoCentro = fila[centro]?.tipo === 'foto' ? (fila[centro] as { n: number }).n : -1;
  return (
    <View className="-mx-[16px] gap-[10px]">
      <Animated.FlatList data={fila} horizontal showsHorizontalScrollIndicator={false}
        keyExtractor={(it) => (it.tipo === 'foto' ? it.foto.id : it.chave)}
        snapToInterval={item} decelerationRate="fast" contentContainerStyle={{ paddingHorizontal: lado }}
        initialScrollIndex={1}
        getItemLayout={(_, i) => ({ length: item, offset: item * i, index: i })}
        onScroll={aoRolar} testID="galeria"
        scrollEventThrottle={16}
        renderItem={({ item: it, index }) => {
          // A do centro reta e inteira; as vizinhas menores, apagadas e viradas, como paredes de um corredor
          const faixa = [(index - 1) * item, index * item, (index + 1) * item];
          const estilo = {
            width: item, alignItems: 'center' as const, justifyContent: 'flex-end' as const,
            opacity: x.interpolate({ inputRange: faixa, outputRange: [0.5, 1, 0.5], extrapolate: 'clamp' }),
            transform: [
              { perspective: 800 },
              { scale: x.interpolate({ inputRange: faixa, outputRange: [0.8, 1, 0.8], extrapolate: 'clamp' }) },
              { rotateY: x.interpolate({ inputRange: faixa, outputRange: ['20deg', '0deg', '-20deg'], extrapolate: 'clamp' }) },
            ],
          };
          return (
            <Animated.View style={estilo}>
              {it.tipo === 'foto' ? (
                <Quadro foto={it.foto} lado={item - 28} centro={index === centro} chave={`${visita}-${it.foto.id}`}
                  aoTocar={() => setAberta(it.n)} aoSegurar={() => setOpcoes(it.foto)} />
              ) : <Totem tipo={it.tipo} chave={visita} />}
            </Animated.View>
          );
        }} />

      {/* Uma bolinha por foto: a acesa é a do centro */}
      <View className="flex-row justify-center gap-[6px]" accessible
        accessibilityLabel={fotoNoCentro >= 0 ? `Foto ${fotoNoCentro + 1} de ${fotos.length}` : `${fotos.length} fotos`}>
        {fotos.map((f, n) => (
          <View key={f.id} style={{ width: n === fotoNoCentro ? 18 : 7, height: 7, borderRadius: 4,
            backgroundColor: n === fotoNoCentro ? c.destaque : c.linha }} />
        ))}
      </View>
      <Apagado estilo={{ textAlign: 'center', fontSize: 12 }}>Arraste para o lado. Toque para ampliar e segure para mais opções.</Apagado>

      <TelaCheia fotos={fotos} inicio={aberta} aoFechar={() => setAberta(null)} />
      <Opcoes foto={opcoes} aoFechar={() => setOpcoes(null)} />
    </View>
  );
}

// Foto emoldurada em cima do pedestal, com a plaquinha do achado. Entra caindo no pedestal.
function Quadro({ foto, lado, centro, chave, aoTocar, aoSegurar }: {
  foto: FotoGaleria; lado: number; centro: boolean; chave: string; aoTocar: () => void; aoSegurar: () => void;
}) {
  const c = useCores();
  const cai = useEntrada(120, chave);
  return (
    <View className="items-center">
      <Animated.View style={{ opacity: cai, transform: [{ translateY: cai.interpolate({ inputRange: [0, 1], outputRange: [-40, 0] }) }] }}>
        <Pressable onPress={aoTocar} onLongPress={aoSegurar} delayLongPress={350} accessibilityRole="imagebutton"
          accessibilityLabel={`${foto.achado}, ${foto.tema}${foto.pontos ? `, ${foto.pontos} pontos` : ''}, salva em ${quando(foto.criado_em)}`}
          accessibilityHint="Toque para ampliar. Segure para mais opções."
          style={{ width: lado, height: lado, borderWidth: 6, borderColor: '#FFFFFF', borderRadius: 6, overflow: 'hidden',
            backgroundColor: c.superficie, shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 10, shadowOffset: { width: 0, height: 6 },
            elevation: 6 }}>
          <Image source={{ uri: enderecoDa(foto) }} className="w-full h-full" resizeMode="cover" />
          {centro ? <Brilho pausa={3800} /> : null}
        </Pressable>
      </Animated.View>
      <Pedestal altura={78}>
        <View style={{ backgroundColor: c.sol, borderRadius: 4, paddingHorizontal: 8, paddingVertical: 3, maxWidth: lado * 0.62, alignItems: 'center' }}>
          <Text className="font-texto-forte text-sol-tinta text-[12px]" numberOfLines={1} >{foto.emoji} {foto.achado}</Text>
          <Text className="font-texto text-sol-tinta text-[10px]" >{foto.pontos ? `+${foto.pontos} · ` : ''}{quando(foto.criado_em)}</Text>
        </View>
      </Pedestal>
    </View>
  );
}

// Totem de decoração: câmera ou troféu flutuando em cima do pedestal. Sobe do chão quando a galeria abre.
export function Totem({ tipo, chave }: { tipo: 'camera' | 'trofeu'; chave: unknown }) {
  const c = useCores();
  const sobe = useEntrada(200, chave);
  const { v: flutua } = useLaco(1600, 400);
  const ouro = tipo === 'trofeu';
  return (
    <Animated.View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={{ alignItems: 'center',
      opacity: sobe, transform: [{ translateY: sobe.interpolate({ inputRange: [0, 1], outputRange: [50, 0] }) }] }}>
      <Animated.View style={{ width: 76, height: 76, borderRadius: 38, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        backgroundColor: ouro ? c.sol : c.suave, marginBottom: 6,
        transform: [{ translateY: flutua.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0, -6, 0] }) }] }}>
        <Icone nome={ouro ? 'trofeu' : 'camera'} tamanho={42} cor={ouro ? c.solTinta : c.destaque} />
        {ouro ? <Brilho pausa={2600} /> : null}
      </Animated.View>
      <Pedestal altura={120} />
    </Animated.View>
  );
}

// Pedestal de pedra: tampo, coluna e base. A plaquinha vai na coluna.
function Pedestal({ altura, children }: { altura: number; children?: ReactNode }) {
  const c = useCores();
  return (
    <View className="items-center">
      <View className="w-[130px] h-[10px] rounded-[3px] bg-linha" />
      <View style={{ width: 104, height: altura, backgroundColor: c.superficie, borderLeftWidth: 1, borderRightWidth: 1,
        borderColor: c.linha, alignItems: 'center', justifyContent: 'center' }}>
        {children}
      </View>
      <View className="w-[150px] h-[14px] rounded-[3px] bg-linha" />
    </View>
  );
}

function TelaCheia({ fotos, inicio, aoFechar }: { fotos: FotoGaleria[]; inicio: number | null; aoFechar: () => void }) {
  const { width, height } = useWindowDimensions();
  const topo = useSafeAreaInsets().top;
  return (
    <Modal visible={inicio !== null} transparent animationType="fade" onRequestClose={aoFechar}>
      <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.94)' }}>
        {inicio !== null ? (
          <FlatList data={fotos} horizontal pagingEnabled showsHorizontalScrollIndicator={false} initialScrollIndex={inicio}
            keyExtractor={(f) => f.id} getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
            renderItem={({ item: f }) => (
              <View style={{ width, height, justifyContent: 'center', gap: 12 }}>
                <Image source={{ uri: enderecoDa(f) }} style={{ width, height: height * 0.62 }} resizeMode="contain"
                  accessibilityLabel={`Foto: ${f.achado}`} />
                <Text style={{ color: '#fff', textAlign: 'center', fontFamily: FONTE_TITULO, fontSize: 20 }}>{f.emoji} {f.achado}</Text>
                <Text className="font-texto" style={{ color: '#ccc', textAlign: 'center' }}>{f.tema}{f.pontos ? ` · +${f.pontos} pontos` : ''} · {quando(f.criado_em)}</Text>
              </View>
            )} />
        ) : null}
        <Pressable accessibilityRole="button" accessibilityLabel="Fechar a foto" onPress={aoFechar}
          style={{ position: 'absolute', top: topo + 8, right: 12, width: 48, height: 48, alignItems: 'center', justifyContent: 'center' }}>
          <Icone nome="fechar" tamanho={28} cor="#fff" />
        </Pressable>
      </View>
    </Modal>
  );
}

function Opcoes({ foto, aoFechar }: { foto: FotoGaleria | null; aoFechar: () => void }) {
  const c = useCores();
  const baixo = useSafeAreaInsets().bottom;
  return (
    <Modal visible={!!foto} transparent animationType="slide" onRequestClose={aoFechar}>
      <Pressable accessibilityLabel="Fechar" onPress={aoFechar} style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} />
      {foto ? (
        <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 22, borderTopRightRadius: 22, padding: 16, paddingBottom: baixo + 16, gap: 12 }}>
          <Text accessibilityRole="header" className="font-titulo text-[20px] text-tinta">{foto.emoji} {foto.achado}</Text>
          <CompartilharFoto foto={enderecoDa(foto)} enviada={enderecoDa(foto)} captura={foto.id} aceita={foto.pontos > 0} placa={foto} />
          <Botao titulo="Apagar da galeria" tipo="secundario" aoTocar={() => { apagarDaGaleria(foto.id); aoFechar(); }} />
        </View>
      ) : null}
    </Modal>
  );
}
