# Para a 00 · tarefa 23 · Nuvem · Fred · legenda v2

**O que é:** a v2 do `legenda_reels.py`:
- os 7 defeitos corrigidos, entre eles o PyAV 19 que quebrava o faster-whisper 1.2.1 (reproduzido aqui);
- os ajustes do estilo "B" como padrão;
- revisão obrigatória em dois passos (`revisar` → `queimar`);
- aviso de legenda já queimada e `--zona organico|anuncio`.

São 29 testes: 22 falham na v1, e os 29 passam na v2.

**Status:** completo. O Whisper de verdade não rodou aqui (o HuggingFace está bloqueado), e não há vídeo real: o exemplo é sintético. A lateral direita da área segura segue não verificada.

**Comandos (Windows, na pasta da v2):**
```
pip install faster-whisper "av<16" pytest
python -m pytest -q test_legenda_reels.py
python legenda_reels.py revisar video.mp4 --termos "marca, nome, bordao"
# corrigir video.palavras.json, "revisado": true
python legenda_reels.py queimar video.mp4 --prints 3 --guia
```

**Dona:** 31 · Fred · Conteúdo.

**Prioridade:** 1. A v1 não roda com o PyAV novo e destrói piada no ruído; a v2 corrige os dois.

**Decidir:** confirmar a faixa direita no gabarito oficial da Meta ("Reels safe zone checker").

**Só com dado real:** rodar de novo os 2 vídeos de 14/10:
- o acerto com o medium e os termos;
- se o aviso acusa o de 26 s (que já tem legenda);
- se a quebra de linha com a Arial Black bate.
