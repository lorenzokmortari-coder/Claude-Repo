# Fred · legenda palavra a palavra

`legenda_reels.py` recebe um vídeo vertical 9:16 em português e devolve o mesmo vídeo com a legenda
queimada no estilo reels. Aparecem 2 a 4 palavras por vez, a palavra falada fica destacada em cor
e com um leve zoom, a fonte é grande com contorno e sombra, e tudo fica dentro da área segura do
Instagram. Roda local, sem serviço pago:

```
vídeo -> faster-whisper (small, int8, CPU, tempo de cada palavra) -> <video>.palavras.json
      -> blocos de 2 a 4 palavras -> legenda .ass -> ffmpeg (libass + x264) -> <video>_legendado.mp4
```

## Como usar no PC (Windows)

```bash
pip install faster-whisper            # o ffmpeg precisa estar no PATH (build do gyan.dev)
python legenda_reels.py video.mp4                       # cria video.palavras.json, video_legendado.ass e .mp4
# corrija alguma palavra em video.palavras.json, se quiser, e rode de novo: a transcrição salva é reaproveitada
python legenda_reels.py video.mp4 --sem-legenda 0:12-0:15,1:02-1:05.5
python legenda_reels.py video.mp4 --prints 3 --guia     # 3 PNG de quadros e a área segura pintada (conferência)
```

Na primeira vez, o faster-whisper baixa o modelo `small` do HuggingFace (algumas centenas de MB) e
guarda no cache. Depois roda sem internet.

| Opção | Padrão | O que faz |
|---|---|---|
| `--palavras ARQ.json` | | usa uma transcrição pronta, no mesmo formato do `palavras.json` |
| `--retranscrever` | | ignora o `palavras.json` salvo |
| `--modelo`, `--pasta-modelo` | `small` | modelo do faster-whisper e onde guardá-lo |
| `--sem-legenda` | | trechos sem legenda, como `0:12-0:15,1:02-1:05.5` (segundos, m:ss ou h:mm:ss) |
| `--fonte`, `--pasta-fontes` | `Arial Black` | fonte (a padrão vem no Windows); `--pasta-fontes` aponta para .ttf/.otf baixados, como Montserrat ExtraBold |
| `--tamanho` | 4,5% da altura (86 px em 1920) | tamanho da fonte em px |
| `--cor`, `--destaque` | `#FFFFFF`, `#FFE14D` | cor do texto e da palavra falada |
| `--posicao` | `0.58` | centro vertical da legenda, em fração da altura; fica sempre dentro da área segura |
| `--caixa alta/normal` | `alta` | maiúsculas ou o texto como foi falado |
| `--sem-zoom` | | tira o zoom de 112% da palavra falada |
| `--palavras-por-bloco` | `2-4` | mínimo e máximo de palavras por vez |
| `--so-ass` | | só gera o `.ass`, para abrir no Aegisub |
| `--prints N`, `--guia` | | salva N quadros PNG; `--guia` pinta o que fica fora da área segura |
| `--crf` | `18` | qualidade do x264; o áudio é copiado e só é recodificado em AAC se o MP4 não aceitar |

## Como a legenda é montada

- **Blocos:** o texto é cortado em frases (ponto final, exclamação, interrogação ou pausa maior que
  0,6 s). Cada frase é dividida pela partição de menor custo. O ideal é 3 palavras; quebrar em vírgula
  ou numa pausa é bom; terminar um bloco em artigo ou preposição ("de", "às", "em") no meio da frase é
  ruim; nenhum bloco passa de 4 palavras nem de 22 caracteres. "A reunião de hoje começa às nove em
  ponto." vira 2 + 3 + 4 palavras, sem um "PONTO." sozinho no fim.
- **Destaque:** cada palavra ganha um evento próprio no `.ass`, com o bloco inteiro e só ela em cor de
  destaque e com zoom. A palavra continua destacada até a próxima começar, e o bloco fica 0,25 s na
  tela depois da última palavra, sem invadir o próximo.
