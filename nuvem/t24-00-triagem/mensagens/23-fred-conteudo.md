Para 31 · Fred · Conteúdo · entrega 23 · prioridade 1

Artifact: "Nuvem · Fred · legenda v2" https://claude.ai/artifact/VXAfSfQDBKY6u5ScCMP5hR
A v2 está inteira em `v2/`. O `aplicar/fred-legenda.diff` da triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT, aplicado sobre a v1, dá o mesmo resultado.

Na pasta da v1:
```
patch -p1 < <t24>/aplicar/fred-legenda.diff
pip install faster-whisper "av<16" pytest
python -m pytest -q test_legenda_reels.py   # 28 ok + 1 pulado com av<16
python legenda_reels.py revisar video.mp4 --termos "marca, nome, bordão"
# corrigir video.palavras.json e marcar "revisado": true
python legenda_reels.py queimar video.mp4 --prints 3 --guia
```

**Os 7 defeitos corrigidos:**
- PyAV 19;
- guia queimado no MP4;
- largura da letra (0,50);
- número partido;
- pasta chamada `medium`;
- base 0,25;
- palavra sem duração.

O padrão agora é o estilo B, e a revisão é obrigatória.

**Decidir:** conferir a faixa direita no "Reels safe zone checker" da Meta.

**Só com dado real:** rodar de novo os 2 vídeos de 14/10 e conferir:
- o acerto com o medium e os termos;
- o aviso de legenda queimada no vídeo de 26 s;
- a quebra de linha com a Arial Black.
