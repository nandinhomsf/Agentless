# Resumo da replicação do Agentless (47 issues do SWE-bench Lite-S)

## Resolução

| | Resolvidas | IC 95% (Wilson) |
|---|---|---|
| Paper (GPT-4o, 4×10 patches, 40 testes) | 18/47 (38.3%) | [26%, 53%] |
| Nós (Gemini 3.1 Flash-Lite, 2×3 patches, 4 testes) | 17/47 (36.2%) | [24%, 50%] |

Ambos: 12 · só nós: 5 · só paper: 6 · nenhum: 24 · McNemar exato p = 1.00

### Por execução

| Execução | Issues | Paper | Nós |
|---|---|---|---|
| flashlite_reduced | 15 | 6/15 (40.0%) | 4/15 (26.7%) |
| flashlite_reduced_ext | 32 | 12/32 (37.5%) | 13/32 (40.6%) |

### Por repositório

| Repositório | Issues | Paper | Nós |
|---|---|---|---|
| sympy | 14 | 4 | 4 |
| django | 14 | 8 | 6 |
| matplotlib | 4 | 1 | 1 |
| scikit-learn | 4 | 1 | 1 |
| pytest-dev | 3 | 1 | 0 |
| sphinx-doc | 3 | 1 | 1 |
| pylint-dev | 1 | 0 | 1 |
| mwaskom | 1 | 1 | 1 |
| astropy | 1 | 0 | 0 |
| pydata | 1 | 0 | 1 |
| psf | 1 | 1 | 1 |

## Localização (o arquivo do patch oficial foi encontrado?)

| Etapa | Paper | Nós |
|---|---|---|
| Arquivos via LLM | 40/47 (85.1%) | 38/47 (80.9%) |
| Arquivos via embeddings | 39/47 (83.0%) | 43/47 (91.5%) |
| Arquivos combinados | 43/47 (91.5%) | 41/47 (87.2%) |
| Elementos relacionados | 40/47 (85.1%) | 39/47 (83.0%) |
| Patch final no arquivo certo | 33/47 (70.2%) | 36/47 (76.6%) |

## Diagnóstico da seleção de patch (nossa execução)

| Situação | Issues | Resolvidas |
|---|---|---|
| Com teste de reprodução e ≥1 patch passando nele | 18 | 10/18 (55.6%) |
| Com teste, mas nenhum patch passa | 19 | 5/19 (26.3%) |
| Sem teste de reprodução válido | 10 | 2/10 (20.0%) |

Patches distintos por issue: média 3.3 · issues com um só patch distinto: 7

## Oráculo (algum dos patches gerados resolve?)

Status: completo

| | Resolvidas |
|---|---|
| Patch selecionado pelo Agentless | 17/47 (36.2%) |
| Oráculo (melhor candidato possível) | 19/47 (40.4%) |

Issues com patch correto gerado mas não selecionado: django__django-12915, matplotlib__matplotlib-25498

_Detalhe por issue: `pesquisa/results/summary/por_issue.csv`_

## Métricas extras

### Custo e tokens (Nós: gemini-3.1-flash-lite; US$ 0.25/1.5 por 1M tokens entrada/saída)

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---|---|---|
| Localização: arquivos (LLM) | 241,853 | 1,447 | 0.063 |
| Localização: arquivos irrelevantes | 244,438 | 7,359 | 0.072 |
| Localização: elementos relacionados | 272,389 | 1,801 | 0.071 |
| Localização: linhas de edição | 452,262 | 3,343 | 0.118 |
| Geração de patches | 390,567 | 132,390 | 0.296 |
| Testes de reprodução | 172,548 | 116,619 | 0.218 |
| Seleção de testes de regressão | 79,571 | 1,748 | 0.023 |
| **Total** | **1,853,628** | **264,707** | **0.860** |

- Custo por issue: US$ 0.018 (47 issues)
- Custo por issue resolvida: US$ 0.051 (17 resolvidas)
- Tokens por issue: 39,439 entrada, 5,632 saída
- Referência do paper (GPT-4o, reportado): US$ 0.70 por issue

_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._

### Diferença pareada vs. paper (mesmas issues)

| | Resolvidas |
|---|---|
| Nós | 17/47 (36.2%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Nós − paper): **-2.1 p.p.**, IC 95% bootstrap pareado [-14.9, +10.6] p.p. (10.000 reamostragens)
- Discordâncias: só Nós 5 · só paper 6 · ambos 12 · nenhum 24 · McNemar exato p = 1.00
- Conclusão: inconclusivo (IC largo demais para afirmar equivalência ou diferença)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
