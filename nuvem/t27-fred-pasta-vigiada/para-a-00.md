# Para a 00 · 27 · Nuvem · Fred · pasta vigiada de vídeo

**O que é:** `vigia.py`, o vigia de pasta no Windows. Vídeo novo em `entrada\` → passo `revisar` da v2 (`revisar.txt` + 3 prévias). Queima só quando o dono cria o `<nome>.ok`. Com "publi" no nome, deixa o checklist de 10 itens em rascunho. Nunca publica, nunca corta silêncio, nunca apaga nem move o bruto.
**Status:** completo, com 43 testes verdes (14 novos + os 29 da v2). Sem Whisper real e sem Windows real aqui.
**Comando (PC):**
```
pip install faster-whisper "av<16" pytest
python -m pytest -q
python vigia.py --raiz D:\Fred\video --uma-vez
```
**Dona:** 31 · Fred · Conteúdo. **Prioridade:** 3.
**Só com dado real:** o Agendador e os .cmd no Windows; o tempo com o medium; a cópia em pasta sincronizada.

**MENSAGEM PRONTA**
Artifact "Nuvem · Fred · pasta vigiada de vídeo". Usa a legenda v2 sem mudança.
1. Copie vigia/ para o PC e rode `python -m pytest -q` (43 verdes; precisa do ffmpeg).
2. Troque a linha RAIZ em rodar-agora.cmd e rode com um bruto em entrada\. Confira revisao\<nome>\: o revisar.txt e as 3 prévias.
3. Corrija o palavras.json, crie <nome>.ok e rode de novo. O vídeo aparece em saida\.
4. Se der certo, rode instalar-agendador.cmd (a cada 5 min).
Para decidir: se o .ok sozinho basta como aprovação (hoje basta); se publi entra pelo nome do arquivo (hoje sim).
