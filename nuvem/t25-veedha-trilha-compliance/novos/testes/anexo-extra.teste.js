/**
 * ANEXO NO PORTÃO, além do contrato do V02 (tarefa 25 da nuvem, 14/10/2026; regra R55).
 *
 *   node --test testes/anexo-extra.teste.js
 *
 * O contrato mínimo mora em testes/v02-anexo.teste.js (escrito pela conversa dona). Aqui vai o que a
 * tarefa 25 pôs por cima: a lista de anexos aprovados pelo sha256 (vazia por padrão), anexo malformado,
 * texto extraído vazio, produto no anexo acionando o suitability, a dispensa de rodapé que não vale com
 * anexo, ofuscação dentro do anexo e o motivo que diz QUAL anexo barrou. Texto sintético.
 */
'use strict';

process.env.VEEDHA_MODO_TESTE = '1';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const RAIZ = path.resolve(__dirname, '..');
const { montarMotor, PRESETS } = require(path.join(RAIZ, 'redteam', 'executor.js'));
const { RODAPE_DE_TESTE } = require(path.join(RAIZ, 'testes', 'portao.teste.js'));

const P = montarMotor().portao;
const comRodape = (t) => `${t}\n\n${RODAPE_DE_TESTE}`;
const TEXTO = 'Bom dia Cliente! Tudo bem? Segue em anexo o material que a gente conversou. Qualquer coisa me chama.';
const HASH = crypto.createHash('sha256').update('convite sintetico').digest('hex');
const r55 = (r) => r.bloqueios.filter((b) => b.regra === 'R55');

/** Uma cópia do motor com uma lista de anexos aprovados escrita antes de carregar o portão. */
function motorComAnexos(aprovados) {
  const { raiz } = montarMotor();
  const cfg = JSON.parse(fs.readFileSync(path.join(raiz, 'config', 'modelos.json'), 'utf8'));
  const lista = aprovados(cfg.aprovadores[0]);
  fs.writeFileSync(path.join(raiz, 'config', 'anexos-aprovados.json'), JSON.stringify({ aprovados: lista }));
  for (const k of Object.keys(require.cache)) if (k.startsWith(raiz)) delete require.cache[k];
  return require(path.join(raiz, 'lib', 'portao.js'));
}

test('A01 sha256 fora da lista de anexos aprovados (vazia por padrao): BLOQUEADO R55', () => {
  const r = P.verificar(comRodape(TEXTO), { ...PRESETS.cliente(), anexos: [{ nome: 'convite.pdf', sha256: HASH }] });
  assert.equal(r.veredito, 'BLOQUEADO');
  assert.ok(r55(r).length && /lista de anexos aprovados/.test(r55(r)[0].motivo), JSON.stringify(r.bloqueios));
  assert.deepEqual(P.ANEXOS_APROVADOS, []);
});

test('A02 sha256 aprovado por quem esta na lista fechada: julgado, mas sai no maximo REVISAR', () => {
  const Q = motorComAnexos((quem) => [{ sha256: HASH, nome: 'convite.pdf', aprovadoPor: quem, aprovadoEm: '2026-09-01' }]);
  const r = Q.verificar(comRodape(TEXTO), { ...PRESETS.cliente(), anexos: [{ nome: 'convite.pdf', sha256: HASH.toUpperCase() }] });
  assert.equal(r.veredito, 'REVISAR', JSON.stringify(r.bloqueios));
  assert.ok(r.revisar.some((x) => x.regra === 'R55' && /aprovado pelo sha256/.test(x.motivo)));
  // aprovador fora da lista, data no futuro ou hash malformado nao aprovam nada
  const R = motorComAnexos(() => [
    { sha256: HASH, aprovadoPor: 'Alguem Fora Da Lista', aprovadoEm: '2026-09-01' },
    { sha256: 'abc', aprovadoPor: 'x', aprovadoEm: '2026-09-01' },
  ]);
  assert.deepEqual(R.ANEXOS_APROVADOS, []);
  assert.equal(R.verificar(comRodape(TEXTO), { ...PRESETS.cliente(), anexos: [{ nome: 'convite.pdf', sha256: HASH }] }).veredito, 'BLOQUEADO');
});

