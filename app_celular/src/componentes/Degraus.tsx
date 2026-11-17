// Os três degraus do pódio (o 1º no meio), usados no Pódio e no placar dos amigos.
import { type ReactNode } from 'react';
import { Animated, Text, View } from 'react-native';

import { type LinhaPodio } from '../lib/api';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { useEntrada } from '../lib/movimento';
import { Holografico as Brilho } from './efeitos/Holografico';
import { Icone } from './icones/Icone';

// ouro, prata e bronze em tinta: legíveis no papel claro e no escuro
const MEDALHAS = { 1: '#D19A00', 2: '#8E9AA3', 3: '#B8692E' } as const;

export function Degraus({ ranking, chave }: { ranking: LinhaPodio[]; chave: string }) {
  const c = useCores();
  const alturas = { 1: 96, 2: 70, 3: 52 } as const;
  return (
    <View className="flex-row items-end gap-[8px] mt-[8px]">
      {([2, 1, 3] as const).map((pos) => {
        const r = ranking.find((x) => x.posicao === pos);
        return (
          <Degrau key={pos} pos={pos} chave={chave} altura={alturas[pos]}
            rotulo={r ? `${pos}º lugar: ${r.apelido}, ${r.pontos} pontos` : `${pos}º lugar vazio`}>
            {r ? (
              <>
                <Icone nome="medalha" tamanho={34} cor={MEDALHAS[pos]} traco={2.2} ativo />
                <Text className="font-texto-forte text-tinta text-[15px]" numberOfLines={1} >{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text className="font-texto text-apagado text-[13px]" >{r.pontos} pts</Text>
              </>
            ) : null}
          </Degrau>
        );
      })}
    </View>
  );
}

// Um degrau sobe do chão (o 3º primeiro, o 1º por último) e a medalha cai em cima dele
function Degrau({ pos, chave, altura, rotulo, children }: { pos: 1 | 2 | 3; chave: string; altura: number; rotulo: string; children: ReactNode }) {
  const c = useCores();
  const sobe = useEntrada({ 3: 0, 2: 150, 1: 300 }[pos], chave);
  const cai = useEntrada({ 3: 250, 2: 400, 1: 550 }[pos], chave);
  return (
    <View className="flex-1 items-center gap-[4px]" accessible accessibilityLabel={rotulo}>
      <Animated.View style={{ alignItems: 'center', gap: 4, opacity: cai,
        transform: [{ translateY: cai.interpolate({ inputRange: [0, 1], outputRange: [-24, 0] }) }] }}>
        {children}
      </Animated.View>
      <Animated.View style={{ alignSelf: 'stretch', height: altura, borderTopLeftRadius: 10, borderTopRightRadius: 10,
        backgroundColor: pos === 1 ? c.sol : c.suave, alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        transformOrigin: 'bottom', transform: [{ scaleY: sobe }] }}>
        <Text style={{ fontFamily: FONTE_TITULO, fontSize: 26, color: pos === 1 ? c.solTinta : c.tinta }}>{pos}</Text>
        {pos === 1 ? <Brilho pausa={4000} /> : null}
      </Animated.View>
    </View>
  );
}
