/**
 * Auditoria da catraca e da fila (catraca.js, whatsapp/lib/outbox.js, whatsapp-governador.js, whatsapp-convivencia.js,
 * lib/conta-nominal.js, trava-reenvio.js), 14/10/2026, sessao da nuvem. Sem rede, sem npm:
 *
 *   node --test testes/catraca-auditoria.test.js          (Node 22+; ~30 s)
 *   SEMENTE=123 node --test testes/catraca-auditoria.test.js   (outra semente para os testes de propriedade)
 *
 * Cada teste roda numa COPIA do pacote numa pasta temporaria, com um banco da captura de teste (o mesmo esquema que os
 * testes do pacote usam) e o estado do servidor que cada caso precisa. Nada toca o servidor nem a fila de verdade.
 *
 *   Axx  achado: falha no codigo de 14/10/2026 e passa com o patch de mesmo numero (patches/NN-*.diff); o A10 e do 02.
 *   Pxx  propriedade: sequencias aleatorias (semente fixa) contra uma invariante das regras R1-R60; passam antes e depois.
 *   Rxx  caca dirigida que NAO achou furo: segura regressao.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const { DatabaseSync } = require('node:sqlite');

const PACOTE = path.join(__dirname, '..');
const RAIZ = fs.mkdtempSync(path.join(os.tmpdir(), 'catraca-auditoria-'));
process.env.HOME = RAIZ;
process.env.USERPROFILE = RAIZ;
process.env.OZAV_CATRACA = 'valer';
for (const k of ['OZAV_CONTA_NOMINAL', 'OZAV_CONTA_NOMINAL_ARQ', 'OZAV_CANAL', 'OZAV_CANAL_CONFIRMADO', 'OZAV_GOVERNADOR_RAIZ', 'OZAV_CORREDORES_FORA']) delete process.env[k];

test.after(() => fs.rmSync(RAIZ, { recursive: true, force: true }));

// ------------------------------------------------------------------ gerador com semente (sem dependencia)

const SEMENTE = Number(process.env.SEMENTE || 20261014);
function gerador(semente) {
  let a = semente >>> 0;
  const r = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  r.int = (a0, b0) => a0 + Math.floor(r() * (b0 - a0 + 1));
  r.um = (xs) => xs[Math.floor(r() * xs.length)];
  r.chance = (p) => r() < p;
  return r;
}

// ------------------------------------------------------------------ a copia do pacote

let _n = 0;
/** Copia o pacote (sem testes) para uma pasta nova, com o banco da captura vazio. Cada copia e um "servidor" novo. */
function copia({ painel, feriados, banco = true } = {}) {
  const dir = path.join(RAIZ, `copia-${++_n}`);
  fs.cpSync(PACOTE, dir, { recursive: true, filter: (src) => !/^(testes|node_modules)(\/|\\|$)/.test(path.relative(PACOTE, src)) });
  if (banco) {
    fs.mkdirSync(path.join(dir, 'whatsapp', 'dados'), { recursive: true });
    const db = new DatabaseSync(path.join(dir, 'whatsapp', 'dados', 'mensagens.db'));
    db.exec(`CREATE TABLE conversas (jid TEXT, nome TEXT);
             CREATE TABLE mensagens (jid TEXT, ts INTEGER, de_mim INTEGER, autor TEXT, autor_jid TEXT, texto TEXT, tipo TEXT, fonte TEXT);
             CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
             CREATE INDEX mensagens_jid_ts ON mensagens (jid, ts);`);
    db.close();
  }
  if (painel !== undefined) fs.writeFileSync(path.join(dir, 'conduzir-config.json'), typeof painel === 'string' ? painel : JSON.stringify(painel));
  if (feriados !== undefined) fs.writeFileSync(path.join(dir, 'feriados.txt'), feriados);
  const req = (p) => require(path.join(dir, p));
  return {
    dir,
    catraca: () => req('catraca.js'),
    outbox: () => req('whatsapp/lib/outbox.js'),
    contaNominal: () => req('lib/conta-nominal.js'),
    /** Uma fala no banco da captura. lado: cliente | lorenzo (de_mim, a mao) | time | robo (de_mim) */
    falar(jid, nome, ts, lado, texto) {
      const db = new DatabaseSync(path.join(dir, 'whatsapp', 'dados', 'mensagens.db'));
      if (!db.prepare('SELECT 1 FROM conversas WHERE jid = ?').get(jid)) db.prepare('INSERT INTO conversas VALUES (?, ?)').run(jid, nome);
      const autor = lado === 'cliente' ? 'Cliente Teste' : lado === 'time' ? 'Ozav Time' : null;
      db.prepare('INSERT INTO mensagens VALUES (?, ?, ?, ?, ?, ?, ?, ?)').run(jid, ts, lado === 'lorenzo' || lado === 'robo' ? 1 : 0, autor, null, texto, 'texto', 'whatsapp');
      db.close();
    },
    fila() {
      const arq = path.join(dir, 'fila-envio.jsonl');
      return fs.existsSync(arq) ? fs.readFileSync(arq, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [];
    },
  };
}

/** Roda um script Node num processo separado (outro robo), com o ambiente dado. */
function rodarFilho(codigo, env = {}) {
  return new Promise((resolve) => {
    const f = spawn(process.execPath, ['-e', codigo], { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
    let saida = '';
    f.stdout.on('data', (d) => (saida += d));
    f.stderr.on('data', (d) => (saida += d));
    f.on('close', (c) => resolve({ codigo: c, saida }));
  });
}

const G = '120363999000000001@g.us';
const NOME = 'EMPRESA_TESTE <> Ozav';
const agoraS = () => Math.floor(Date.now() / 1000);

// ====================================================================== achados (falham antes do patch)

test('A01 dois robos enfileirando ao mesmo tempo para a mesma conversa: so um entra (R15, um robo por vez na fila)', async () => {
  const c = copia();
  // o cliente fechou ("ok, obrigado") e o Lorenzo respondeu: devolutiva do time pode sair (nao ha cliente esperando)
  c.falar(G, NOME, agoraS() - 3 * 3600, 'cliente', 'ok, obrigado');
  c.falar(G, NOME, agoraS() - 2 * 3600, 'lorenzo', 'combinado, sigo com o time por aqui');
  const outbox = path.join(c.dir, 'whatsapp', 'lib', 'outbox.js');
  const largada = Date.now() + 1500;
  const codigo = (i) =>
    `process.env.OZAV_CONTA_NOMINAL='liberar';const o=require(${JSON.stringify(outbox)});while(Date.now()<${largada}){}` +
    `const r=o.enfileirar([{canal:'whatsapp',jid:${JSON.stringify(G)},conversa:${JSON.stringify(NOME)},campanha:'devolutiva|robo${i}|r1',followup:false,texto:'saiu o retorno do time sobre o cadastro ${i}: ja esta liberado no portal'}]);` +
    `console.log(JSON.stringify({e:r.enfileiradas,rec:r.recusadas.map(x=>x.motivo)}))`;
  const filhos = await Promise.all(Array.from({ length: 8 }, (_, i) => rodarFilho(codigo(i))));
  for (const f of filhos) assert.equal(f.codigo, 0, f.saida);
  const naFila = c.fila().filter((x) => x.jid === G);
  assert.equal(naFila.length, 1, `${naFila.length} itens de robos diferentes entraram juntos na fila da mesma conversa: ${naFila.map((x) => x.campanha).join(', ')}`);
});

test('A02 painel de travas ilegivel nao solta conversa travada: nada sai e o motivo e escrito (falha FECHADA)', () => {
  const agora = Date.parse('2026-10-20T13:00:00Z'); // terca 10h de SP
  const c = copia({ painel: '{"travadas": []}' });
  c.falar(G, NOME, agora / 1000 - 3 * 86400, 'cliente', 'combinado, obrigado');
  const catraca = c.catraca();
  const item = { canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'devolutiva|x1|r1', followup: false, texto: 'Bom dia, pessoal! Saiu o retorno do time: o cadastro de voces ja esta liberado no portal.', chave: 'k1', em: new Date(agora).toISOString() };
  assert.equal(catraca.avaliar(item, { momento: 'entrada', agora, semLivro: true }).ok, true, 'controle: sem trava, esta devolutiva passa');
  fs.writeFileSync(path.join(c.dir, 'conduzir-config.json'), '{"travadas": ["EMPRESA_TESTE"], }'); // virgula sobrando: JSON quebrado na mao
  const r = catraca.avaliar(item, { momento: 'entrada', agora, semLivro: true });
  assert.equal(r.ok, false, 'o painel ilegivel virou "nenhuma trava" e a devolutiva passou para a conversa que o Lorenzo travou');
  assert.match(String(r.motivo), /painel|conduzir-config/i);
});

test('A03 governador com estado ilegivel nao desarma o disjuntor em silencio, e a convivencia percebe', () => {
  const raiz = fs.mkdtempSync(path.join(RAIZ, 'gov-'));
  const c = copia();
  process.env.OZAV_GOVERNADOR_RAIZ = raiz;
  try {
    const gov = require(path.join(c.dir, 'whatsapp-governador.js'));
    const msg = { canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'regua|x', followup: true, texto: 'oi', chave: 'm1' };
    gov.sinal('rate-overlimit', { conversa: NOME }, null); // o WhatsApp deu sinal: nada sai por 3h
    assert.match(String(gov.motivo(msg, Date.now(), null)), /disjuntor/);
    const arq = path.join(raiz, 'whatsapp-governador.json');
    fs.writeFileSync(arq, fs.readFileSync(arq, 'utf8').slice(0, 40)); // escrita cortada no meio (disco cheio, edicao a mao)
    const m = gov.motivo(msg, Date.now(), null);
    assert.ok(m, 'com o estado ilegivel o disjuntor sumiu e a mensagem sai logo depois de um sinal de banimento');
    const conv = require(path.join(c.dir, 'whatsapp-convivencia.js'));
    const q = conv.quadro(Date.now(), { gov, db: null, pendentes: [], livro: [], grupos: [], desligados: [] });
    assert.ok(q.governador.ilegivel, 'a convivencia diz "na duvida (governador ilegivel), nao", mas nunca ve o estado ilegivel');
  } finally {
    delete process.env.OZAV_GOVERNADOR_RAIZ;
  }
});

test('A04 trava casa com o nome escrito diferente (espaco invisivel, NBSP, espaco duplo, hifen, letra estilizada) (R10)', () => {
  const c = copia();
  const { casa } = c.catraca();
  const r = gerador(SEMENTE);
  const ruidos = [
    ['espaco duro (NBSP)', (s) => s.replace(/ /g, ' ')],
    ['espaco de largura zero', (s) => s.slice(0, 2) + '​' + s.slice(2)],
    ['espaco duplo', (s) => s.replace(/ /g, '  ')],
    ['hifen no lugar do espaco', (s) => s.replace(/ /g, '-')],
    ['sem espaco', (s) => s.replace(/ /g, '')],
    ['emoji no meio', (s) => s.replace(/ /g, ' 🚀 ')],
    ['letra de largura total', (s) => s.replace(/a/g, 'ａ')],
  ];
  const palavras = ['acme', 'nova', 'trading', 'logistica', 'pagamentos', 'brasil', 'global', 'tech', 'comercio'];
  const falhas = [];
  for (let i = 0; i < 200; i++) {
    const nome = `${r.um(palavras)} ${r.um(palavras)}`;
    const [qual, ruido] = r.um(ruidos);
    const conversa = `${ruido(nome.toUpperCase())} <> Ozav`;
    if (!casa({ conversa }, [nome])) falhas.push(`${qual}: painel "${nome}" x conversa ${JSON.stringify(conversa)}`);
  }
  assert.equal(falhas.length, 0, `${falhas.length} de 200 nomes travados nao casaram (o robo escreve na conversa travada):\n  ${[...new Set(falhas.map((f) => f.split(':')[0]))].join('\n  ')}`);
});

test('A05 vespera de dia santo judaico depois do por do sol: follow-up nao sai (feriado que comeca na noite anterior)', () => {
  const c = copia();
  const catraca = c.catraca();
  const fup = (agora) => ({ canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'regua|teste', followup: true, texto: 'Boa noite, pessoal! A cotacao de USDT esta boa hoje, querem simular um pagamento?', chave: 'f' + agora, em: new Date(agora).toISOString() });
  // controle: terca 20/04/2027 18h30 de SP, vespera de Tiradentes (nao e dia santo judaico): o follow-up passa
  const controle = Date.parse('2027-04-20T21:30:00Z');
  c.falar(G, NOME, controle / 1000 - 3 * 86400, 'cliente', 'combinado, obrigado');
  const rc = catraca.avaliar(fup(controle), { momento: 'entrada', agora: controle, semLivro: true });
  assert.equal(rc.ok, true, `controle: ${rc.motivo}`);
  const agora = Date.parse('2027-04-27T21:30:00Z'); // terca 27/04/2027 18h30 de SP; 28/04/2027 e Pessach no feriados.txt
  c.falar(G, NOME, agora / 1000 - 3 * 86400, 'cliente', 'combinado, obrigado');
  const r = catraca.avaliar(fup(agora), { momento: 'entrada', agora, semLivro: true });
  assert.equal(r.ok, false, 'o follow-up sai na vespera de Pessach as 18h30, depois do por do sol');
  assert.match(String(r.motivo), /vespera/);
});

test('A06 linha do feriados.txt so com a data (sem nome) conta como feriado', () => {
  const c = copia({ feriados: '# teste\n2026-11-17\n2026-11-18  com nome\n' });
  const { feriadoDe } = c.catraca();
  const arq = path.join(c.dir, 'feriados.txt');
  assert.ok(feriadoDe('2026-11-18', arq), 'a linha com nome vale');
  assert.ok(feriadoDe('2026-11-17', arq), 'a data sem nome foi ignorada em silencio: os robos de follow-up trabalham no feriado');
});

test('A07 pedido de documento de conta nominal com espaco duro ou espaco duplo nao escapa da trava (R11)', () => {
  const c = copia();
  const { pedeContaNominal } = c.contaNominal();
  for (const t of [
    'pra abrir a conta em reais ainda falta o comprovante de endereco do socio',
    'pra abrir a conta  em reais ainda falta o comprovante de endereco do socio',
    'falta o cadastro no BC Protege+ para a conta em reais',
    'pra conta​ nominal ainda precisamos do aceite do termo',
  ]) {
    assert.equal(pedeContaNominal(t), true, `escapou: ${JSON.stringify(t)}`);
  }
});

test('A08 "oi" de grupo novo nao sai em feriado de dia de semana (R39 diz dia util; a catraca exclui feriado do dia util)', () => {
  const raiz = fs.mkdtempSync(path.join(RAIZ, 'gov-'));
  const c = copia();
  process.env.OZAV_GOVERNADOR_RAIZ = raiz;
  try {
    const gov = require(path.join(c.dir, 'whatsapp-governador.js'));
    gov.gravarEstado({ ...gov.lerEstado(), novas_desde: '2026-09-01T00:00:00Z' });
    const oi = { canal: 'whatsapp', acao: 'oi_pendente', conversa: NOME, grupo_nome: NOME, jid: 'oi:x@g.us', texto: 'opa, tudo certo? criei o grupo pra gente falar por aqui', chave: 'o1' };
    const feriado = Date.parse('2026-11-20T13:00:00Z'); // sexta 10h de SP, Consciencia Negra
    const util = Date.parse('2026-11-19T13:00:00Z'); // quinta 10h de SP
    assert.equal(gov.motivo(oi, util, null), null, 'no dia util o "oi" sai');
    assert.match(String(gov.motivo(oi, feriado, null)), /dia util/, 'no feriado o "oi" de grupo novo saiu');
  } finally {
    delete process.env.OZAV_GOVERNADOR_RAIZ;
  }
});

test('A09 envio interrompido por queda do processo nao volta a sair sozinho: vira "envio incerto" para o Lorenzo (R36, R37)', async () => {
  const c = copia();
  process.env.OZAV_CONTA_NOMINAL = 'liberar';
  try {
    const outbox = c.outbox();
    c.falar(G, NOME, agoraS() - 3 * 3600, 'cliente', 'ok, obrigado');
    c.falar(G, NOME, agoraS() - 2 * 3600, 'lorenzo', 'combinado');
    const r = outbox.enfileirar([{ canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'devolutiva|a09|r1', followup: false, texto: 'saiu o retorno do time: o cadastro ja esta liberado no portal' }]);
    assert.equal(r.enfileiradas, 1, JSON.stringify(r));
    const [m] = outbox.pendentes();
    // o dreno anota a tentativa ANTES de chamar o WhatsApp; enquanto o processo vive, o item segue na fila (os outros robos o veem)
    assert.equal(typeof outbox.marcarEnviando, 'function', 'o outbox nao tem como anotar "estou enviando": uma queda no meio do envio nao deixa rastro e o dreno que sobe manda de novo');
    outbox.marcarEnviando(m);
    assert.equal(outbox.pendentes().filter((x) => x.chave === m.chave).length, 1, 'envio em curso (processo vivo) sumiu da fila');
    // outro processo de dreno anota a tentativa e cai (kill, falta de memoria, reboot) antes de marcar enviada
    const outboxJs = JSON.stringify(path.join(c.dir, 'whatsapp', 'lib', 'outbox.js'));
    const f = await rodarFilho(`const o=require(${outboxJs});const m=o.pendentes()[0];o.marcarEnviando(m);process.exit(9)`);
    assert.equal(f.codigo, 9, f.saida);
    // o dreno volta: o item nao pode estar pronto para sair de novo, e a trava-reenvio tem de ve-lo
    assert.equal(outbox.pendentes().filter((x) => x.chave === m.chave).length, 0, 'o item com envio interrompido voltou para a fila e sai de novo (duplicata)');
    assert.deepEqual(outbox.incertos().map((x) => x.chave), [m.chave]);
    const t = await rodarFilho(`process.argv.push('--valer');require(${JSON.stringify(path.join(c.dir, 'trava-reenvio.js'))})`, { OZAV_CONTA_NOMINAL: 'liberar' });
    assert.equal(t.codigo, 0, t.saida);
    assert.equal(outbox.incertos().length, 0, 'a trava-reenvio nao tirou o envio incerto da fila');
    assert.ok(c.fila().some((x) => x.canal === 'slack' && /^envio-incerto\|/.test(String(x.campanha))), 'o Lorenzo nao recebeu o texto para conferir: ' + t.saida);
  } finally {
    delete process.env.OZAV_CONTA_NOMINAL;
  }
});

test('A10 travar com o painel ilegivel nao apaga as travas que ja estavam nele (perda de dado)', () => {
  const txt = '{"travadas": ["EMPRESA_UM", "EMPRESA_DOIS"], "cautela": ["EMPRESA_TRES"],}\n'; // virgula sobrando
  const c = copia({ painel: txt });
  const { mexerPainel } = c.catraca();
  let erro = null;
  try {
    mexerPainel('travadas', 'EMPRESA_QUATRO', true);
  } catch (e) {
    erro = e;
  }
  const depois = fs.readFileSync(path.join(c.dir, 'conduzir-config.json'), 'utf8');
  assert.equal(depois, txt, `o painel foi regravado por cima e as travas que estavam nele sumiram: ${depois.trim()}`);
  assert.match(String(erro && erro.message), /ilegivel/, 'travar com o painel ilegivel tem de dar erro dizendo o que houve');
});

// ====================================================================== propriedades (semente fixa; passam antes e depois)

/** Uma fonte da catraca em memoria (a mesma interface do fonteReal), com a conversa montada pelo gerador. */
function fonteDe({ agora, C, enviados = [], pendentes = [], painel = {}, nunca = [] }, catraca) {
  const env = enviados.map((e) => ({ ...e, tipo: catraca.classificar({ campanha: e.campanha, followup: e.followup }), robo: catraca.roboDe(e.campanha) }));
  return {
    agora,
    regras: null,
    painel,
    nunca,
    semBanco: !C,
    pendentes: () => pendentes,
    enviados: () => env,
    enviadosDe: () => env.slice().sort((a, b) => Date.parse(b.em) - Date.parse(a.em)),
    conversa: () => C,
    ehDoLorenzo: () => false,
    fechar() {},
  };
}

const FALAS_CLIENTE = ['Boa tarde pessoal!', 'tem como cotar 10 mil USDT hoje?', 'to com um saque travado', 'ok, obrigado', 'perfeito, fico no aguardo', 'vou testar e te aviso', '👍', 'quanto fica o spread pra EUR?', 'mandei o comprovante agora'];
const FALAS_NOSSAS = ['combinado!', 'vou checar com o time e te volto', 'liberado, ja pode operar', 'segue a cotacao: 5,32', 'checking right now'];

/** Um retrato aleatorio da conversa (o que o lerConversa devolveria), coerente: cada campo e o mais novo do seu lado. */
function conversaAleatoria(r, agoraSeg, catraca) {
  const n = r.int(0, 8);
  const linhas = [];
  let t = agoraSeg - r.int(60, 10 * 86400);
  for (let i = 0; i < n; i++) {
    const lado = r.um(['cliente', 'cliente', 'mao', 'time', 'robo']);
    linhas.push({ lado, ts: t, texto: lado === 'cliente' ? r.um(FALAS_CLIENTE) : r.um(FALAS_NOSSAS) });
    t += r.int(30, 30 * 3600);
    if (t >= agoraSeg) break;
  }
  const ordem = linhas.filter((x) => x.ts < agoraSeg).reverse();
  const C = { jids: [G], ultima_qualquer_ts: null, ultima_cliente_ts: null, ultima_nossa_ts: null, ultima_mao_ts: null, ultima_time_ts: null, ultima_robo_ts: null, nossos: [], quem_por_ultimo: null, ultima_nossa: null, ultima_cliente: null };
  for (const x of ordem) {
    if (C.ultima_qualquer_ts == null) C.ultima_qualquer_ts = x.ts;
    if (x.lado === 'cliente') {
      if (!C.ultima_cliente_ts) {
        C.ultima_cliente_ts = x.ts;
        C.ultima_cliente = { ts: x.ts, texto: x.texto, autor: 'Cliente Teste' };
      }
      if (!C.quem_por_ultimo) C.quem_por_ultimo = 'cliente';
      continue;
    }
    if (!C.ultima_nossa_ts) {
      C.ultima_nossa_ts = x.ts;
      C.ultima_nossa = { ts: x.ts, texto: x.texto, quem: x.lado, autor: x.lado === 'time' ? 'Ozav Time' : null };
    }
    if (x.lado === 'mao' && !C.ultima_mao_ts) C.ultima_mao_ts = x.ts;
    if (x.lado === 'time' && !C.ultima_time_ts) C.ultima_time_ts = x.ts;
    if (x.lado === 'robo' && !C.ultima_robo_ts) C.ultima_robo_ts = x.ts;
    if (!C.quem_por_ultimo) C.quem_por_ultimo = x.lado;
    if (C.nossos.length < 12) C.nossos.push({ ts: x.ts, texto: x.texto, quem: x.lado });
  }
  const ordemD = ordem.map((x) => ({ lado: x.lado === 'cliente' ? 'cliente' : 'nosso', ts: x.ts, texto: x.texto, autor: x.lado === 'cliente' ? 'Cliente Teste' : null }));
  // derivados (turno do cliente, nomes): o mesmo calculo do pacote, pela conversaDoPacote
  const D = catraca.conversaDoPacote({ ultimas: [] });
  return Object.assign(D, C, { ...derivar(ordemD) });
}
function derivar(ordem) {
  const i0 = ordem.findIndex((x) => x.lado === 'cliente');
  const turno = [];
  if (i0 >= 0) for (let i = i0; i < ordem.length && ordem[i].lado === 'cliente'; i++) turno.push(ordem[i]);
  return { nomes_cliente: new Set(['cliente']), turno_cliente: turno.map((x) => x.texto).reverse().join('\n'), turno_cliente_ts: turno.length ? turno[0].ts : null, turno_midia: false, cliente_recentes: ordem.filter((x) => x.lado === 'cliente').slice(0, 8).map((x) => x.texto) };
}

const ITENS = [
  { campanha: 'regua|p', followup: true, texto: 'Fala pessoal! A cotacao de USDT esta boa hoje, querem simular?' },
  { campanha: 'LISTA-4-conduzir-x.md', followup: false, texto: 'Fala pessoal! consigo sim, te mando a cotacao em seguida' },
  { campanha: 'devolutiva|p|r1', followup: false, texto: 'saiu o retorno do time: liberado no portal' },
  { campanha: 'pedido|p|2|t1', followup: false, texto: 'passando para lembrar do comprovante de endereco da empresa' },
  { campanha: 'hunting-wpp|p', texto: 'Ola! Somos a Ozav, infraestrutura de cambio para empresas.' },
];

test('P01 propriedade: conversa travada nunca recebe nada de robo, em qualquer tipo, entrada ou saida (R10)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 1);
  for (let i = 0; i < 400; i++) {
    const agora = Date.parse('2026-10-19T12:00:00Z') + r.int(0, 30 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    const base = r.um(ITENS);
    const item = { ...base, canal: 'whatsapp', jid: G, conversa: NOME, chave: 'p' + i, em: new Date(agora - r.int(0, 3600) * 1000).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C, painel: { travadas: ['EMPRESA_TESTE'] } }, catraca), momento: r.um(['entrada', 'saida']), semLivro: true });
    assert.equal(v.ok, false, `item ${base.campanha} passou numa conversa travada`);
  }
});

