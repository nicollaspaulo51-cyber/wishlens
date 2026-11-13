# WishLens: app de celular (Expo / React Native)

O jogo como app nativo. A foto vai para o servidor do juiz (`../servidor`), que roda o CLIP e calcula os
pontos; o login é o mesmo Supabase do app web.

## Testar no celular (Expo Go)

1. Instale o **Expo Go** no celular (Play Store ou App Store).
2. Copie `.env.example` para `.env` e preencha:
   - `EXPO_PUBLIC_SERVIDOR_URL`: o endereço do Space (`https://<usuario>-<space>.hf.space`), ou o do seu
     computador na rede (`http://192.168.x.x:7860`) se o servidor estiver rodando nele.
   - `EXPO_PUBLIC_SUPABASE_URL` e `EXPO_PUBLIC_SUPABASE_KEY`: os mesmos dos Secrets do Streamlit (chave anon).
     Sem os dois, o app entra só com um apelido e o servidor guarda tudo em memória.
3. Rode e leia o QR code com o Expo Go (Android) ou com a câmera (iPhone):

```bash
npm install
npx expo start --tunnel
```

## Conferir

```bash
npx tsc --noEmit
npx expo-doctor
npx expo start --web
```

A versão web serve só para ver as telas: sem mapa nativo, e a câmera depende do navegador.

## Estrutura

```
src/app/            telas (Expo Router): entrar, câmera e as abas Jogar, Pódio e Coleção
src/componentes/    cartão de pontos, painel do dia, mapa (nativo e web), peças de interface
src/lib/            api (servidor do juiz), sessão (Supabase), cores, useDados
```
