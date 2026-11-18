// Galeria do Museu, como um corredor de museu: cada foto salva fica num totem com plaquinha, e totens de câmera e
// troféu decoram o caminho. Arrastar para o lado passa as fotos; a do centro fica grande e as dos lados ficam menores.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Animated, FlatList, Image, Pressable, Text, useWindowDimensions, View } from 'react-native';
import Reanimated, { Extrapolation, interpolate, runOnJS, useAnimatedScrollHandler, useAnimatedStyle, useSharedValue,
  type SharedValue } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { PALETA, useCores } from '../lib/cores';
import { apagarDaGaleria, enderecoDa, useGaleria, type FotoGaleria } from '../lib/galeria';
import { useEntrada, useLaco } from '../lib/movimento';
import { CompartilharFoto } from './CompartilharFoto';
import { Apagado, Botao, ModalTema } from './ui';
import { Icone, IconeTema } from './icones/Icone';

type Item = { tipo: 'foto'; foto: FotoGaleria; n: number } | { tipo: 'camera' | 'trofeu'; chave: string };

const idTemaDaFoto = (foto: FotoGaleria) => foto.temaId ?? foto.tema.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');

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
  // Reanimated: a rolagem mexe a escala e a opacidade na thread de interface, sem passar pelo JavaScript a cada quadro
  const x = useSharedValue(0);
  const largura = useSharedValue(item);
  useEffect(() => { largura.value = item; }, [item, largura]);
  const [centro, setCentro] = useState(1); // índice da fila no centro (começa na 1ª foto, depois do totem de entrada)
  const centroSV = useSharedValue(1);
  const aoRolar = useAnimatedScrollHandler({
    onScroll: (e) => {
      x.value = e.contentOffset.x;
      const i = Math.round(e.contentOffset.x / largura.value);
      if (i !== centroSV.value) {
        centroSV.value = i;
        runOnJS(setCentro)(i);
      }
    },
  });
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
      <Reanimated.FlatList data={fila} horizontal showsHorizontalScrollIndicator={false}
        keyExtractor={(it) => (it.tipo === 'foto' ? it.foto.id : it.chave)}
        snapToInterval={item} decelerationRate="fast" contentContainerStyle={{ paddingHorizontal: lado }}
        initialScrollIndex={1}
        getItemLayout={(_, i) => ({ length: item, offset: item * i, index: i })}
        onScroll={aoRolar} testID="galeria"
        scrollEventThrottle={16}
        renderItem={({ item: it, index }) => (
          <Vitrine x={x} index={index} largura={item}>
            {it.tipo === 'foto' ? (
              <Quadro foto={it.foto} lado={item - 28} centro={index === centro} chave={`${visita}-${it.foto.id}`}
                aoTocar={() => setAberta(it.n)} aoSegurar={() => setOpcoes(it.foto)} />
            ) : <Totem tipo={it.tipo} chave={visita} />}
          </Vitrine>
        )} />

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

// Cada lugar da fila: a do centro reta e inteira; as vizinhas menores e com opacidade reduzida
function Vitrine({ x, index, largura, children }: { x: SharedValue<number>; index: number; largura: number; children: ReactNode }) {
  const estilo = useAnimatedStyle(() => {
    const faixa = [(index - 1) * largura, index * largura, (index + 1) * largura];
    return {
      opacity: interpolate(x.value, faixa, [0.5, 1, 0.5], Extrapolation.CLAMP),
      transform: [
        { scale: interpolate(x.value, faixa, [0.8, 1, 0.8], Extrapolation.CLAMP) },
      ],
    };
  });
  return <Reanimated.View style={[{ width: largura, alignItems: 'center', justifyContent: 'flex-end' }, estilo]}>{children}</Reanimated.View>;
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
          style={{ width: lado, height: lado, borderWidth: 1, borderColor: centro ? c.destaque : c.linha,
            borderRadius: 6, overflow: 'hidden', backgroundColor: c.superficie }}>
          <Image source={{ uri: enderecoDa(foto) }} className="w-full h-full" resizeMode="cover" />
        </Pressable>
      </Animated.View>
      <Pedestal altura={78}>
        <View className="items-center px-2 py-1" style={{ maxWidth: lado * 0.72 }}>
          <View className="flex-row items-center gap-1">
            {foto.tema ? <IconeTema id={idTemaDaFoto(foto)} tamanho={16} cor={c.tinta} /> : null}
            <Text className="shrink font-texto-forte text-tinta text-[12px]" numberOfLines={1}>{foto.achado}</Text>
          </View>
          <Text className="font-texto text-apagado text-[10px]">{foto.pontos ? <><Text className="font-numero">+{foto.pontos}</Text> · </> : null}{quando(foto.criado_em)}</Text>
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
      <Animated.View style={{ width: 76, height: 76, borderRadius: 6, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        backgroundColor: ouro ? c.superficie : c.suave, borderWidth: ouro ? 1 : 0, borderColor: c.destaque, marginBottom: 6,
        transform: [{ translateY: flutua.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0, -6, 0] }) }] }}>
        <Icone nome={ouro ? 'trofeu' : 'camera'} tamanho={42} cor={c.destaque} />
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
      <View className="w-[130px] h-[10px] rounded-ficha bg-linha" />
      <View style={{ width: 104, height: altura, backgroundColor: c.superficie, borderLeftWidth: 1, borderRightWidth: 1,
        borderColor: c.linha, alignItems: 'center', justifyContent: 'center' }}>
        {children}
      </View>
      <View className="w-[150px] h-[14px] rounded-ficha bg-linha" />
    </View>
  );
}

