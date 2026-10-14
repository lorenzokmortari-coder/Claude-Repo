/**
 * Tarefa 18 (nuvem, 14/10/2026): risco de banimento no WhatsApp. Testes dos dois patches do governador.
 *
 *   node --test testes/banimento.test.js
 *
 * Sem rede e sem o banco real: estado e livro do governador numa pasta temporaria (OZAV_GOVERNADOR_RAIZ) e o banco
 * da captura em memoria (node:sqlite), com a mesma tabela `mensagens` (jid, de_mim, ts).
 *
 *   B01-B03 (patch 01): os sinais de restricao de 2025-2026 armam o disjuntor; queda comum nao arma.
 *   B04-B08 (patch 02): as mensagens sem resposta no privado em 30 dias sao medidas, e so seguram com teto ligado.
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const RAIZ = fs.mkdtempSync(path.join(os.tmpdir(), 'ozav-t18-'));
process.env.OZAV_GOVERNADOR_RAIZ = RAIZ;
const ARQ_GOV = path.join(__dirname, '..', 'whatsapp-governador.js');
const LIVRO = path.join(RAIZ, 'whatsapp-governador.jsonl');
const ESTADO = path.join(RAIZ, 'whatsapp-governador.json');

/** O governador carregado de novo com estas variaveis (os tetos sao lidos no carregamento). */
function governador(env = {}) {
  for (const k of ['OZAV_WPP_SEM_RESPOSTA_30D']) delete process.env[k];
  Object.assign(process.env, env);
  delete require.cache[require.resolve(ARQ_GOV)];
  return require(ARQ_GOV);
}

function limpar() {
  fs.rmSync(LIVRO, { force: true });
  fs.rmSync(ESTADO, { force: true });
}

test.after(() => fs.rmSync(RAIZ, { recursive: true, force: true }));

// ------------------------------------------------------------------ patch 01: sinais de restricao

const RESTRICAO = [
  'Error: 463 NackCallerReachoutTimelocked', // a trava de reach-out (issue 2441 do Baileys)
  'reachout timelock: cannot message new contacts',
  'RESTRICT_ALL_COMPANIONS',
  'Stream Errored (device_removed)',
  'Your account may soon be subject to restrictions',
  'This account is not allowed to use WhatsApp',
];
const QUEDA_COMUM = ['Connection Closed', 'Timed Out', 'Stream Errored (conflict)', 'Stream Errored (restart required)', 'socket hang up', 'read ECONNRESET'];

test('B01 cada sinal de restricao arma o disjuntor (nada por 3h, nenhuma interacao nova por 48h)', () => {
  const gov = governador();
  for (const erro of RESTRICAO) {
    limpar();
    assert.strictEqual(gov.sinal(erro, { conversa: 'EMPRESA_TESTE <> Ozav' }), true, erro);
    const e = gov.lerEstado();
    assert.ok(Date.parse(e.disjuntor_tudo_ate) > Date.now() + 2.9 * 3600e3, erro);
    assert.ok(Date.parse(e.disjuntor_novas_ate) > Date.now() + 47.9 * 3600e3, erro);
    assert.match(gov.motivo({ canal: 'whatsapp', jid: 'x@g.us', chave: 'k', campanha: 'regua|x' }, Date.now(), null) || '', /disjuntor armado/);
  }
});

test('B02 queda comum de conexao nao arma o disjuntor (controle)', () => {
  const gov = governador();
  for (const erro of QUEDA_COMUM) {
    limpar();
    assert.strictEqual(gov.sinal(erro, null), false, erro);
    assert.strictEqual(gov.lerEstado().disjuntor_tudo_ate, null, erro);
  }
});

test('B03 os sinais que ja armavam continuam armando (regressao)', () => {
  const gov = governador();
  for (const erro of ['rate-overlimit', 'forbidden', 'Connection Failure 401', 'loggedOut', 'temporarily banned', 'spam']) {
    limpar();
    assert.strictEqual(gov.sinal(erro, null), true, erro);
  }
});

// ------------------------------------------------------------------ patch 02: mensagens sem resposta

