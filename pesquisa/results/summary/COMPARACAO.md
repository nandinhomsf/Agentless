# Agentless × abordagem agêntica nas 47 issues do SWE-bench Lite-S

_Gerado por `pesquisa/scripts/compare_all.py`. Avaliação oficial do SWE-bench em Docker; as mesmas 47 issues em todas as execuções._

## Resultado e custo

| Abordagem | Modelo | Resolvidas | IC 95% (Wilson) | Custo total (US$) | US$/issue | US$/resolvida | Tokens/issue (entrada · saída) |
|---|---|---|---|---|---|---|---|
| Agentless (paper) | GPT-4o | 18/47 (38,3%) | 26–53% | — | 0,70* | 2,19* | — |
| Agentless | GPT-6 Luna | **24/47 (51,1%)** | 37–65% | 0,620 | 0,013 | 0,026 | 33,7k · 19,7k |
| Agente (mini-SWE-agent) | GPT-6 Luna | **30/47 (63,8%)** | 50–76% | 0,664 | 0,014 | 0,022 | 123,4k · 3,6k |
| Agentless | Claude Haiku 5.5 | **28/47 (59,6%)** | 45–72% | 0,787 | 0,017 | 0,028 | 68,4k · 19,8k |
| Agente (Claude Code) | Claude Haiku 5.5 | **32/47 (68,1%)** | 54–80% | 0,151 | 0,003 | 0,005 | — (custo informado pelo provedor) |

Custo = tokens registrados × preço de tabela por 1M de tokens (entrada/saída: Claude Haiku 5.5 US$ 0,10/0,50; GPT-6 Luna US$ 0,10/0,50), só chamadas ao LLM. No agente Claude Code, o custo é o informado pelo próprio provedor (inclui cache). Nos modelos de raciocínio, a saída inclui o raciocínio.
*Valores reportados pelo paper para o SWE-bench Lite inteiro: US$ 0,70 por issue e 96/300 resolvidas, o que dá US$ 2,19 por issue resolvida.

## Comparações pareadas

Mesmas issues dos dois lados; só as issues que uma abordagem resolve e a outra não pesam no teste.

| A × B | Só A | Só B | Diferença (p.p.) | IC 95% bootstrap | McNemar p | Leitura |
|---|---|---|---|---|---|---|
| Agente Luna × Agentless Luna (efeito da abordagem, mesmo modelo) | 7 | 1 | +12,8 | +2,1 a +25,5 | 0,070 | indício (bootstrap exclui 0, McNemar não) |
| Agente Haiku × Agentless Haiku (efeito da abordagem, mesmo modelo) | 7 | 3 | +8,5 | -4,3 a +21,3 | 0,344 | sem evidência de diferença |
| Agentless Haiku × Agentless Luna (efeito do modelo no Agentless) | 7 | 3 | +8,5 | -4,3 a +21,3 | 0,344 | sem evidência de diferença |
| Agentless Luna × Paper | 10 | 4 | +12,8 | -2,1 a +27,7 | 0,180 | sem evidência de diferença |
| Agentless Haiku × Paper | 13 | 3 | +21,3 | +4,3 a +36,2 | 0,021 | diferença significativa |
| Agente Luna × Paper | 16 | 4 | +25,5 | +8,5 a +42,6 | 0,012 | diferença significativa |
| Agente Haiku × Paper | 16 | 2 | +29,8 | +14,9 a +44,7 | 0,001 | diferença significativa |

Critério de significância: McNemar exato a 5%. Com poucas issues discordantes, o bootstrap percentil tende a dar intervalos estreitos demais, por isso ele indica só a magnitude plausível da diferença. p alto não prova equivalência. Bootstrap pareado com 10.000 reamostragens.

## Por repositório

| Repositório | Issues | Paper | Agentless Luna | Agente Luna | Agentless Haiku | Agente Haiku |
|---|---|---|---|---|---|---|
| django | 14 | 8 | 9 | 12 | 11 | 14 |
| sympy | 14 | 4 | 8 | 9 | 8 | 10 |
| matplotlib | 4 | 1 | 1 | 3 | 1 | 2 |
| scikit-learn | 4 | 1 | 1 | 1 | 2 | 1 |
| pytest-dev | 3 | 1 | 0 | 1 | 2 | 2 |
| sphinx-doc | 3 | 1 | 2 | 1 | 1 | 0 |
| astropy | 1 | 0 | 0 | 0 | 0 | 0 |
| mwaskom | 1 | 1 | 1 | 1 | 1 | 1 |
| psf | 1 | 1 | 0 | 0 | 0 | 0 |
| pydata | 1 | 0 | 1 | 1 | 1 | 1 |
| pylint-dev | 1 | 0 | 1 | 1 | 1 | 1 |
| **Total** | **47** | **18** | **24** | **30** | **28** | **32** |

Resolvidas por pelo menos uma das nossas execuções: 37/47.

### Não resolvidas por nenhuma das nossas execuções (10)

- `astropy__astropy-7746`
- `matplotlib__matplotlib-23299`
- `psf__requests-863` (resolvida pelo paper)
- `pytest-dev__pytest-5221`
- `scikit-learn__scikit-learn-13497`
- `scikit-learn__scikit-learn-14983`
- `sphinx-doc__sphinx-8721` (resolvida pelo paper)
- `sympy__sympy-12454`
- `sympy__sympy-14308`
- `sympy__sympy-14317`

Detalhe por issue: `pesquisa/results/summary/comparacao_por_issue.csv`.
