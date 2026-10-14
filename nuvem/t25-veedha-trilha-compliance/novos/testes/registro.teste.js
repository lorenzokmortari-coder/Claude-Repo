/**
 * REGISTRO DE SAÍDA, além do contrato do V01 (tarefa 25 da nuvem, 14/10/2026).
 *
 *   node --test testes/registro.teste.js
 *
 * O contrato mínimo mora em testes/v01-log-de-saida.teste.js (escrito pela conversa dona). Aqui vai o
 * que a tarefa 25 pôs por cima: a cadeia de hash, a virada do ano, o `verificar` que aponta a primeira
 * linha adulterada, o `consultar`, a falha fechada por link para o OneDrive, por arquivo corrompido e
 * por veredito que não sai, a trava entre processos e a função que a fila chama. Tudo em pasta
 * temporária, com texto sintético e telefone do bloco de teste (5511900000xxx).
 */
'use strict';

process.env.VEEDHA_MODO_TESTE = '1';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const RAIZ = path.resolve(__dirname, '..');
const MODULO = path.join(RAIZ, 'lib', 'registro.js');
const R = () => require(MODULO);
const pasta = () => fs.mkdtempSync(path.join(os.tmpdir(), 'veedha-registro-'));
const saida = (n, extra = {}) => ({
  id: `fila-${String(n).padStart(4, '0')}`,
  destino: `55119000000${String(n % 100).padStart(2, '0')}`,
  canal: 'whatsapp_pessoal',
  texto: `Bom dia Cliente! Tudo bem? Mensagem sintetica numero ${n}.`,
  veredito: 'REVISAR',
  regras: ['R38'],
  aprovadoPor: 'Aprovador de Teste',
  aprovadoEm: '2026-10-14T12:00:00.000Z',
  em: '2026-10-14T13:00:00.000Z',
  ...extra,
});
const linhas = (arq) => fs.readFileSync(arq, 'utf8').split('\n').filter(Boolean);

test('X01 cada linha leva o hash da anterior e o verificar confere a cadeia inteira', () => {
  const raiz = pasta();
  const a = R().registrar(saida(1), { raiz });
  const b = R().registrar(saida(2), { raiz });
  const c = R().registrar(saida(3), { raiz });
  assert.deepEqual([a.seq, b.seq, c.seq], [1, 2, 3]);
  assert.equal(a.hashAnterior, '0'.repeat(64));
  assert.equal(b.hashAnterior, a.hash);
  assert.equal(c.hashAnterior, b.hash);
  assert.deepEqual(R().ler({ raiz }).map((r) => r.id), ['fila-0001', 'fila-0002', 'fila-0003']);
  const v = R().verificarCadeia({ raiz });
  assert.equal(v.ok, true);
  assert.equal(v.total, 3);
  assert.ok(R().ler({ raiz }).every((r) => typeof r.registradoEm === 'string' && r.registradoEm.length >= 20), 'hora do servidor em todo registro');
});

test('X02 um arquivo por ano, e a cadeia atravessa a virada', () => {
  const raiz = pasta();
  const a = R().registrar(saida(1), { raiz, agora: '2026-12-31T23:59:00.000Z' });
  const b = R().registrar(saida(2), { raiz, agora: '2027-01-01T00:01:00.000Z' });
  assert.deepEqual(fs.readdirSync(raiz).filter((n) => n.endsWith('.jsonl')).sort(), ['registro-2026.jsonl', 'registro-2027.jsonl']);
  assert.equal(b.hashAnterior, a.hash);
  assert.equal(R().verificarCadeia({ raiz }).ok, true);
  // relógio que volta não abre o arquivo do ano velho: a linha vai para o mais novo, e a cadeia segue
  const c = R().registrar(saida(3), { raiz, agora: '2026-06-01T10:00:00.000Z' });
  assert.equal(linhas(path.join(raiz, 'registro-2027.jsonl')).length, 2);
  assert.equal(c.hashAnterior, b.hash);
  assert.equal(R().verificarCadeia({ raiz }).ok, true);
});

