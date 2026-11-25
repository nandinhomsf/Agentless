# Agentless (GPT-6 Luna, 2×3 patches, 4 testes) × paper (47 issues do SWE-bench Lite-S)

## Resolução

| | Resolvidas | IC 95% (Wilson) |
|---|---|---|
| Paper (GPT-4o, 4×10 patches, 40 testes) | 18/47 (38.3%) | [26%, 53%] |
| Nós (GPT-6 Luna, 2×3 patches, 4 testes) | 24/47 (51.1%) | [37%, 65%] |

Ambos: 14 · só nós: 10 · só paper: 4 · nenhum: 19 · McNemar exato p = 0.18

### Por execução

| Execução | Issues | Paper | Nós |
|---|---|---|---|
| luna_reduced | 15 | 6/15 (40.0%) | 7/15 (46.7%) |
| luna_reduced_ext | 32 | 12/32 (37.5%) | 17/32 (53.1%) |

### Por repositório

| Repositório | Issues | Paper | Nós |
|---|---|---|---|
| sympy | 14 | 4 | 8 |
| django | 14 | 8 | 9 |
| scikit-learn | 4 | 1 | 1 |
| matplotlib | 4 | 1 | 1 |
| sphinx-doc | 3 | 1 | 2 |
| pytest-dev | 3 | 1 | 0 |
| psf | 1 | 1 | 0 |
| pydata | 1 | 0 | 1 |
| mwaskom | 1 | 1 | 1 |
| astropy | 1 | 0 | 0 |
| pylint-dev | 1 | 0 | 1 |

## Localização (o arquivo do patch oficial foi encontrado?)

| Etapa | Paper | Nós |
|---|---|---|
| Arquivos via LLM | 40/47 (85.1%) | 38/47 (80.9%) |
| Arquivos via embeddings | 39/47 (83.0%) | 43/47 (91.5%) |
| Arquivos combinados | 43/47 (91.5%) | 42/47 (89.4%) |
| Elementos relacionados | 40/47 (85.1%) | 41/47 (87.2%) |
| Patch final no arquivo certo | 33/47 (70.2%) | 39/47 (83.0%) |

## Diagnóstico da seleção de patch (nossa execução)

| Situação | Issues | Resolvidas |
|---|---|---|
| Com teste de reprodução e ≥1 patch passando nele | 29 | 17/29 (58.6%) |
| Com teste, mas nenhum patch passa | 8 | 3/8 (37.5%) |
| Sem teste de reprodução válido | 10 | 4/10 (40.0%) |

Patches distintos por issue: média 3.6 · issues com um só patch distinto: 9

## Oráculo (algum dos patches gerados resolve?)

Status: completo

| | Resolvidas |
|---|---|
| Patch selecionado pelo Agentless | 24/47 (51.1%) |
| Oráculo (melhor candidato possível) | 28/47 (59.6%) |

Issues com patch correto gerado mas não selecionado: django__django-13158, django__django-16910, matplotlib__matplotlib-23987, scikit-learn__scikit-learn-14983

_Detalhe por issue: `pesquisa/results/summary/agentless_luna/por_issue.csv`_

## Métricas extras

### Custo e tokens (Nós: gpt-6-luna; US$ 0.1/0.5 por 1M tokens entrada/saída)

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---|---|---|
| Localização: arquivos (LLM) | 199,212 | 29,453 | 0.035 |
| Localização: arquivos irrelevantes | 201,656 | 26,385 | 0.033 |
| Localização: elementos relacionados | 199,903 | 52,497 | 0.046 |
| Localização: linhas de edição | 368,030 | 57,655 | 0.066 |
| Geração de patches | 399,993 | 416,321 | 0.248 |
| Testes de reprodução | 152,692 | 289,145 | 0.160 |
| Seleção de testes de regressão | 63,445 | 52,160 | 0.032 |
| **Total** | **1,584,931** | **923,616** | **0.620** |

- Custo por issue: US$ 0.013 (47 issues)
- Custo por issue resolvida: US$ 0.026 (24 resolvidas)
- Tokens por issue: 33,722 entrada, 19,651 saída
- Referência do paper (GPT-4o, reportado): US$ 0.70 por issue

_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._

### Diferença pareada vs. paper (mesmas issues)

| | Resolvidas |
|---|---|
| Nós | 24/47 (51.1%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Nós − paper): **+12.8 p.p.**, IC 95% bootstrap pareado [-2.1, +27.7] p.p. (10.000 reamostragens)
- Discordâncias: só Nós 10 · só paper 4 · ambos 14 · nenhum 19 · McNemar exato p = 0.18
- Conclusão: inconclusivo (IC largo demais para afirmar equivalência ou diferença)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
