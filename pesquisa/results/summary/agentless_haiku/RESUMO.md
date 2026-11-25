# Agentless (Claude Haiku 5.5, 2×3 patches, 4 testes) × paper (47 issues do SWE-bench Lite-S)

## Resolução

| | Resolvidas | IC 95% (Wilson) |
|---|---|---|
| Paper (GPT-4o, 4×10 patches, 40 testes) | 18/47 (38.3%) | [26%, 53%] |
| Nós (Claude Haiku 5.5, 2×3 patches, 4 testes) | 28/47 (59.6%) | [45%, 72%] |

Ambos: 15 · só nós: 13 · só paper: 3 · nenhum: 16 · McNemar exato p = 0.02

### Por execução

| Execução | Issues | Paper | Nós |
|---|---|---|---|
| haiku_reduced | 15 | 6/15 (40.0%) | 10/15 (66.7%) |
| haiku_reduced_ext | 32 | 12/32 (37.5%) | 18/32 (56.2%) |

### Por repositório

| Repositório | Issues | Paper | Nós |
|---|---|---|---|
| django | 14 | 8 | 11 |
| sympy | 14 | 4 | 8 |
| scikit-learn | 4 | 1 | 2 |
| matplotlib | 4 | 1 | 1 |
| pytest-dev | 3 | 1 | 2 |
| sphinx-doc | 3 | 1 | 1 |
| mwaskom | 1 | 1 | 1 |
| psf | 1 | 1 | 0 |
| pydata | 1 | 0 | 1 |
| pylint-dev | 1 | 0 | 1 |
| astropy | 1 | 0 | 0 |

## Localização (o arquivo do patch oficial foi encontrado?)

| Etapa | Paper | Nós |
|---|---|---|
| Arquivos via LLM | 40/47 (85.1%) | 44/47 (93.6%) |
| Arquivos via embeddings | 39/47 (83.0%) | 45/47 (95.7%) |
| Arquivos combinados | 43/47 (91.5%) | 45/47 (95.7%) |
| Elementos relacionados | 40/47 (85.1%) | 45/47 (95.7%) |
| Patch final no arquivo certo | 33/47 (70.2%) | 42/47 (89.4%) |

## Diagnóstico da seleção de patch (nossa execução)

| Situação | Issues | Resolvidas |
|---|---|---|
| Com teste de reprodução e ≥1 patch passando nele | 34 | 22/34 (64.7%) |
| Com teste, mas nenhum patch passa | 8 | 3/8 (37.5%) |
| Sem teste de reprodução válido | 5 | 3/5 (60.0%) |

Patches distintos por issue: média 4.2 · issues com um só patch distinto: 9

## Oráculo (algum dos patches gerados resolve?)

Avaliado na máquina da execução do Haiku; os relatórios do oráculo não estão neste repositório. Resultado registrado em [RESULTADOS_HAIKU.md](../../../docs/RESULTADOS_HAIKU.md): selecionado 28/47 (59,6%), oráculo 33/47 (70,2%), com 197 candidatos distintos avaliados. Patch correto gerado e não selecionado: django-11815, matplotlib-25498, pytest-5221, scikit-learn-14983 e sympy-14396.

_Detalhe por issue: `pesquisa/results/summary/agentless_haiku/por_issue.csv`_

## Métricas extras

### Custo e tokens (Nós: claude-haiku-5-5; US$ 0.1/0.5 por 1M tokens entrada/saída)

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---|---|---|
| Localização: arquivos (LLM) | 304,483 | 15,955 | 0.038 |
| Localização: arquivos irrelevantes | 309,183 | 36,189 | 0.049 |
| Localização: elementos relacionados | 336,849 | 28,094 | 0.048 |
| Localização: linhas de edição | 1,178,060 | 57,649 | 0.147 |
| Geração de patches | 748,674 | 494,172 | 0.322 |
| Testes de reprodução | 229,100 | 264,178 | 0.155 |
| Seleção de testes de regressão | 109,747 | 34,180 | 0.028 |
| **Total** | **3,216,096** | **930,417** | **0.787** |

- Custo por issue: US$ 0.017 (47 issues)
- Custo por issue resolvida: US$ 0.028 (28 resolvidas)
- Tokens por issue: 68,428 entrada, 19,796 saída
- Referência do paper (GPT-4o, reportado): US$ 0.70 por issue

_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._

### Diferença pareada vs. paper (mesmas issues)

| | Resolvidas |
|---|---|
| Nós | 28/47 (59.6%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Nós − paper): **+21.3 p.p.**, IC 95% bootstrap pareado [+4.3, +36.2] p.p. (10.000 reamostragens)
- Discordâncias: só Nós 13 · só paper 3 · ambos 15 · nenhum 16 · McNemar exato p = 0.02
- Conclusão: diferença significativa (IC exclui 0)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