test('P02 propriedade: follow-up que passa tem 24h de silencio, nenhum toque nosso em 20h e nao e feriado (R12, R17, R21)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 2);
  let passaram = 0;
  for (let i = 0; i < 600; i++) {
    const agora = Date.parse('2026-10-19T11:30:00Z') + r.int(0, 60 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    const enviados = r.chance(0.4) ? [{ jid: G, chave: 'e' + i, campanha: r.um(['regua|x', 'devolutiva|x|r1']), texto: 'Fala pessoal! tudo certo?', em: new Date(agora - r.int(1, 72) * 3600e3).toISOString() }] : [];
    const item = { canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'regua|p', followup: true, texto: r.um(['Fala pessoal! A cotacao de USDT esta boa hoje, querem simular?', 'Opa! vamos testar o fluxo de payout essa semana?']), chave: 'f' + i, em: new Date(agora).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C, enviados }, catraca), momento: 'entrada', semLivro: true });
    if (!v.ok) continue;
    passaram++;
    const s = agora / 1000;
    assert.ok(!C.ultima_qualquer_ts || s - C.ultima_qualquer_ts >= 24 * 3600, 'follow-up com a conversa viva em 24h');
    assert.ok(!enviados.length || agora - Date.parse(enviados[0].em) >= 20 * 3600e3, 'follow-up com toque nosso ha menos de 20h');
    assert.equal(catraca.feriadoDe(new Date(agora - 3 * 3600e3).toISOString().slice(0, 10)), null, 'follow-up em feriado');
  }
  assert.ok(passaram > 0, 'o gerador precisa produzir casos que passam');
});

