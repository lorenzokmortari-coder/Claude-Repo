# Fred · legenda palavra a palavra, v2 (14/10/2026)

`legenda_reels.py` recebe um vídeo vertical 9:16 em português e devolve o mesmo vídeo com a legenda queimada no estilo reels:
- 2 a 3 palavras por vez;
- a palavra falada destacada em cor e com um leve zoom;
- Arial Black grande, com contorno.

Na v2, a transcrição passa por uma **revisão obrigatória** antes de queimar.

```
vídeo -> revisar: áudio pelo ffmpeg -> faster-whisper (medium, int8, CPU) -> video.palavras.json + video.revisar.txt
      -> [você corrige as palavras duvidosas e marca "revisado": true]
      -> queimar: blocos de 2 a 3 palavras -> .ass -> ffmpeg (libass + x264) -> video_legendado.mp4
```

## Instalar (Windows)

```
pip install faster-whisper "av<16"
```

- O ffmpeg tem de estar no PATH (build do gyan.dev).
- O `"av<16"` evita o defeito do PyAV novo com o faster-whisper 1.2.1. A v2 já não depende disso, porque decodifica o áudio pelo ffmpeg, mas fixar a versão não custa.
- Na primeira vez, o faster-whisper baixa o modelo `medium` do HuggingFace e guarda no cache. Depois roda sem internet.

## Usar: dois passos

```
python legenda_reels.py revisar video.mp4 --termos "Cheetos, Miojo, pappardelle"
```

Esse passo grava dois arquivos:
- **`video.palavras.json`:** com `"revisado": false`;
- **`video.revisar.txt`:** só as palavras com prob abaixo de 0,5, com tempo e as palavras em volta. Por exemplo:
  ```
  tempo      prob  palavra            contexto
  00:00.57   0.31  chitos             Comprei um ⟦chitos⟧ no mercado.
  ```

Abra o `palavras.json`, ache cada palavra pelo `"inicio"`, corrija o `"texto"` e troque `"revisado": false` por `"revisado": true`. Leva uns 2 minutos. Corrigir qualquer palavra também conta como revisão.

Depois:

```
python legenda_reels.py queimar video.mp4 --prints 3
python legenda_reels.py queimar video.mp4 --prints 3 --guia      # PNG extras com a área segura pintada
```

- **Sem revisão, o `queimar` recusa.** Para pular de propósito, use `--sem-revisar`, que queima e avisa quantas palavras duvidosas ficaram sem conferir.
- **Sem "revisar" ou "queimar" na frente,** vale "queimar". Sem `palavras.json`, ele faz a revisão e para.

## Opções

| Opção | Padrão | O que faz |
|---|---|---|
| `--termos "A, B, C"` / `--termos-arquivo roteiro.txt` | | Marcas, nomes e bordões do roteiro. Vão no `initial_prompt` e nos `hotwords` do faster-whisper. A dica de fala coloquial ("tá, tô, pra, né, o que que") vai sempre |
| `--modelo` | `medium` | Modelo do faster-whisper. "medium" e "small" viram o id do HuggingFace, então uma pasta local com esse nome não atrapalha. Uma pasta com `model.bin` também serve |
| `--limiar` | `0.5` | Prob abaixo disto vai para o `revisar.txt` |
| `--zona organico/anuncio` | `organico` | Área segura: base de 25% (orgânico, validado no PC) ou de 35% (anúncio, orientação da Meta). Ver `area-segura.md` |
| `--posicao` | `0.62` | Centro vertical da legenda, em fração da altura |
| `--tamanho` | 5,8% da altura (111 px em 1920) | Tamanho da fonte em px |
| `--palavras-por-bloco`, `--max-caracteres` | `2-3`, `16` | Tamanho do bloco |
| `--fonte`, `--pasta-fontes`, `--cor`, `--destaque` | Arial Black, `#FFFFFF`, `#FFE14D` | Fonte e cores (as mesmas da v1) |
| `--sem-legenda 0:12-0:15` | | Trechos sem legenda |
| `--prints N`, `--guia` | | N quadros em PNG; `--guia` faz PNG extras com a área segura pintada. O MP4 fica limpo |
| `--sem-aviso-legenda` | | Não procura legenda já queimada no vídeo |
| `--palavras ARQ.json` | | Transcrição de outra fonte (conta como revisada) |

## O que a v2 corrige (cada item tem teste em `test_legenda_reels.py`)

1. **PyAV 16+ quebrava o faster-whisper 1.2.1**, com o erro "open() got an unexpected keyword argument 'metadata_errors'". O áudio agora vem do ffmpeg, em float32 mono 16 kHz, e entra como array: o PyAV não é chamado.
2. **`--guia` queimava as caixas vermelhas no MP4.** Agora vão só em `<video>_legendado_guia_N.png`.
3. **`largura_letra` 0,72 estava errada para o libass.** O Fontsize do libass é ascendente + descendente, e a maiúscula ocupa cerca de 0,49 dele. Passou a 0,50, e o espaço conta meia letra. Bloco de até 16 caracteres cabe numa linha.
4. **Número partido pelo Whisper** ("5" ",45,") volta a ser um só, e hora vira "5H45". Preço ("5,45", "R$ 5,45", "5,45 reais") fica como está.
5. **Pasta local chamada `medium` ou `small`** era lida como modelo ("Unable to open file 'model.bin'"). O nome agora vira o id do HuggingFace.
6. **Base de 35% travava a legenda grande em cerca de 59% da altura.** No orgânico, a base é 25% e a legenda fica em 62%.
7. **Palavra com duração zero, ou com o mesmo início da seguinte, nunca acendia.** Agora cada palavra tem pelo menos 0,08 s de destaque; se não couber, o tempo do bloco é repartido.

**Ajustes validados no PC (estilo "B"):**
- modelo medium;
- `--termos`;
- fala coloquial mantida;
- tamanho de 5,8%;
- blocos de 2 a 3 palavras com até 16 caracteres;
- posição 0,62 com base de 0,25;
- fonte e cores mantidas.

## Aviso de legenda já queimada

No `revisar` (e no `queimar` sem `palavras.json`), o script olha 6 quadros e procura texto claro com contorno escuro entre 40% e 92% da altura, no mesmo lugar em vários quadros. Se achar, **avisa e não bloqueia**: as duas legendas juntas poluem a tela, então o melhor é usar o vídeo bruto.

É heurística:
- placa, prateleira ou camiseta escrita podem acusar;
- legenda fina, sem contorno, pode passar.

## Testes

```
python -m pytest -q test_legenda_reels.py     # 29 testes; a ponta a ponta precisa de ffmpeg
```

Sem espeak-ng, o `gerar_teste.py` faz o vídeo de teste com bipes no lugar da voz. O gabarito de tempo continua exato, e o teste da legenda usa um modelo falso.

Rodados contra a v1, 22 desses testes falham. A tabela está em `testes-antes-depois.md`.

## Limitações

- **Whisper de verdade:** não rodou aqui, porque o HuggingFace está bloqueado nesta nuvem. A chamada foi conferida contra o faster-whisper 1.2.1 instalado, e o defeito do PyAV 19 foi reproduzido aqui. Os números de acerto (93 a 95% no limpo, 84 a 88% no ruidoso com termos) são os medidos no PC em 14/10/2026.
- **Largura da Arial Black:** a medida de 0,49 é a do PC. Aqui só há Inter Display Black. Com outra fonte, ajuste `--tamanho`.
- **Área segura:** a lateral direita (botões) não tem número oficial. Ver `area-segura.md`.