test('X03 linha alterada: o verificar aponta arquivo e linha, sai 1, e nada mais se grava nem se le calado', () => {
  const raiz = pasta();
  for (const n of [1, 2, 3]) R().registrar(saida(n), { raiz, agora: '2026-10-14T13:00:00.000Z' });
  const arq = path.join(raiz, 'registro-2026.jsonl');
  const ls = linhas(arq);
  const mexida = JSON.parse(ls[1]);
  mexida.texto = 'texto trocado depois do envio';
  ls[1] = JSON.stringify(mexida);
  fs.writeFileSync(arq, ls.join('\n') + '\n');
  const v = R().verificarCadeia({ raiz });
  assert.equal(v.ok, false);
  assert.deepEqual([v.problema.arquivo, v.problema.linha], ['registro-2026.jsonl', 2]);
  assert.match(v.problema.motivo, /alterada/);
  const cli = spawnSync(process.execPath, [MODULO, 'verificar', '--raiz', raiz], { encoding: 'utf8' });
  assert.equal(cli.status, 1);
  assert.match(cli.stdout, /registro-2026\.jsonl:2/);
  assert.throws(() => R().registrar(saida(4), { raiz }), /cadeia quebrada/);
  assert.throws(() => R().ler({ raiz }), /cadeia quebrada/);
});

test('X04 linha apagada no meio tambem quebra a cadeia, na linha seguinte ao buraco', () => {
  const raiz = pasta();
  for (const n of [1, 2, 3]) R().registrar(saida(n), { raiz, agora: '2026-10-14T13:00:00.000Z' });
  const arq = path.join(raiz, 'registro-2026.jsonl');
  const ls = linhas(arq);
  fs.writeFileSync(arq, [ls[0], ls[2]].join('\n') + '\n');
  const v = R().verificarCadeia({ raiz });
  assert.equal(v.ok, false);
  assert.equal(v.problema.linha, 2);
});

test('X05 arquivo corrompido (linha cortada): falha fechada, a proxima mensagem nao se grava', () => {
  const raiz = pasta();
  R().registrar(saida(1), { raiz, agora: '2026-10-14T13:00:00.000Z' });
  fs.appendFileSync(path.join(raiz, 'registro-2026.jsonl'), '{"seq":2,"id":"fila-00');
  assert.throws(() => R().registrar(saida(2), { raiz, agora: '2026-10-14T13:00:00.000Z' }), /cadeia quebrada|nao e JSON/);
});

test('X06 consultar: o que foi enviado a um destino num periodo (e pela linha de comando)', () => {
  const raiz = pasta();
  R().registrar(saida(1, { destino: '5511900000001', em: '2026-03-02T10:00:00.000Z' }), { raiz });
  R().registrar(saida(2, { destino: '5511900000001', em: '2026-03-20T10:00:00.000Z' }), { raiz });
  R().registrar(saida(3, { destino: '5511900000002', em: '2026-03-21T10:00:00.000Z' }), { raiz });
  R().registrar(saida(4, { destino: '5511900000001', em: '2026-04-01T10:00:00.000Z' }), { raiz });
  const marco = R().consultar({ raiz, destino: '5511900000001', de: '2026-03-01', ate: '2026-03-31' });
  assert.deepEqual(marco.map((r) => r.id), ['fila-0001', 'fila-0002']);
  assert.throws(() => R().consultar({ raiz, de: '01/03/2026' }), /AAAA-MM-DD/);
  const cli = spawnSync(process.execPath, [MODULO, 'consultar', '--destino', '5511900000001', '--de', '2026-03-01', '--ate', '2026-03-31', '--raiz', raiz], { encoding: 'utf8' });
  assert.equal(cli.status, 0, cli.stderr);
  assert.equal(cli.stdout.trim().split('\n').length, 2);
  assert.equal(JSON.parse(cli.stdout.trim().split('\n')[0]).texto, saida(1).texto);
});

test('X07 pasta sincronizada por link ou junction tambem recusa (e Dropbox, Google Drive, iCloud)', () => {
  const base = pasta();
  const sincronizada = path.join(base, 'OneDrive - Pessoal', 'dados');
  fs.mkdirSync(sincronizada, { recursive: true });
  const link = path.join(base, 'dados-de-cliente');
  fs.symlinkSync(sincronizada, link, 'junction');
  assert.throws(() => R().registrar(saida(1), { raiz: path.join(link, 'registro') }), /sincronizad/i);
  for (const nome of ['Dropbox', 'Google Drive', 'iCloudDrive']) {
    assert.throws(() => R().registrar(saida(1), { raiz: path.join(base, nome, 'registro') }), /sincronizad/i, nome);
  }
  assert.equal(fs.existsSync(path.join(sincronizada, 'registro')), false, 'nada pode ser criado dentro da pasta sincronizada');
});