test('P03 propriedade: retorno do time e pedido ao cliente nunca saem com pergunta do cliente sem resposta ha ate 7 dias (R19)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 3);
  for (let i = 0; i < 600; i++) {
    const agora = Date.parse('2026-10-19T14:00:00Z') + r.int(0, 30 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    const base = r.um(ITENS.filter((x) => /^(devolutiva|pedido)/.test(x.campanha)));
    const item = { ...base, canal: 'whatsapp', jid: G, conversa: NOME, chave: 'd' + i, em: new Date(agora).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C }, catraca), momento: r.um(['entrada', 'saida']), semLivro: true });
    if (!v.ok) continue;
    // oraculo independente: a ultima fala e do cliente, com "?" ou "travado", ha ate 7 dias
    const espera = C.ultima_cliente_ts && (!C.ultima_nossa_ts || C.ultima_cliente_ts > C.ultima_nossa_ts) && agora / 1000 - C.ultima_cliente_ts <= 7 * 86400 && /\?|travad/.test(C.turno_cliente);
    assert.ok(!espera, `${base.campanha} saiu por cima do cliente esperando: ${JSON.stringify(C.turno_cliente)}`);
  }
});

test('P04 propriedade: resposta comum so sai com o cliente por ultimo, ou com promessa nossa vencida (R18)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 4);
  for (let i = 0; i < 600; i++) {
    const agora = Date.parse('2026-10-19T14:00:00Z') + r.int(0, 30 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    if (!C.ultima_qualquer_ts) continue; // conversa sem fala nenhuma: ver R05
    const item = { ...ITENS[1], canal: 'whatsapp', jid: G, conversa: NOME, chave: 'r' + i, em: new Date(agora).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C }, catraca), momento: 'entrada', semLivro: true });
    if (!v.ok) continue;
    const clientePorUltimo = C.ultima_cliente_ts && (!C.ultima_nossa_ts || C.ultima_cliente_ts > C.ultima_nossa_ts);
    assert.ok(clientePorUltimo || v.promessa_vencida, 'resposta saiu sem nada a responder');
  }
});

