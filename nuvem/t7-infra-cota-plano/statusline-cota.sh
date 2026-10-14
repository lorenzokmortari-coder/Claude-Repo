#!/usr/bin/env bash
# Barra de status do Claude Code com a cota real do plano (5 h e 7 dias) e registro de no máximo
# 1 linha por minuto em ~/.claude/cota.jsonl. Mesma saída do statusline-cota.mjs, para quem não
# tem Node: só bash 5 (o do Git Bash). Não usa jq (o Git Bash não traz) nem date.
#
# No Git Bash do Windows cada $(...) ou comando externo custa um fork lento. Por isso as funções
# devolvem o resultado na variável R, a hora sai do printf '%(...)T' do próprio bash e, no caminho
# normal, o script não cria nenhum processo.
#
# Campos (code.claude.com/docs/en/statusline, conferido em 14/10/2026): rate_limits.five_hour e
# rate_limits.seven_day com used_percentage (0-100) e resets_at (epoch em segundos); model.id,
# model.display_name, session_id, workspace.current_dir, context_window.used_percentage.
#
# Settings (~/.claude/settings.json), com barras normais no caminho (o Git Bash come as invertidas):
#   "statusLine": { "type": "command", "command": "bash ~/.claude/statusline-cota.sh", "refreshInterval": 60 }
# Opcional: ~/.claude/cota-base.txt com o comando da barra que você já usava.
# Só para teste: COTA_DIR (pasta no lugar de ~/.claude) e COTA_AGORA (epoch fixo).

IFS= read -r -d '' entrada
dir="${COTA_DIR:-$HOME/.claude}"
arquivo="$dir/cota.jsonl"
estado="$dir/cota.ultimo"
dias=(dom seg ter qua qui sex sáb)
verde=$'\e[32m'; amarelo=$'\e[33m'; vermelho=$'\e[31m'; cinza=$'\e[2m'; fim=$'\e[0m'