test('X08 so sai o que o portao deixou sair: BLOQUEADO, REVISAR sem aprovacao e campo faltando recusam, sem gravar nada', () => {
  const raiz = pasta();
  assert.throws(() => R().registrar(saida(1, { veredito: 'BLOQUEADO' }), { raiz }), /nao sai/);
  assert.throws(() => R().registrar(saida(2, { aprovadoPor: null }), { raiz }), /aprovacao humana/);
  assert.throws(() => R().registrar(saida(3, { aprovadoEm: 'ontem' }), { raiz }), /aprovadoEm/);
  assert.throws(() => R().registrar(saida(4, { texto: '  ' }), { raiz }), /sem texto/);
  assert.throws(() => R().registrar(saida(5, { destino: undefined }), { raiz }), /sem destino/);
  assert.deepEqual(R().ler({ raiz }), []);
  const livre = R().registrar(saida(6, { veredito: 'LIVRE', aprovadoPor: null, aprovadoEm: null }), { raiz });
  assert.equal(livre.seq, 1, 'LIVRE (instancia de modelo aprovado) nao pede aprovacao por mensagem');
});

test('X09 a API nao tem como apagar nada, e o modulo e congelado', () => {
  const m = R();
  assert.ok(Object.isFrozen(m));
  const proibidas = Object.keys(m).filter((k) => /apagar|remover|limpar|truncar|delet|excluir|reescrever/i.test(k));
  assert.deepEqual(proibidas, []);
  assert.equal(m.RETENCAO_ANOS, 5);
  assert.equal(m.podeExpurgar({ em: '2021-10-14T00:00:00.000Z' }, '2026-10-13T23:59:59.000Z'), false, 'um segundo antes dos 5 anos');
  assert.equal(m.podeExpurgar({ em: '2021-10-14T00:00:00.000Z' }, '2026-10-14T00:00:00.000Z'), true);
  assert.equal(m.podeExpurgar({ em: 'data ruim' }, '2040-01-01T00:00:00.000Z'), false, 'sem data legivel nao se prova a idade');
});

test('X10 registrarSaida (o que a fila chama): junta as regras do julgamento e falha com code SEM_REGISTRO', () => {
  const raiz = pasta();
  const julgamento = { veredito: 'REVISAR', passou: true, bloqueios: [], revisar: [{ regra: 'R38' }, { regra: 'R37' }], avisos: [{ regra: 'R05' }] };
  const item = { id: 'fila-0001', destino: '5511900000001', canal: 'email', texto: 'Ola Cliente, tudo bem?', aprovadoPor: 'Aprovador de Teste', aprovadoEm: '2026-10-14T12:00:00.000Z' };
  const reg = R().registrarSaida(item, julgamento, { raiz });
  assert.deepEqual(reg.regras, ['R05', 'R37', 'R38']);
  assert.equal(reg.veredito, 'REVISAR');
  for (const ruim of [{ veredito: 'BLOQUEADO', passou: false }, null, { veredito: 'LIVRE', passou: false }]) {
    assert.throws(() => R().registrarSaida({ ...item, id: 'x' + Math.random() }, ruim, { raiz }), (e) => e.code === 'SEM_REGISTRO');
  }
  assert.throws(() => R().registrarSaida(item, julgamento, { raiz }), (e) => e.code === 'SEM_REGISTRO' && /ja registrado/.test(e.message));
});

test('X11 o arquivo nasce so com permissao do dono (600) e a pasta 700', { skip: process.platform === 'win32' }, () => {
  const raiz = path.join(pasta(), 'nova');
  R().registrar(saida(1), { raiz, agora: '2026-10-14T13:00:00.000Z' });
  assert.equal(fs.statSync(path.join(raiz, 'registro-2026.jsonl')).mode & 0o777, 0o600);
  assert.equal(fs.statSync(raiz).mode & 0o777, 0o700);
});

test('X12 quatro processos gravando juntos: 40 registros, nenhum perdido, cadeia inteira', async () => {
  const raiz = pasta();
  const filho = (k) =>
    new Promise((ok, falhou) => {
      const codigo = `const R=require(${JSON.stringify(MODULO)});for(let i=0;i<10;i++)R.registrar({id:'p${k}-'+i,destino:'5511900000001',canal:'email',texto:'sintetico '+i,veredito:'LIVRE'},{raiz:${JSON.stringify(raiz)}});`;
      const p = spawn(process.execPath, ['-e', codigo], { stdio: 'inherit' });
      p.on('exit', (c) => (c === 0 ? ok() : falhou(new Error(`processo ${k} saiu com ${c}`))));
    });
  await Promise.all([0, 1, 2, 3].map(filho));
  const v = R().verificarCadeia({ raiz });
  assert.equal(v.ok, true, v.problema && v.problema.motivo);
  assert.equal(v.total, 40);
});