test('P05 propriedade: na saida, follow-up nunca sai se alguem falou depois que ele entrou na fila (R16)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 5);
  for (let i = 0; i < 600; i++) {
    const agora = Date.parse('2026-10-19T14:00:00Z') + r.int(0, 30 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    const em = agora - r.int(0, 48 * 3600) * 1000;
    const item = { ...ITENS[0], canal: 'whatsapp', jid: G, conversa: NOME, chave: 's' + i, em: new Date(em).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C }, catraca), momento: 'saida', semLivro: true });
    if (!v.ok) continue;
    const emS = Math.floor(em / 1000);
    assert.ok(!(C.ultima_cliente_ts >= emS) && !(C.ultima_mao_ts >= emS) && !(C.ultima_time_ts >= emS), 'follow-up saiu com a conversa andando depois da fila');
  }
});

test('P06 propriedade: o que passa cabe no teto de tamanho do tipo (R25)', () => {
  const c = copia();
  const catraca = c.catraca();
  const r = gerador(SEMENTE + 6);
  for (let i = 0; i < 400; i++) {
    const agora = Date.parse('2026-10-19T14:00:00Z') + r.int(0, 30 * 86400) * 1000;
    const C = conversaAleatoria(r, agora / 1000, catraca);
    const base = r.um(ITENS.slice(0, 4));
    const texto = base.texto + ' ' + 'mais um detalhe. '.repeat(r.int(0, 30)) + (r.chance(0.3) ? '\nlinha\nlinha\nlinha' : '');
    const item = { ...base, texto, canal: 'whatsapp', jid: G, conversa: NOME, chave: 't' + i, em: new Date(agora).toISOString() };
    const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C }, catraca), momento: 'entrada', semLivro: true });
    if (!v.ok) continue;
    const teto = catraca.tetoDe(item, v.tipo, C, catraca.REGRAS);
    if (!teto) continue;
    const t = texto.replace(/\r/g, '').trim();
    assert.ok(t.length <= teto.chars && t.split('\n').filter((l) => l.trim()).length <= teto.linhas, `passou acima do teto: ${t.length} caracteres (teto ${teto.chars})`);
  }
});

