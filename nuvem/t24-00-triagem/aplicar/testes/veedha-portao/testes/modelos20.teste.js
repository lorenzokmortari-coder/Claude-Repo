/**
 * Tarefa 20 (nuvem, 14/10/2026): as 30 propostas de modelo de modelos20/modelos.json, no portao real.
 *
 *   node --test testes/modelos20.teste.js       (da raiz do motor; precisa de redteam/ da tarefa 14 e de modelos20/)
 *
 * Cada modelo tem de dar o veredito esperado no config de teste (REVISAR, sem bloqueio), no config real de hoje
 * (conversa pura REVISAR; com produto ou dinheiro, BLOQUEADO so pela R08) e, se for candidato a LIVRE, ser aceito na
 * carga e sair LIVRE como instancia exata. Sem o patch 01, M29 e M30 falham no config real (saem sem rodape).
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { main } = require('../modelos20/rodar.js');

test('M01-M30: veredito esperado nas tres conferencias', () => {
  const log = console.log;
  console.log = () => {};
  let res;
  try {
    res = main();
  } finally {
    console.log = log;
    process.exitCode = 0;
  }
  const ruins = res.filter((r) => !r.ok).map((r) => `${r.id}: teste ${r.teste}, real ${r.real} (${r.regrasReal}), livre ${r.livre}`);
  assert.equal(res.length, 30);
  assert.equal(ruins.length, 0, ruins.join('\n'));
});
