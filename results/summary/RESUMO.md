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
| scikit-learn | 4 | 1 | 1 |
| matplotlib | 4 | 1 | 1 |
| pytest-dev | 3 | 1 | 0 |
| sphinx-doc | 3 | 1 | 1 |
| pydata | 1 | 0 | 1 |
| pylint-dev | 1 | 0 | 1 |
| mwaskom | 1 | 1 | 1 |
| psf | 1 | 1 | 1 |
| astropy | 1 | 0 | 0 |

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

_Detalhe por issue: `results/summary/por_issue.csv`_