// ====================================================================== caca dirigida sem furo (regressao)

test('R01 fuso: a abertura do dia e o feriado viram a meia-noite de Sao Paulo, nao a de UTC (servidor em UTC)', () => {
  const c = copia();
  const catraca = c.catraca();
  // 01/11/2026 23h59 de SP = 02/11 02h59 UTC (ja e Finados em UTC, ainda nao em SP)
  const vespera = Date.parse('2026-11-02T02:59:00Z');
  const dia = Date.parse('2026-11-02T03:01:00Z');
  const fup = (agora) => ({ canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'regua|x', followup: true, texto: 'Boa noite, pessoal! A cotacao de USDT esta boa hoje, querem simular?', chave: 'z', em: new Date(agora).toISOString() });
  const C = { jids: [G], ultima_qualquer_ts: vespera / 1000 - 3 * 86400, ultima_cliente_ts: vespera / 1000 - 3 * 86400, nossos: [], nomes_cliente: new Set(), turno_cliente: 'combinado, obrigado', turno_cliente_ts: vespera / 1000 - 3 * 86400, cliente_recentes: [] };
  const v1 = catraca.avaliar(fup(vespera), { fonte: fonteDe({ agora: vespera, C }, catraca), momento: 'entrada', semLivro: true });
  assert.doesNotMatch(String(v1.motivo || ''), /feriado/, 'as 23h59 de SP ainda nao e Finados');
  const v2 = catraca.avaliar(fup(dia), { fonte: fonteDe({ agora: dia, C }, catraca), momento: 'entrada', semLivro: true });
  assert.match(String(v2.motivo || ''), /feriado/, 'as 00h01 de SP ja e Finados');
});

