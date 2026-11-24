# Resultados do Agentless com o Claude Haiku 5.5

Registro dos resultados do Agentless com o **Claude Haiku 5.5 (esforço `medium`)** nas **47 issues do SWE-bench Lite-S** da amostra do estudo, com as **seis métricas** escolhidas (as quatro dos slides e as duas extras). Os números do Flash-Lite e do paper são as referências.

Dados brutos: `results/haiku_reduced/` (lote 1, 15 issues) e `results/haiku_reduced_ext/` (lote 2, 32 issues). Resumo gerado: `results/summary_agentless_haiku/RESUMO.md` e `por_issue.csv`. Descrição das métricas extras: `docs/METRICAS_NOVAS.md`.

> A issue isolada de teste (`psf__requests-2317`) rodou o pipeline completo, mas **não faz parte das 47** e não entra em nenhuma contagem.

---

## 1. Configuração da execução

| | Paper | Flash-Lite | **Haiku 5.5** |
|---|---|---|---|
| Modelo | GPT-4o (`gpt-4o-2024-05-13`) | Gemini 3.1 Flash-Lite | **claude-haiku-5-5** |
| Raciocínio | não | desligado | **esforço `medium`** (API nativa, `output_config.effort`) |
| Patches por issue | 4 × 10 = 40 | 2 × 3 = 6 | **2 × 3 = 6** |
| Testes de reprodução | 40 | 4 | **4** |
| Embeddings | `text-embedding-3-small` | `bge-small-en-v1.5` (local) | **`bge-small-en-v1.5` (local)** |
| Amostragem | temperatura 0,8 | temperatura 0,8 | **padrão do provedor** (a API recusa `temperature`) |
| Issues | 300 (Lite) | 47 (Lite-S) | **47 (Lite-S)**, em dois lotes (15 + 32) |

**Diferenças operacionais a registrar**
- Os containers de teste rodaram com `WORKERS=4` (lote 1) e `WORKERS=6` (lote 2). Isso muda só o tempo.
- **Quatro issues usaram imagens Docker oficiais do SWE-bench (Docker Hub)** em vez de construídas localmente, por falha de construção local: `matplotlib-23987`, `scikit-learn-25500`, `scikit-learn-25570` e `pylint-7993`. As do Flash-Lite foram todas construídas localmente.
- O Git global tem assinatura de commits ligada. Para o rerank não travar, ela foi desligada **só nos processos do pipeline** (variáveis `GIT_CONFIG_*` no `.env`).

---

## 2. As seis métricas

### Métrica 1: Taxa de resolução

| | Resolvidas | Taxa |
|---|---|---|
| Paper (GPT-4o, mesmas 47 issues) | 18/47 | 38,3% |
| Flash-Lite | 17/47 | 36,2% |
| **Haiku 5.5 (medium)** | **28/47** | **59,6%** |

Por lote: Haiku **10/15 (66,7%)** no lote 1 (paper 6/15, Flash-Lite 4/15) e **18/32 (56,2%)** no lote 2 (paper 12/32, Flash-Lite 13/32).

### Métrica 2: Teste de McNemar exato (pareado, mesmas issues)

| Comparação | Só Haiku | Só outro | Ambos | Nenhum | p |
|---|---|---|---|---|---|
| Haiku × Paper | 13 | 3 | 15 | 16 | **0,02** |
| Haiku × Flash-Lite | 13 | 2 | 15 | 17 | **0,007** |

### Métrica 3: Intervalo de confiança 95% (Wilson)

| | IC 95% |
|---|---|
| Paper (47 issues) | [26%, 53%] |
| Flash-Lite | [24%, 50%] |
| **Haiku 5.5** | **[45%, 72%]** |

### Métrica 4: Avaliação oráculo (algum candidato resolve?)

| | Selecionado | Oráculo | Perdidas na seleção |
|---|---|---|---|
| Flash-Lite | 17/47 (36,2%) | 19/47 (40,4%) | 2 |
| **Haiku 5.5** | **28/47 (59,6%)** | **33/47 (70,2%)** | **5** |

Issues do Haiku com patch correto gerado e não selecionado: `django-11815`, `matplotlib-25498`, `pytest-5221`, `scikit-learn-14983` e `sympy-14396`.
Foram avaliados os **197 candidatos distintos** (70 no lote 1 e 127 no lote 2).

### Métrica 5 (extra): Custo por issue resolvida, com tokens por etapa

Preços usados: US$ 0,10 por 1M de tokens de entrada e US$ 0,50 por 1M de saída (Artificial Analysis; confirmar no console).

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---:|---:|---:|
| Localização: arquivos (LLM) | 304.483 | 15.955 | 0,038 |
| Localização: arquivos irrelevantes | 309.183 | 36.189 | 0,049 |
| Localização: elementos relacionados | 336.849 | 28.094 | 0,048 |
| Localização: linhas de edição | 1.178.060 | 57.649 | 0,147 |
| Geração de patches | 748.674 | 494.172 | 0,322 |
| Testes de reprodução | 229.100 | 264.178 | 0,155 |
| Seleção de testes de regressão | 109.747 | 34.180 | 0,028 |
| **Total** | **3.216.096** | **930.417** | **0,787** |

