/**
 * RED TEAM DO PORTÃO (tarefa 14 da nuvem, 14/10/2026): os patches 01 a 07, contra o corpus sintético.
 *
 *   node --test testes/redteam.teste.js          (Node 20+; sem dependência; ~5 s)
 *
 * Cada teste Pxx lista as mensagens do corpus (redteam/corpus.jsonl) que o patch de mesmo número
 * faz barrar: falha no código de 14/10/2026 e passa com o patch. Todos conferem também que nenhuma
 * mensagem que tem de passar (categoria deve-passar, sem marca de "aberto") passou a ser barrada.
 * O último teste é o corpus inteiro: nenhum caso fora do esperado sem marca de "aberto".
 * O portão roda numa cópia temporária (redteam/executor.js, montarMotor); o config real não é tocado.
 *
 * DADO PESSOAL: nenhum. O corpus é sintético.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { montarMotor, rodar } = require('../redteam/executor.js');

const casos = fs.readFileSync(path.join(__dirname, '..', 'redteam', 'corpus.jsonl'), 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
const res = rodar(casos, montarMotor().portao);
const porId = new Map(res.map((x) => [x.id, x]));

function barra(ids) {
  const escaparam = ids.filter((id) => porId.get(id).obtido !== 'BLOQUEADO').map((id) => `${id} ${porId.get(id).obtido}: ${porId.get(id).texto.slice(0, 70)}`);
  assert.equal(escaparam.length, 0, `${escaparam.length} de ${ids.length} ainda escapam:\n  ${escaparam.join('\n  ')}`);
  const alarmes = res.filter((x) => x.categoria === 'deve-passar' && !x.aberto && x.obtido === 'BLOQUEADO').map((x) => `${x.id}: ${x.texto.slice(0, 70)}`);
  assert.equal(alarmes.length, 0, `mensagem legitima barrada:\n  ${alarmes.join('\n  ')}`);
}

test('P01 numero por extenso matava regras: "risco zero", "dois tercos do que voce tem", "duas vezes mais" com o 2 na fonte', () => {
  barra(['PR004', 'PR005', 'PR006', 'PR007', 'PR008', 'PR009', 'PR011', 'RE004', 'EX029']);
});

test('P02 promessa por sinonimo, com pontuacao no meio e em outra lingua ("nao perde um centavo", "risco? nenhum", "guaranteed return")', () => {
  barra(['PR001', 'PR012', 'PR013', 'PR014', 'PR016', 'PR017', 'PR019', 'PR020', 'PR021', 'PR022', 'PR024', 'PR026', 'PR027', 'PR028', 'PR029', 'PR030', 'PR031', 'PR032', 'PR033', 'PR034', 'PR035', 'PR036']);
});

test('P03 produto por extenso e sigla que faltava (LCA e CRI por extenso, titulo publico, FIDC) para quem nao tem perfil', () => {
  barra(['SU021', 'SU022', 'SU023', 'SU024', 'SU025', 'SU026']);
});

test('P04 print ou resumo da carteira do cliente e extrato (art. 25, VII), mesmo sem numero no texto', () => {
  barra(['EX026', 'EX027']);
});

test('P05 dinheiro em maos e para socio, procuracao por sinonimo e acesso por QR code, link e palavra-chave (art. 25, I, II e VI)', () => {
  barra(['DI012', 'DI013', 'DI014', 'PC008', 'PC009', 'PC010', 'PC011', 'PC012', 'PC013', 'SE013', 'SE014', 'SE015', 'SE016', 'SE017']);
});

test('P06 chamada para operar com pressa ("me confirma que eu reservo", "aplicar hoje", "fecha hoje que eu boleto")', () => {
  barra(['CT003', 'CT004', 'CT005']);
});

test('P07 ranking proprio e comparacao em giria ("o melhor CDB da XP", "humilha a poupanca", "uma vez e meia a poupanca")', () => {
  barra(['AN003', 'AN005', 'AN006', 'AN010', 'AN011', 'AN012']);
});

test('corpus inteiro: nenhum caso fora do esperado sem marca de "aberto", e nada sai LIVRE sem ser modelo', () => {
  const fora = res.filter((x) => x.resultado !== 'ok' && !x.aberto).map((x) => `${x.id} ${x.esperado}->${x.obtido}: ${x.texto.slice(0, 70)}`);
  assert.equal(fora.length, 0, `${fora.length} caso(s):\n  ${fora.join('\n  ')}`);
  assert.equal(res.filter((x) => x.obtido === 'LIVRE' && x.esperado !== 'LIVRE').length, 0);
});
