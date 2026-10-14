# Fred · pasta vigiada de vídeo (14/10/2026)

`vigia/vigia.py` vigia uma pasta no Windows e leva cada vídeo bruto até a legenda queimada pela legenda v2. A revisão humana fica no meio, obrigatória. É Python sem serviço pago. Roda sob demanda ou pelo Agendador de Tarefas.

```
D:\Fred\video\
  entrada\            você põe o bruto aqui; o vigia só lê (nunca apaga, move nem regrava)
  revisao\<nome>\     <nome>.palavras.json, <nome>.revisar.txt, <nome>_previa_1..3.png,
                      publi-checklist.rascunho.md (só com "publi" no nome) e o <nome>.ok que VOCÊ cria
  saida\              <nome>_legendado.mp4 e 3 prints, depois do .ok
  .vigia\             vigia.log, estado.json e a trava
```

## O ciclo de um vídeo

1. **Você copia** `corte.mp4` para `entrada\`. O vigia espera o tamanho e a data ficarem parados por 10 s e o arquivo abrir para leitura. Arquivo ainda copiando fica para a próxima rodada. `.crdownload`, `.part`, `.tmp` e `~$` são ignorados.
2. **O vigia roda o passo `revisar` da v2.** Os arquivos vão para `revisao\corte\`:
   - `corte.revisar.txt`: só as palavras com prob abaixo de 0,5, com tempo e contexto, e o aviso de legenda já queimada pela edição, se houver;
   - `corte.palavras.json`;
   - 3 prévias: quadros do bruto com a legenda ainda sem revisão desenhada por cima, para ver posição e tamanho. O vídeo não é tocado.
3. **Você corrige** o `"texto"` das palavras erradas no `palavras.json` (uns 2 minutos) e cria na mesma pasta um arquivo vazio `corte.ok`. Pelo Explorer: botão direito → Novo → Documento de texto, renomeado para `corte.ok`, sem `.txt`.
4. **A rodada seguinte queima** com o mesmo estilo da v2 (Arial Black, destaque #FFE14D, 62% da altura, área segura orgânica) e põe `corte_legendado.mp4` e 3 prints em `saida\`.

Regras do ciclo:
- **O vigia nunca queima sem o `.ok`.** Não existe opção para pular a revisão.
- **Mexeu no `palavras.json` depois do `.ok`?** O vigia não queima a versão nova até você criar o `.ok` de novo. Ele só queima a versão que o `.ok` marcou, para não queimar no meio de uma edição.
- **Queimou e você corrigiu de novo:** recrie o `.ok`. Ele queima outra vez, por cima da saída anterior.
- **Bruto trocado** (mesmo nome, outro arquivo) depois da revisão: o vigia para, não queima e explica no log. Dê outro nome ao vídeo ou apague `revisao\<nome>\` para recomeçar.

## Publi

Se o nome do arquivo tiver a palavra `publi` (`publi_marca_2026-10-20.mp4`, `corte_publi.mov`, mas não "republica"), o vigia grava `publi-checklist.rascunho.md` com os 10 itens do "Nuvem · Fred · publi sem risco":
- todos em aberto `[ ]`, com espaço para o OK do dono;
- a marca tirada do nome do arquivo;
- dicas tiradas da transcrição, com tempo: aposta/bet, rendimento e juros, crédito, "garantido", presente.

**É rascunho.** O vigia não marca item nenhum e não publica. Dica ausente não quer dizer item ok.

## Instalar (Windows)

1. Python 3.10+ do python.org, com "Add python.exe to PATH" marcado.
2. `pip install faster-whisper "av<16" pytest`
3. ffmpeg no PATH (build do gyan.dev, pasta `bin`).
4. Copie a pasta `vigia\` para o PC. Ela já traz a legenda v2 inteira e sem mudança: `legenda_reels.py`, `gerar_teste.py` e os testes, com o mesmo sha256 do artifact "Nuvem · Fred · legenda v2".
5. Teste: `python -m pytest -q` dentro de `vigia\`. São 43 testes (14 do vigia e 29 da v2) e precisam do ffmpeg.

## Usar

```
python vigia.py --raiz D:\Fred\video --uma-vez        # uma rodada (padrão)
python vigia.py --raiz D:\Fred\video --status         # em que pé está cada vídeo
python vigia.py --raiz D:\Fred\video --intervalo 60   # fica vigiando numa janela aberta
python vigia.py --raiz D:\Fred\video --termos "Marca, Bordão" --zona anuncio
```

- **`rodar-agora.cmd`:** uma rodada mais o status, com duplo clique. Troque a linha `RAIZ`.
- **`instalar-agendador.cmd`:** cria a tarefa "Vigia de video", a cada 5 minutos, com `pythonw`, sem janela. Troque a linha `RAIZ`.
  - Para remover: `schtasks /Delete /TN "Vigia de video" /F`.
  - Se uma rodada ainda estiver transcrevendo quando a próxima começar, a trava (`.vigia\trava`) faz a segunda sair sem fazer nada.
  - Trava com mais de 6 h é de uma rodada que morreu e é tomada.
- **Termos do roteiro:** `--termos` ou `--termos-arquivo` valem para todos os vídeos. Um `corte.termos.txt` ao lado do vídeo, em `entrada\`, vale só para ele.
- **Tempo:** com o medium em CPU, a transcrição leva cerca de 1,4× a duração do vídeo, e a queima de 20 a 30 s (números do PC na v2).

## O que o vigia nunca faz (cada item tem teste)

- **Publicar:** não há código de rede. O teste bloqueia o `socket.connect` e roda o ciclo inteiro.
- **Cortar silêncio:** a saída tem a mesma duração do bruto (±0,15 s), e nenhum comando ffmpeg leva `silenceremove`, `atrim`, `trim=`, `-t` ou `-to`.
- **Apagar ou mover o bruto:** o teste vigia `os.remove`, `unlink`, `rename`, `replace`, `shutil.move` e `rmtree` em `entrada\`. Confere também o sha256, a data e a lista da pasta antes e depois.
- **Queimar sem `.ok`**, ou com `palavras.json` quebrado: nesse caso grava `ERRO.txt` e não queima.
- **Refazer o que já fez:** a segunda rodada não chama o modelo de novo e não regrava o `palavras.json` que você corrigiu.

## Limitações

- **Whisper e vídeo reais:** o Whisper de verdade não rodou aqui (o HuggingFace está bloqueado) e não há vídeo real. O teste usa o vídeo sintético do `gerar_teste.py`, com voz do espeak-ng, e um modelo falso que devolve o gabarito.
- **Windows:** os `.cmd` e o Agendador não foram testados num Windows de verdade, porque esta nuvem é Linux. O código usa só `pathlib` e caminhos sem barra fixa. O comando do Agendador tem limite de 261 caracteres: com caminho muito longo, mova a pasta.
- **Pasta sincronizada:** em pasta do OneDrive ou de outro sincronizador, o arquivo pode aparecer "parado" antes de baixar inteiro. Use uma pasta local.
