// Avisar um problema (suporte): o juiz errou, o app travou ou outra coisa. Vai para o arquivo de avisos do juiz.
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Apagado, Botao, Fichas, Titulo } from '../componentes/ui';
import { api, type TipoAviso } from '../lib/api';
import { useCores } from '../lib/cores';

const TIPOS: { valor: TipoAviso; texto: string; dica: string }[] = [
  { valor: 'juiz', texto: 'O juiz errou', dica: 'Ex.: era um fone de ouvido e o juiz disse mouse.' },
  { valor: 'app', texto: 'O app travou', dica: 'Ex.: o mapa ficou sem ícones depois que tirei a foto.' },
  { valor: 'outro', texto: 'Outra coisa', dica: 'Conte o que aconteceu ou o que poderia melhorar.' },
];

export default function Avisar() {
  const c = useCores();
  const p = useLocalSearchParams<{ tipo?: TipoAviso; captura?: string; achado?: string }>();
  const [tipo, setTipo] = useState<TipoAviso>(p.tipo ?? 'juiz');
  const [texto, setTexto] = useState(p.achado ? `O juiz disse "${p.achado}", mas era ` : '');
  const [enviando, setEnviando] = useState(false);
  const [msg, setMsg] = useState<{ texto: string; erro: boolean } | null>(null);
  const dica = TIPOS.find((t) => t.valor === tipo)!.dica;

  async function enviar() {
    setEnviando(true);
    setMsg(null);
    try {
      await api.avisar(tipo, texto.trim(), p.captura);
      setMsg({ texto: 'Aviso enviado. Obrigado: ele vai ser lido e corrigido.', erro: false });
      setTimeout(() => router.back(), 1500);
    } catch (e) {
      setMsg({ texto: e instanceof Error ? e.message : 'Não deu para enviar. Tente de novo.', erro: true });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'bottom']} className="flex-1 bg-papel">
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
          <Titulo>Avisar um problema</Titulo>
          <Fichas<TipoAviso> rotulo="Tipo de problema" valor={tipo} aoEscolher={setTipo}
            opcoes={TIPOS.map(({ valor, texto: t }) => ({ valor, texto: t }))} />
          <View className="gap-[6px]">
            <TextInput value={texto} onChangeText={setTexto} multiline maxLength={500} placeholder={dica}
              placeholderTextColor={c.apagado} accessibilityLabel="O que aconteceu"
              style={{ minHeight: 140, textAlignVertical: 'top', borderWidth: 1.5, borderColor: c.linha, borderRadius: 14,
                padding: 14, fontSize: 16, lineHeight: 22, color: c.tinta, backgroundColor: c.superficie }} />
            <Apagado estilo={{ fontSize: 12, alignSelf: 'flex-end' }}>{texto.length}/500</Apagado>
          </View>
          <Apagado>
            Vai junto: seu apelido, o que você escreveu{p.captura ? ' e o que o juiz disse desta foto' : ''}.
            A foto e a sua localização não vão.
          </Apagado>
          {msg ? (
            <Text className="font-texto" accessibilityLiveRegion="polite" style={{ color: msg.erro ? c.recusa : c.destaque, fontSize: 15 }}>{msg.texto}</Text>
          ) : null}
          <Botao titulo="Enviar aviso" aoTocar={enviar} carregando={enviando} desativado={texto.trim().length < 3} />
          <Botao titulo="Cancelar" tipo="secundario" aoTocar={() => router.back()} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
