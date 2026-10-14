/**
 * Tarefa 20 (nuvem, 14/10/2026): a dispensa de rodape em conversa pura (decisao do Lorenzo, 23/09/2026) nao pode valer
 * para mensagem que nomeia produto ou fala de movimentar dinheiro. Config REAL (rodape oficial vazio).
 *
 *   node --test testes/dispensa.teste.js        (da raiz do motor; precisa de redteam/ da tarefa 14)
 *
 * Antes do patch 01, os 9 primeiros casos saem REVISAR, sem rodape. Depois, BLOQUEADO so pela R08. As conversas puras
 * (inclusive os 5 modelos aprovados, sem rodape) continuam REVISAR. DADO PESSOAL: nenhum.
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { montarMotor, PRESETS } = require('../redteam/executor.js');
const P = montarMotor({ real: true }).portao;
const v = (t) => P.verificar(t, PRESETS.cliente());

const COM_PRODUTO_OU_DINHEIRO = [
  'Bom dia Cliente! Tudo bem? A XP publicou um relatorio novo sobre renda fixa. Se quiser, me responde aqui que a gente conversa.',
  'Oi Cliente, tudo bem? Queria te mostrar uma ideia de bitcoin. Me liga quando puder.',
  'Oi Cliente, tudo bem? Tem um titulo publico que eu queria te mostrar. Me liga quando puder.',
  'Oi Cliente, tudo bem? Queria falar do multimercado que vc comentou. Me chama.',
  'Oi Cliente, tudo bem? Que tal a gente olhar renda variavel na semana que vem? Me fala um horario.',
  'Bom dia Cliente! Tudo bem? Os dados pra depositar na sua conta da XP ficam no ambiente da XP, no seu nome. O deposito sai do seu banco direto pra la. Se travar em alguma parte, me chama.',
  'Oi Cliente, tudo bem? Faz o pix pra sua conta da XP quando puder. Me chama se travar.',
  'Oi Cliente, tudo bem? A TED pra sua conta da XP ja pode ser feita. Qualquer coisa me chama.',
  'Oi Cliente, tudo bem? A transferencia pra sua conta da XP sai do seu banco. Qualquer coisa me chama.',
];
const CONVERSA_PURA = [
  'oi, tudo bem? me chama quando puder, abs',
  'Bom dia Cliente! Tudo bem? Faz um tempo que a gente nao conversa. Me fala um horario bom pra gente conversar?',
  'Bom dia Cliente! Tudo bem? Queria marcar a nossa conversa de revisao. quinta-feira as 10:00 funciona pra vc? Se nao der, me fala outro horario.',
];

test('D01 mensagem com produto ou movimentacao de dinheiro nao dispensa o rodape (BLOQUEADO so pela R08)', () => {
  const escaparam = COM_PRODUTO_OU_DINHEIRO.map((t) => [t, v(t)]).filter(([, r]) => r.veredito !== 'BLOQUEADO' || r.bloqueios.some((b) => b.regra !== 'R08'));
  assert.equal(escaparam.length, 0, escaparam.map(([t, r]) => `${r.veredito}: ${t.slice(0, 70)}`).join('\n'));
});

test('D02 conversa pura continua dispensando o rodape (REVISAR)', () => {
  for (const t of CONVERSA_PURA) assert.equal(v(t).veredito, 'REVISAR', t);
});

test('D03 os 5 modelos aprovados, sem rodape, continuam REVISAR (a decisao de 23/09 fica de pe)', () => {
  const cfg = require(path.join(__dirname, '..', 'config', 'modelos.json'));
  const ex = { primeiroNome: 'Cliente', data: '20/11', hora: '10:00', diaDaSemana: 'quinta-feira' };
  for (const m of cfg.modelos) {
    const t = m.corpo.replace(/\{(\w+)\}/g, (_, k) => ex[k]);
    assert.equal(v(t).veredito, 'REVISAR', m.id);
  }
});
