# Área segura do Reels: o que é oficial e o critério da v2 (14/10/2026)

## O que a Meta publica (oficial, para anúncio)

- **Ficha "Awareness Image Ad Specs on Instagram Reels"** do Ads Guide:
  > "Consider leaving roughly 14% of the top, 35% of the bottom, and 6% on each side of your asset free from text, logos, or other key creative elements"
  - **Como foi lida:** o mesmo trecho apareceu idêntico em 3 buscas, mas a página (facebook.com) estava bloqueada nesta rede e não abriu.
  - **Escopo:** é de **anúncio** e da ficha de **imagem**. Não confirmei se a ficha de vídeo traz o mesmo texto.
- **Em 1080×1920** (conta minha): topo de cerca de 269 px, base de 672 px e 65 px de cada lado.
- **Gabarito oficial:** a Meta oferece o "Reels safe zone checker" (ppt, psd, keynote) na página de anúncios em Reels. Não consegui baixar.

## O que NÃO é oficial (não verificado)

- **Reels orgânico:** não achei orientação de área segura do Instagram (help.instagram.com só traz proporção, FPS e resolução).
- **A coluna de botões à direita** (curtir, comentar, compartilhar): a Meta só diz "6% on each side". Fontes não oficiais citam de 120 px a cerca de 230 px (21% da largura). **Não verificado.**

## O critério da v2

| Zona | Topo | Base | Lados | Extra à direita | Origem |
|---|---|---|---|---|---|
| `organico` (padrão) | 14% | **25%** | 6% | 6% | Topo e lados da Meta. A base de 25% e a posição em 62% da altura são o que o teste do PC com dois vídeos reais validou em 14/10/2026 ("não cobre rosto nem botões"), sem número oficial para orgânico |
| `anuncio` (`--zona anuncio`) | 14% | **35%** | 6% | 6% | A orientação oficial da Meta para anúncio em Reels. A base maior protege o botão de chamada do anúncio |

**A faixa extra de 6% à direita** (cerca de 65 px, que somados aos 6% dão cerca de 130 px) é da casa. Fica dentro da faixa das fontes não oficiais (120 a 230 px) e passou no teste do PC. Para fechar o número, abra o gabarito oficial numa rede sem bloqueio a facebook.com.

**O `--guia`** pinta essas faixas num PNG à parte (`<video>_legendado_guia_N.png`), para conferir no olho, e nunca mais no MP4.