function TelaCheia({ fotos, inicio, aoFechar }: { fotos: FotoGaleria[]; inicio: number | null; aoFechar: () => void }) {
  const c = useCores();
  const { width, height } = useWindowDimensions();
  const topo = useSafeAreaInsets().top;
  return (
    <ModalTema visible={inicio !== null} transparent animationType="fade" onRequestClose={aoFechar}>
      <View style={{ flex: 1, backgroundColor: c.fundo }}>
        {inicio !== null ? (
          <FlatList data={fotos} horizontal pagingEnabled showsHorizontalScrollIndicator={false} initialScrollIndex={inicio}
            keyExtractor={(f) => f.id} getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
            renderItem={({ item: f }) => (
              <View style={{ width, height, justifyContent: 'center', gap: 12 }}>
                <Image source={{ uri: enderecoDa(f) }} style={{ width, height: height * 0.62 }} resizeMode="contain"
                  accessibilityLabel={`Foto: ${f.achado}`} />
                <Text className="font-titulo text-tinta text-center text-[20px]">{f.achado}</Text>
                <View className="flex-row items-center justify-center gap-2">
                  {f.tema ? <IconeTema id={idTemaDaFoto(f)} tamanho={18} cor={c.tinta} /> : null}
                  <Text className="font-texto text-apagado">{f.tema ? `${f.tema} · ` : ''}{f.pontos ? <><Text className="font-numero">+{f.pontos}</Text> pontos · </> : null}{quando(f.criado_em)}</Text>
                </View>
              </View>
            )} />
        ) : null}
        <Pressable accessibilityRole="button" accessibilityLabel="Fechar a foto" onPress={aoFechar}
          style={{ position: 'absolute', top: topo + 8, right: 12, width: 48, height: 48, alignItems: 'center', justifyContent: 'center' }}>
          <Icone nome="fechar" tamanho={28} cor={c.tinta} />
        </Pressable>
      </View>
    </ModalTema>
  );
}

function Opcoes({ foto, aoFechar }: { foto: FotoGaleria | null; aoFechar: () => void }) {
  const c = useCores();
  const baixo = useSafeAreaInsets().bottom;
  return (
    <ModalTema visible={!!foto} transparent animationType="slide" onRequestClose={aoFechar}>
      <Pressable accessibilityLabel="Fechar" onPress={aoFechar} style={{ flex: 1, backgroundColor: `${PALETA.escuro.fundo}66` }} />
      {foto ? (
        <View style={{ backgroundColor: c.fundo, borderTopLeftRadius: 6, borderTopRightRadius: 6, padding: 16, paddingBottom: baixo + 16, gap: 12 }}>
          <View className="flex-row items-center gap-2">
            {foto.tema ? <IconeTema id={idTemaDaFoto(foto)} tamanho={20} cor={c.tinta} /> : null}
            <Text accessibilityRole="header" className="font-titulo text-[20px] text-tinta">{foto.achado}</Text>
          </View>
          <CompartilharFoto foto={enderecoDa(foto)} enviada={enderecoDa(foto)} captura={foto.id} aceita={foto.pontos > 0} placa={foto} />
          <Botao titulo="Apagar da galeria" tipo="secundario" aoTocar={() => { apagarDaGaleria(foto.id); aoFechar(); }} />
        </View>
      ) : null}
    </ModalTema>
  );
}
