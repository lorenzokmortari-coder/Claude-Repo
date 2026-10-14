# Os testes da v2 rodados contra a v1 (14/10/2026)

**O que foi feito:** os 29 testes de `v2/test_legenda_reels.py` rodaram contra o código da v1 (`legenda_reels.py` e `gerar_teste.py` da tarefa 8).

**Ambiente:** Python 3.13, faster-whisper 1.2.1, PyAV 19.0.1, ffmpeg do sistema. Sem espeak-ng, então o vídeo de teste sai com bipes.

**Resultado:**
- na v1: **22 falham** e 7 passam;
- na v2: **29 passam** (no Python do sistema, sem faster-whisper, 28 passam e 1 pula, porque a reprodução do PyAV exige o faster-whisper instalado).

| Teste | v1 | v2 | O que prova |
|---|---|---|---|
| test_d1_transcrever_manda_ao_modelo_o_audio_decodificado_pelo_ffmpeg | falha | passa | D1: o áudio chega ao modelo como array float32 de 16 kHz, decodificado pelo ffmpeg, sem o PyAV |
| test_d1_reproduz_o_defeito_do_pyav_e_o_contorno | falha | passa | D1: o `decode_audio` do faster-whisper 1.2.1 cai em `TypeError ... metadata_errors` com o PyAV 19 (reproduzido aqui), e o da v2 funciona |
| test_d2_guia_vai_so_nos_png_e_o_mp4_sai_limpo | falha | passa | D2: o MP4 sai sem as caixas; os PNG de guia vêm à parte |
| test_d3_bloco_de_ate_16_caracteres_cabe_numa_linha_no_padrao | falha | passa | D3: bloco de até 16 caracteres numa linha só (largura de 0,50, espaço como meia letra) |
| test_d3_espaco_vale_meia_letra | falha | passa | D3: a medida da largura |
| test_d4_numero_partido_volta_a_ser_um_e_hora_vira_5H45 | falha | passa | D4: "5" ",45," vira "5H45,"; "5:45" vira "5H45"; "bom" "?" vira "bom?" |
| test_d4_preco_e_numero_comum_nao_viram_hora | falha | passa | D4: "5,45", "R$ 5,45" e "5,45 reais" ficam como preço |
| test_d4_transcrever_ja_entrega_o_numero_junto | falha | passa | D4: a transcrição já devolve o número junto |
| test_d5_nome_de_modelo_nao_colide_com_pasta_local | falha | passa | D5: "medium" vira `Systran/faster-whisper-medium` mesmo com uma pasta `medium` no lugar |
| test_d6_legenda_desce_para_62_por_cento_no_organico | falha | passa | D6: y = 62% de 1920; com `--zona anuncio`, fica limitado pela base de 35% |
| test_d7_toda_palavra_acende_mesmo_com_duracao_zero | falha | passa | D7: palavra de duração zero, ou com o mesmo início da seguinte, acende em exatamente um evento |
| test_d7_tempos_destaque_reparte_quando_nao_cabe | falha | passa | D7: o tempo é repartido quando não cabe |
| test_padroes_validados_no_pc | falha | passa | os padrões: medium, 5,8% (111 px), 2 a 3 palavras, 16 caracteres, 0,62, Arial Black, as mesmas cores |
| test_termos_vao_no_prompt_e_nos_hotwords_com_a_dica_coloquial | falha | passa | `--termos` vai no initial_prompt e nos hotwords, mais a dica de fala coloquial |
| test_revisar_grava_o_json_e_lista_so_as_palavras_duvidosas | falha | passa | o passo `revisar`: o palavras.json com "revisado": false e o revisar.txt só com as palavras de prob abaixo de 0,5, com tempo e contexto |
| test_queimar_so_com_o_json_revisado | falha | passa | o passo `queimar` recusa sem revisão; aceita com "revisado": true ou com o json editado; `--sem-revisar` avisa |
| test_palavras_json_da_v1_continua_legivel | falha | passa | o palavras.json da v1 (lista) continua legível |
| test_aviso_quando_o_video_ja_tem_legenda_queimada | falha | passa | o aviso de legenda já queimada: vídeo limpo não acusa; o com legenda branca e contorno acusa; o `revisar` avisa e não bloqueia |
| test_a_propria_saida_legendada_acusa_legenda | falha | passa | a saída da própria ferramenta acusa legenda |
| test_ass_um_destaque_por_evento_e_layout_estavel | falha | passa | teste da v1, ajustado ao tamanho novo (111 px) |
| test_transcrever_pede_tempo_por_palavra | falha | passa | teste da v1, ajustado ao modelo medium e ao áudio como array |
| test_ponta_a_ponta_video_sintetico | falha | passa | teste da v1, ajustado à revisão obrigatória (`--sem-revisar`) e a rodar sem espeak-ng |
| test_cor_tempo_e_trechos, test_quebra_de_linha_equilibrada, test_posicao_fica_dentro_da_area_segura, test_comparar_com_gabarito, test_video_de_celular_com_rotacao | passa | passa | testes da v1 sem mudança |
| test_blocos_equilibrados_sem_palavra_sozinha, test_pausa_e_frase_curta | passa | passa | testes da v1 que agora usam os limites da v1 de forma explícita (4 palavras, 22 caracteres): medem o algoritmo, e com o padrão novo uma palavra sozinha às vezes é inevitável |
