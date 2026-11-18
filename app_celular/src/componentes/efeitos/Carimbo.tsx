// Selo reto do resultado do juiz ("aceita" / "recusada"), na cor recebida. O celular vibra quando o selo aparece.
import * as Haptics from 'expo-haptics';
import { useEffect } from 'react';
import { Text, View } from 'react-native';

export function Carimbo({ aceita, cor }: { aceita: boolean; cor: string }) {
  const texto = aceita ? 'aceita' : 'recusada';
  useEffect(() => {
    Haptics.impactAsync(aceita ? Haptics.ImpactFeedbackStyle.Heavy : Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  }, [aceita]);
  return (
    <View pointerEvents="none" accessible accessibilityLabel={`Resultado: ${texto}`}
      className="py-1">
      <Text className="font-texto-forte text-xs uppercase" style={{ color: cor }}>{texto}</Text>
    </View>
  );
}