# Conteúdo de um objeto "chave":{...} sem objeto aninhado (vale para five_hour, seven_day, model).
objeto() { R=""; local re="\"$1\"[[:space:]]*:[[:space:]]*\\{([^{}]*)\\}"; [[ $2 =~ $re ]] && R=${BASH_REMATCH[1]}; }
numero() { R=""; local re="\"$1\"[[:space:]]*:[[:space:]]*(-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?)"; [[ $2 =~ $re ]] && R=${BASH_REMATCH[1]}; }
texto() { R=""; local re="\"$1\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\""; [[ $2 =~ $re ]] && R=${BASH_REMATCH[1]}; }
# Arredonda meio para cima (23,5 -> 24), como o Math.round do Node.
inteiro() {
  local v=${1:-0} i f
  i=${v%%.*}; [[ $v == *.* ]] && f=${v#*.} || f=0
  [[ -z $i || $i == "-" ]] && i=0
  f=${f:0:1}; [[ $f =~ ^[0-9]$ ]] || f=0
  (( f >= 5 )) && i=$(( i + 1 ))
  R=$i
}
hora_de() { printf -v R "%($1)T" "$2"; }

objeto five_hour "$entrada"; j5=$R
objeto seven_day "$entrada"; j7=$R
numero used_percentage "$j5"; p5=$R
numero resets_at "$j5"; r5=${R%%.*}
numero used_percentage "$j7"; p7=$R
numero resets_at "$j7"; r7=${R%%.*}
objeto model "$entrada"; modelo_obj=$R
texto id "$modelo_obj"; modelo_id=$R
texto display_name "$modelo_obj"; modelo_nome=$R
texto session_id "$entrada"; sessao=$R
texto current_dir "$entrada"; pasta=$R
[[ -z $pasta ]] && { texto cwd "$entrada"; pasta=$R; }
ctx_bloco=${entrada#*\"context_window\"}; [[ $ctx_bloco == "$entrada" ]] && ctx_bloco=""
ctx_bloco=${ctx_bloco%%\"rate_limits\"*}
numero used_percentage "$ctx_bloco"; ctx=$R

agora=${COTA_AGORA:-$EPOCHSECONDS}
[[ -z $agora ]] && printf -v agora '%(%s)T' -1

# ---- registro: no máximo 1 linha por minuto, só quando alguma janela veio
if [[ -n $p5 || -n $p7 ]]; then
  hora_de '%Y-%m-%dT%H:%M:%S%z' "$agora"; hora="${R:0:22}:${R:22:2}"
  minuto=${hora:0:16}
  ultimo=""; [[ -f $estado ]] && read -r ultimo < "$estado"
  if [[ $minuto != "$ultimo" ]]; then
    js() { if [[ -n $1 ]]; then R="\"$1\""; else R=null; fi; }
    js "$modelo_id"; jm=$R; js "$modelo_nome"; jn=$R; js "$sessao"; js_s=$R
    [[ -d $dir ]] || mkdir -p "$dir" 2>/dev/null
    printf '{"hora":"%s","pct_5h":%s,"reset_5h":%s,"pct_7d":%s,"reset_7d":%s,"modelo":%s,"modelo_nome":%s,"sessao":%s}\n' \
      "$hora" "${p5:-null}" "${r5:-null}" "${p7:-null}" "${r7:-null}" "$jm" "$jn" "$js_s" >> "$arquivo" 2>/dev/null \
      && printf '%s' "$minuto" > "$estado" 2>/dev/null
  fi
fi

# ---- barra
cor() { inteiro "$1"; if (( R >= 80 )); then R=$vermelho; elif (( R >= 50 )); then R=$amarelo; else R=$verde; fi; }
blocos() {
  local cheios i s=""
  inteiro "$1"; cheios=$(( (R + 5) / 10 )); (( cheios > 10 )) && cheios=10; (( cheios < 0 )) && cheios=0
  for (( i = 0; i < 10; i++ )); do if (( i < cheios )); then s+="▓"; else s+="░"; fi; done
  R=$s
}
quando() {
  local hm dia hoje w
  hora_de '%H:%M' "$1"; hm=$R; hora_de '%Y-%m-%d' "$1"; dia=$R; hora_de '%Y-%m-%d' "$agora"; hoje=$R
  if [[ $dia == "$hoje" ]]; then R=$hm; else hora_de '%w' "$1"; w=$R; R="${dias[$w]} $hm"; fi
}

principal=""
if [[ -f "$dir/cota-base.txt" ]]; then
  IFS= read -r base < "$dir/cota-base.txt"; base=${base%$'\r'}
  [[ -n $base ]] && principal=$(printf '%s' "$entrada" | timeout 2.5 bash -c "$base" 2>/dev/null)
fi
if [[ -z $principal ]]; then
  principal="[${modelo_nome:-${modelo_id:-?}}]"
  base_pasta=${pasta//\\\\//}; base_pasta=${base_pasta%/}; base_pasta=${base_pasta##*/}
  [[ -n $base_pasta ]] && principal+=" $base_pasta"
  if [[ -n $ctx ]]; then inteiro "$ctx"; principal+=" | ctx $R%"; else principal+=" | ctx --"; fi
fi

cota=""
if [[ -n $p5 ]]; then
  cor "$p5"; c=$R; blocos "$p5"; b=$R; inteiro "$p5"
  cota="5h $c$b $R%$fim"
  [[ -n $r5 ]] && { quando "$r5"; cota+=" ${cinza}↻$R$fim"; }
fi
if [[ -n $p7 ]]; then
  cor "$p7"; c=$R; inteiro "$p7"
  parte="7d $c$R%$fim"
  [[ -n $r7 ]] && { quando "$r7"; parte+=" ${cinza}↻$R$fim"; }
  cota+="${cota:+ · }$parte"
fi

if [[ -z $cota ]]; then printf '%s\n' "$principal"
elif [[ $principal == *$'\n'* ]]; then printf '%s\n%s\n' "$principal" "$cota"
else printf '%s | %s\n' "$principal" "$cota"; fi