test('R02 texto repetido: acento, maiuscula e emoji nao disfarcam a mesma mensagem (R26)', () => {
  const c = copia();
  const catraca = c.catraca();
  const agora = Date.parse('2026-10-20T14:00:00Z');
  const C = { jids: [G], nossos: [{ ts: agora / 1000 - 86400, texto: 'a cotação de USDT está ótima hoje, vamos simular um pagamento?', quem: 'robo' }] };
  const rep = catraca.repeteNossa('A COTACAO de usdt esta otima hoje 🚀 vamos simular um pagamento?', C, [], agora / 1000, new Set());
  assert.ok(rep, 'a mesma mensagem com outra grafia passou como nova');
});

test('R03 resposta substitui o follow-up que esperava na fila da mesma conversa (R15)', () => {
  const c = copia();
  process.env.OZAV_CONTA_NOMINAL = 'liberar';
  try {
    const outbox = c.outbox();
    c.falar(G, NOME, agoraS() - 3 * 86400, 'cliente', 'combinado');
    const fila0 = outbox.enfileirar([{ canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'leva|r03', followup: true, texto: 'x', nao_antes: new Date(Date.now() + 86400e3).toISOString() }]);
    // o follow-up pode ou nao entrar pela forma; o que importa e a substituicao quando ele estiver la
    if (fila0.enfileiradas !== 1) return;
    c.falar(G, NOME, agoraS() - 60, 'cliente', 'tem como cotar 10 mil USDT hoje?');
    const r = outbox.enfileirar([{ canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'LISTA-4-conduzir-r03.md', followup: false, texto: 'consigo sim, te mando a cotacao em seguida' }]);
    assert.equal(r.enfileiradas, 1, JSON.stringify(r.recusadas));
    assert.equal(r.substituidas.length, 1);
    assert.equal(outbox.pendentes().filter((x) => x.jid === G).length, 1);
  } finally {
    delete process.env.OZAV_CONTA_NOMINAL;
  }
});

