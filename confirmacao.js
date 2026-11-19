const fragmento = new URLSearchParams(window.location.hash.slice(1));
const consulta = new URLSearchParams(window.location.search);

// O Supabase pode devolver dados da sessão no fragmento da URL. A página não usa a sessão.
if (window.location.hash || window.location.search) {
  window.history.replaceState(null, '', window.location.pathname);
}

const titulo = document.querySelector('h1');
const mensagem = document.querySelector('#mensagem');

if (fragmento.has('error') || fragmento.has('error_code') || consulta.has('error') || consulta.has('error_code')) {
  titulo.textContent = 'Link de confirmação indisponível';
  mensagem.textContent = 'O link pode ter expirado ou já ter sido usado. Se você já confirmou seu e-mail, volte ao WishLens e tente entrar.';
} else if (fragmento.has('access_token') && ['signup', 'email'].includes(fragmento.get('type'))) {
  titulo.textContent = 'E-mail confirmado';
  mensagem.textContent = 'Volte ao WishLens no Expo Go e entre com seu e-mail e sua senha.';
}
