// Componentes de fora do React Native que recebem className do NativeWind (os do RN já recebem sozinhos)
import { CameraView } from 'expo-camera';
import { cssInterop } from 'nativewind';
import { SafeAreaView } from 'react-native-safe-area-context';

cssInterop(SafeAreaView, { className: 'style' });
cssInterop(CameraView, { className: 'style' });