test('R04 mesma campanha enfileirada duas vezes no mesmo processo: um item so; ja enviada: nao entra de novo (R29)', () => {
  const c = copia();
  process.env.OZAV_CONTA_NOMINAL = 'liberar';
  try {
    const outbox = c.outbox();
    c.falar(G, NOME, agoraS() - 3 * 3600, 'cliente', 'ok, obrigado');
    c.falar(G, NOME, agoraS() - 2 * 3600, 'lorenzo', 'combinado');
    const item = { canal: 'whatsapp', jid: G, conversa: NOME, campanha: 'devolutiva|r04|r1', followup: false, texto: 'saiu o retorno do time: liberado no portal' };
    const a = outbox.enfileirar([item, { ...item }]);
    assert.equal(a.enfileiradas, 1);
    const [m] = outbox.pendentes();
    outbox.marcarEnviada(m);
    assert.equal(outbox.enfileirar([item]).jaEnviadas, 1);
    assert.equal(outbox.pendentes().length, 0);
  } finally {
    delete process.env.OZAV_CONTA_NOMINAL;
  }
});

test('R05 (em aberto) resposta comum numa conversa sem nenhuma fala no banco passa: "nada a responder" nao fecha', { todo: 'decisao do dono: jid trocado ou captura parada deixam a conversa vazia; hoje a resposta sai' }, () => {
  const c = copia();
  const catraca = c.catraca();
  const agora = Date.parse('2026-10-20T14:00:00Z');
  const C = conversaAleatoria(gerador(1), agora / 1000, catraca);
  for (const k of Object.keys(C)) if (/_ts$/.test(k)) C[k] = null;
  Object.assign(C, { nossos: [], quem_por_ultimo: null, ultima_nossa: null, ultima_cliente: null, turno_cliente: '', cliente_recentes: [] });
  const item = { ...ITENS[1], canal: 'whatsapp', jid: G, conversa: NOME, chave: 'r05', em: new Date(agora).toISOString() };
  const v = catraca.avaliar(item, { fonte: fonteDe({ agora, C }, catraca), momento: 'entrada', semLivro: true });
  assert.equal(v.ok, false, 'a resposta saiu numa conversa sem nenhuma fala');
});