- **Quebra de linha:** quando o bloco não cabe numa linha, o código decide onde quebrar (a divisão mais
  equilibrada) e põe a mesma quebra em todos os eventos do bloco. Assim o texto não pula de lugar
  quando o zoom passa de uma palavra para outra.
- **Área segura:** a padrão é 14% em cima, 35% embaixo e 6% de cada lado, mais 6% à direita por causa
  dos botões do Reels. A legenda fica centrada em 58% da altura. É a regra prática que circula para
  anúncios em Reels; **não conferi** na página da Meta nesta sessão (a cota de buscas acabou). Os
  valores ficam no começo do arquivo, na classe `Estilo`.
- **Vídeo de celular:** se o arquivo vem deitado com a marca de rotação, o tamanho da legenda segue o
  quadro já girado. O teste confere isso.

## Teste com vídeo sintético

`gerar_teste.py` cria um vídeo 9:16 com fundo em degradê e uma voz sintética (espeak-ng, pt-br), mais
o gabarito com o tempo exato de cada palavra. Cada palavra é sintetizada sozinha e colada com pausas
conhecidas, então o tempo é exato até a amostra. A voz sai robótica.

```bash
python gerar_teste.py --saida teste.mp4                    # teste.mp4 + teste.gabarito.json
python legenda_reels.py teste.mp4 --palavras teste.gabarito.json --prints 3     # sem Whisper
python legenda_reels.py teste.mp4 --retranscrever                                # com o Whisper (no PC)
python gerar_teste.py --comparar teste.palavras.json teste.gabarito.json         # acerto e erro de tempo
python -m pytest -q                                                              # 10 testes
```

Os 10 testes cobrem cores, tempos, trechos sem legenda, os blocos, a quebra de linha, o `.ass` (um
destaque por evento, o mesmo texto em todo o bloco, nada sobreposto, posição dentro da área segura e
chaves que nunca viram tag), os argumentos passados ao faster-whisper (com um modelo falso) e o
comparador com o gabarito. A ponta a ponta gera o vídeo sintético, legenda e confere tamanho, duração,
áudio e os 3 prints. Ela também confere pixel a pixel que há legenda quando há fala e nenhuma no
trecho marcado sem legenda, e que a segunda rodada reaproveita o `palavras.json`. O último teste é o
vídeo de celular com rotação.

Os `print_1.png` a `print_3.png` são quadros do `exemplo_legendado.mp4` (1080x1920, 13,4 s), com a
fonte Inter Display Black, que é a pesada disponível nesta máquina. No Windows a padrão é Arial Black.
`print_guia_area_segura.png` mostra a mesma legenda com `--guia`. Aqui, legendar o vídeo e tirar os 3
prints levou cerca de 13 s (4 núcleos, x264 preset medium).

## Limitações e o que não deu para verificar

- **O faster-whisper não rodou de verdade aqui.** O modelo vem do HuggingFace, que a rede desta nuvem
  bloqueia (o download deu 403 no proxy). A chamada foi conferida contra a assinatura do faster-whisper
  1.2.1 e testada com um modelo falso; a legenda foi testada com o gabarito exato. No PC, rode o teste
  com `--retranscrever` e o `--comparar` para medir o acerto e o erro de tempo do Whisper.
- O tempo por palavra do Whisper costuma errar por algumas dezenas a centenas de milissegundos e piora
  com música alta. Por isso o `palavras.json` fica salvo para correção.
- A área segura é a regra prática citada acima, não conferida na fonte oficial.
- A largura média de letra (`largura_letra = 0,72`) é uma estimativa para fontes pesadas. Com uma fonte
  bem mais larga ou mais estreita, ajuste o tamanho ou esse valor para a quebra de linha ficar boa.
- Queimar a legenda recodifica o vídeo (x264, CRF 18). A perda é pequena, mas existe.