| | Custo por issue | Custo por issue resolvida | Tokens por issue (entrada / saída) |
|---|---|---|---|
| Paper (GPT-4o, reportado) | US$ 0,70 | ~US$ 2,19 (derivado: 0,70 × 300 ÷ 96) | n/d |
| Flash-Lite | US$ 0,018 | US$ 0,051 | ~39,4 mil / ~5,6 mil |
| **Haiku 5.5** | **US$ 0,017** | **US$ 0,028** | **~68,4 mil / ~19,8 mil** |

Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs.

### Métrica 6 (extra): Diferença pareada com IC (bootstrap, 10.000 reamostragens)

| Comparação | Diferença | IC 95% | Conclusão |
|---|---|---|---|
| Haiku − Paper | **+21,3 p.p.** | [+4,3, +36,2] | diferença significativa (o IC exclui 0) |
| Haiku − Flash-Lite | **+23,4 p.p.** | [+8,5, +38,3] | diferença significativa (o IC exclui 0) |

---

## 3. Tabelas complementares (dos slides de resultado)

### Resolução por repositório

| Repositório | Issues | Paper | Flash-Lite | **Haiku** |
|---|---:|---:|---:|---:|
| django | 14 | 8 | 6 | **11** |
| sympy | 14 | 4 | 4 | **8** |
| scikit-learn | 4 | 1 | 1 | **2** |
| matplotlib | 4 | 1 | 1 | **1** |
| pytest-dev | 3 | 1 | 0 | **2** |
| sphinx-doc | 3 | 1 | 1 | **1** |
| psf | 1 | 1 | 1 | **0** |
| astropy | 1 | 0 | 0 | **0** |
| pylint-dev | 1 | 0 | 1 | **1** |
| mwaskom | 1 | 1 | 1 | **1** |
| pydata | 1 | 0 | 1 | **1** |
| **Total** | **47** | **18** | **17** | **28** |

### Localização (o arquivo do patch oficial foi encontrado?)

| Etapa | Paper | Flash-Lite | **Haiku** |
|---|---|---|---|
| Arquivos via LLM | 40/47 (85,1%) | 38/47 (80,9%) | **44/47 (93,6%)** |
| Arquivos via embeddings | 39/47 (83,0%) | 43/47 (91,5%) | **45/47 (95,7%)** |
| Arquivos combinados | 43/47 (91,5%) | 41/47 (87,2%) | **45/47 (95,7%)** |
| Elementos relacionados | 40/47 (85,1%) | 39/47 (83,0%) | **45/47 (95,7%)** |
| Patch final no arquivo certo | 33/47 (70,2%) | 36/47 (76,6%) | **42/47 (89,4%)** |

### Diagnóstico da seleção de patch

| Situação | Flash-Lite | **Haiku** |
|---|---|---|
| Com teste de reprodução e ≥1 patch passando nele | 10/18 (55,6%) | **22/34 (64,7%)** |
| Com teste, mas nenhum patch passa | 5/19 (26,3%) | **3/8 (37,5%)** |
| Sem teste de reprodução válido | 2/10 (20,0%) | **3/5 (60,0%)** |
| Patches distintos por issue (média) | 3,3 | **4,2** |
| Issues com um só patch distinto | 7 | **9** |

---

## 4. Ressalvas para a interpretação

1. **A comparação com o paper mistura fatores além do modelo:** modelo de 2026 com raciocínio `medium` contra o GPT-4o de 2024, 2×3 patches contra 4×10, embeddings locais e amostragem do provedor em vez de temperatura 0,8.
2. **O baseline do paper nos slides precisa de correção.** O 40,7% do slide é do Agentless com Claude 3.5 Sonnet. O GPT-4o do paper resolve **96/300 = 32,0%**, a US$ 0,70 por issue. A comparação válida é a das mesmas 47 issues (18/47 = 38,3%).
3. **Uma rodada só e amostra de 47 issues:** os intervalos são largos. O IC da diferença contra o paper vai de +4,3 a +36,2 p.p.
4. **Quatro issues em imagens oficiais do Docker Hub** (seção 1). Os testes do `requests` dependem de rede e podem falhar dentro do container.
5. O oráculo mede só o que foi gerado: **33 de 47 é o teto** do Haiku com esses 6 patches por issue.
6. Possível contaminação: as issues do SWE-bench são públicas e anteriores aos modelos, o que vale para o paper, para o Flash-Lite e para o Haiku.
