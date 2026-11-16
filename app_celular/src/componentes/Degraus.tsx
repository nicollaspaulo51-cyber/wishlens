// Os três degraus do pódio (o 1º no meio), usados no Pódio e no placar dos amigos.
import { type ReactNode } from 'react';
import { Animated, Text, View } from 'react-native';

import { type LinhaPodio } from '../lib/api';
import { FONTE_TITULO, useCores } from '../lib/cores';
import { Brilho, useEntrada } from '../lib/movimento';

export function Degraus({ ranking, chave }: { ranking: LinhaPodio[]; chave: string }) {
  const c = useCores();
  const alturas = { 1: 96, 2: 70, 3: 52 } as const;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: 8 }}>
      {([2, 1, 3] as const).map((pos) => {
        const r = ranking.find((x) => x.posicao === pos);
        return (
          <Degrau key={pos} pos={pos} chave={chave} altura={alturas[pos]}
            rotulo={r ? `${pos}º lugar: ${r.apelido}, ${r.pontos} pontos` : `${pos}º lugar vazio`}>
            {r ? (
              <>
                <Text style={{ fontSize: 26 }}>{pos === 1 ? '🥇' : pos === 2 ? '🥈' : '🥉'}</Text>
                <Text numberOfLines={1} style={{ color: c.tinta, fontWeight: '700', fontSize: 15 }}>{r.apelido}{r.voce ? ' (você)' : ''}</Text>
                <Text style={{ color: c.apagado, fontSize: 13 }}>{r.pontos} pts</Text>
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
    <View style={{ flex: 1, alignItems: 'center', gap: 4 }} accessible accessibilityLabel={rotulo}>
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