test('A03 lista de anexos malformada e decidir no escuro: BLOQUEADO R35', () => {
  for (const anexos of ['extrato.pdf', [null], [{}], [{ nome: '   ' }], [{ nome: 'a.pdf', texto: 5 }], [{ nome: 'a.pdf', sha256: 7 }], [{ nome: 'a.pdf', texto: 'x'.repeat(400001) }]]) {
    const r = P.verificar(comRodape(TEXTO), { ...PRESETS.cliente(), anexos });
    assert.equal(r.veredito, 'BLOQUEADO', JSON.stringify(anexos).slice(0, 60));
    assert.ok(r.bloqueios.some((b) => b.regra === 'R35' && /anexos/.test(b.motivo)), JSON.stringify(r.bloqueios).slice(0, 200));
  }
});

test('A04 texto extraido vazio (PDF escaneado, imagem) conta como nao lido: BLOQUEADO R55', () => {
  const r = P.verificar(comRodape(TEXTO), { ...PRESETS.cliente(), anexos: [{ nome: 'print.png', texto: ' \n ' }] });
  assert.equal(r.veredito, 'BLOQUEADO');
  assert.equal(r55(r).length, 1);
});

test('A05 produto dentro do anexo aciona o suitability como no corpo', () => {
  const lamina = [{ nome: 'lamina.pdf', texto: 'Conheca o CDB do banco parceiro, com liquidez diaria.' }];
  const prospect = P.verificar(comRodape(TEXTO), { ...PRESETS.prospect(), anexos: lamina });
  assert.equal(prospect.veredito, 'BLOQUEADO');
  assert.ok(prospect.bloqueios.some((b) => b.regra === 'R15'), JSON.stringify(prospect.bloqueios).slice(0, 300));
  const vencido = P.verificar(comRodape(TEXTO), { ...PRESETS.vencido(), anexos: lamina });
  assert.ok(vencido.bloqueios.some((b) => b.regra === 'R16'));
});

test('A06 com anexo nao ha dispensa de rodape: anexo e material (config real, rodape oficial ainda vazio)', () => {
  const real = montarMotor({ real: true }).portao;
  const conversa = 'Bom dia Cliente! Tudo bem? Consegue falar amanha as 10h?';
  const sem = real.verificar(conversa, { ...PRESETS.cliente() });
  if (real.DISPENSA_CONVERSA_PURA.ligado) assert.equal(sem.veredito, 'REVISAR', 'sem anexo, a conversa pura continua dispensada');
  const com = real.verificar(conversa, { ...PRESETS.cliente(), anexos: [{ nome: 'convite.pdf', texto: 'Convite para uma conversa no escritorio.' }] });
  assert.equal(com.veredito, 'BLOQUEADO');
  assert.ok(com.bloqueios.some((b) => b.regra === 'R08'), 'o rodape volta a ser exigido');
});

test('A07 ofuscacao dentro do anexo barra como no corpo, e o motivo diz qual anexo', () => {
  const r = P.verificar(comRodape(TEXTO), {
    ...PRESETS.cliente(),
    anexos: [
      { nome: 'convite.pdf', texto: 'Convite para uma conversa no escritorio.' },
      { nome: 'resumo.pdf', texto: 'Sua cus​todia: R$ 900.000,00 aplicados.' },
    ],
  });
  assert.equal(r.veredito, 'BLOQUEADO');
  assert.ok(r.bloqueios.every((b) => /anexo "resumo\.pdf"/.test(b.motivo)), JSON.stringify(r.bloqueios.map((b) => b.motivo.slice(0, 60))));
  assert.ok(!r.bloqueios.some((b) => /convite\.pdf/.test(b.motivo)), 'o anexo inofensivo nao barra');
});

test('A08 o portao exportado segue congelado e anuncia o arquivo novo do config', () => {
  assert.ok(Object.isFrozen(P.ANEXOS_APROVADOS));
  assert.equal(P.CONFIG.anexos, 'config/anexos-aprovados.json');
  assert.ok(P.REGRAS.R55 && P.REGRAS.R55.ids.includes('res178-art25-VII'));
});