const DIA = 86400e3;
function bancoFalso(falas) {
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(':memory:');
  db.exec("CREATE TABLE mensagens (id TEXT PRIMARY KEY, jid TEXT NOT NULL, de_mim INTEGER NOT NULL, ts INTEGER NOT NULL, fonte TEXT NOT NULL DEFAULT 'whatsapp')");
  const ins = db.prepare('INSERT INTO mensagens (id, jid, de_mim, ts) VALUES (?, ?, ?, ?)');
  falas.forEach(([jid, deMim, msAtras], i) => ins.run('m' + i, jid, deMim, Math.floor((Date.now() - msAtras) / 1000)));
  return db;
}
function livroCom(linhas) {
  fs.writeFileSync(LIVRO, linhas.map(([jid, msAtras, extra]) => JSON.stringify({ chave: 'c' + Math.random(), acao: 'msg', conversa: String(jid), jid, nova: false, resposta: false, ...extra, em: new Date(Date.now() - msAtras).toISOString() })).join('\n') + '\n');
}

// A: 3 follow-ups e nunca respondeu (3); B: respondeu depois (0); C: falou ANTES do nosso envio (1); D: resposta nossa
// (fora); E: ha 40 dias (fora); grupo (fora); linha velha sem jid (fora). Total: 4 mensagens, 2 contatos.
function cenario() {
  limpar();
  livroCom([
    ['5511900000001@s.whatsapp.net', 10 * DIA],
    ['5511900000001@s.whatsapp.net', 5 * DIA],
    ['5511900000001@s.whatsapp.net', 30 * 3600e3],
    ['5511900000002@s.whatsapp.net', 6 * DIA],
    ['5511900000003@s.whatsapp.net', 2 * DIA],
    ['5511900000004@s.whatsapp.net', 26 * 3600e3, { resposta: true }],
    ['5511900000005@s.whatsapp.net', 40 * DIA],
    ['120363000000000004@g.us', 3 * DIA],
    [null, 3 * DIA],
  ]);
  return bancoFalso([
    ['5511900000002@s.whatsapp.net', 0, 5 * DIA],
    ['5511900000003@s.whatsapp.net', 0, 3 * DIA],
    ['120363000000000004@g.us', 1, 3 * DIA],
  ]);
}
const followup = { canal: 'whatsapp', jid: '5511900000099@s.whatsapp.net', conversa: 'EMPRESA_NOVA', chave: 'f1', campanha: 'regua|EMPRESA_NOVA|1', followup: true, texto: 'Bom dia! Conseguiram olhar a proposta de ontem?' };
const resposta = { canal: 'whatsapp', jid: '5511900000099@s.whatsapp.net', conversa: 'EMPRESA_NOVA', chave: 'r1', campanha: 'responder|EMPRESA_NOVA|1', followup: false, texto: 'Opa, consigo sim, mando agora.' };

test('B04 conta as mensagens de iniciativa no privado que ninguem respondeu em 30 dias', () => {
  const gov = governador();
  const db = cenario();
  assert.deepStrictEqual(gov.semResposta(Date.now(), db), { mensagens: 4, contatos: 2, dias: 30 });
  assert.strictEqual(gov.semResposta(Date.now(), null), null);
});

test('B05 sem teto (padrao), so mede: o status mostra o numero e nada segura', () => {
  const gov = governador();
  const db = cenario();
  const st = gov.status(Date.now(), db);
  assert.strictEqual(st.sem_resposta_30d.mensagens, 4);
  assert.strictEqual(st.teto_sem_resposta_30d, 'so mede');
  assert.doesNotMatch(gov.motivo(followup, Date.now(), db) || '', /sem resposta/);
});

test('B06 com teto ligado e atingido, follow-up segura e resposta passa', () => {
  const gov = governador({ OZAV_WPP_SEM_RESPOSTA_30D: '4' });
  const db = cenario();
  assert.match(gov.motivo(followup, Date.now(), db) || '', /4 mensagens sem resposta no privado em 30 dias \(teto 4\)/);
  assert.strictEqual(gov.motivo(resposta, Date.now(), db), null);
  const folga = governador({ OZAV_WPP_SEM_RESPOSTA_30D: '5' });
  assert.doesNotMatch(folga.motivo(followup, Date.now(), db) || '', /sem resposta/);
});

test('B07 com teto ligado e sem o banco da captura, na duvida segura', () => {
  const gov = governador({ OZAV_WPP_SEM_RESPOSTA_30D: '50' });
  cenario();
  assert.match(gov.motivo(followup, Date.now(), null) || '', /sem o banco da captura/);
});

test('B08 o registrar grava o jid no livro (sem ele nao ha como contar)', () => {
  const gov = governador();
  limpar();
  const db = bancoFalso([['5511900000099@s.whatsapp.net', 0, DIA]]);
  gov.registrar(followup, db);
  const ultima = JSON.parse(fs.readFileSync(LIVRO, 'utf8').trim().split('\n').pop());
  assert.strictEqual(ultima.jid, '5511900000099@s.whatsapp.net');
});
