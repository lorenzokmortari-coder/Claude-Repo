Para 23 · Veedha · Motor (aplicar) e 20 · Veedha · Orquestrador (decidir) · entrega 14 · prioridade 1

Artifact: "Nuvem · Veedha · red team do portão" https://claude.ai/artifact/9PiiQKdp8MFakYy68ZTiwW
Consolidado da 14 mais o patch da 20 em aplicar/veedha-portao.diff, na triagem https://claude.ai/artifact/QiqEBkSYXwY2PX5pMQEMaT.

Na pasta do motor:
```
cp -r <t24>/aplicar/testes/veedha-portao/. .
node --test testes/redteam.teste.js testes/dispensa.teste.js testes/modelos20.teste.js   # 10 falham
patch -p1 < <t24>/aplicar/veedha-portao.diff
node --test testes/redteam.teste.js testes/dispensa.teste.js testes/modelos20.teste.js   # 12 ok
VEEDHA_VAULT=./vault node testes/portao.teste.js   # 773 ok
```

**O que muda:**
- as fugas para REVISAR caem de 71 para 9;
- nenhuma mensagem sai LIVRE sem dever;
- com o patch da 20, "renda fixa", "pix" e "TED" sem rodapé deixam de passar.

As duas ordens dão o mesmo `portao.js`.

**Decidir (20):**
- barrar a gíria de agenda ("já remarquei", "vai dar bom");
- se a pressa sozinha barra.

**Só com dado real:** o alarme falso no corpus anonimizado do escritório.
