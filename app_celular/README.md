# WishLens: app de celular (Expo / React Native)

O app envia a foto ao servidor do juiz (`../servidor`), que avalia o achado e calcula os pontos. O login usa o Supabase.

## Identidade visual

A interface segue a identidade de mapa topográfico sóbrio: neutros frios de pedra e laranja de sinalização de trilha como única cor de destaque da interface. O texto usa Overpass, e os números usam Overpass Mono.

Cartões e controles retangulares usam cantos de 6 px e borda de 1 px, sem sombra. Os ícones da interface são de traço próprio. Nas telas, as curvas de nível aparecem só no topo da aba **Jogar**.

Para regenerar os ícones do app em `assets/`, rode `python scripts/gerar_icones.py` na raiz do repositório, com Pillow instalado.

## Testar no celular (Expo Go)

1. Instale o **Expo Go** no celular (Play Store ou App Store).
2. Copie `.env.example` para `.env` e preencha:
   - `EXPO_PUBLIC_SERVIDOR_URL`: a URL do servidor do juiz, acessível pelo celular.
   - `EXPO_PUBLIC_SUPABASE_URL` e `EXPO_PUBLIC_SUPABASE_KEY`: a URL e a chave pública do seu projeto Supabase.
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
