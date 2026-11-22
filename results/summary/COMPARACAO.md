# Agentless × agente nas 47 issues do SWE-bench Lite-S

_Gerado por `scripts/compare_all.py`. Avaliação oficial do SWE-bench em Docker; as mesmas 47 issues em todas as execuções._

## Resultado, custo e tokens

| Abordagem | Modelo | Resolvidas | IC 95% (Wilson) | Custo total (US$) | US$/issue | US$/resolvida | Tokens/issue (entrada · saída) |
|---|---|---|---|---|---|---|---|
| Agentless (paper) | GPT-4o | 18/47 (38,3%) | 26–53% | — | 0,70* | ≈1,83* | — |
| Agentless, rodada 1 | Gemini 3.1 Flash-Lite | **17/47 (36,2%)** | 24–50% | 0,860 | 0,018 | 0,051 | 39,4k · 5,6k |
| Agentless, rodada 2 | Gemini 3.1 Flash-Lite | **17/47 (36,2%)** | 24–50% | 0,866 | 0,018 | 0,051 | 39,7k · 5,7k |
| Agentless | GPT-6 Luna | **24/47 (51,1%)** | 37–65% | 0,620 | 0,013 | 0,026 | 33,7k · 19,7k |
| Agente (mini-SWE-agent) | GPT-6 Luna | **30/47 (63,8%)** | 50–76% | 0,664 | 0,014 | 0,022 | 123,4k · 3,6k |
| Agente (mini-SWE-agent) | Gemini 3.1 Flash-Lite | em andamento (12/47 issues executadas) | — | 1,199 até agora | — | — | — |

Custo = tokens registrados × preço de tabela por 1M de tokens (Flash-Lite US$ 0,25/1,50; Luna US$ 0,10/0,50), só chamadas ao LLM. Nos modelos de raciocínio a saída inclui o raciocínio. *O paper reporta US$ 0,70 por issue (GPT-4o, Lite inteiro); o custo por resolvida é uma estimativa.

## Comparações pareadas

Mesmas issues dos dois lados; só as issues que uma abordagem resolve e a outra não pesam no teste.

| A × B | Só A | Só B | Diferença (p.p.) | IC 95% bootstrap | McNemar p | Leitura |
|---|---|---|---|---|---|---|
| Agente Luna × Agentless Luna (efeito da abordagem, mesmo modelo) | 7 | 1 | +12,8 | +2,1 a +25,5 | 0,070 | indício (bootstrap exclui 0, McNemar não) |
| Agentless Luna × Agentless Flash-Lite (r1) (efeito do modelo no Agentless) | 9 | 2 | +14,9 | +2,1 a +27,7 | 0,065 | indício (bootstrap exclui 0, McNemar não) |
| Agente Luna × Paper | 16 | 4 | +25,5 | +8,5 a +42,6 | 0,012 | diferença significativa |
| Agentless Luna × Paper | 10 | 4 | +12,8 | -2,1 a +27,7 | 0,180 | sem evidência de diferença |
| Agentless Flash-Lite (r1) × Paper | 5 | 6 | -2,1 | -14,9 a +10,6 | 1,000 | sem evidência de diferença |
| Agente Luna × Agentless Flash-Lite (r1) | 15 | 2 | +27,7 | +12,8 a +42,6 | 0,002 | diferença significativa |
| Agentless Flash-Lite (r2) × Agentless Flash-Lite (r1) (estabilidade entre rodadas) | 1 | 1 | +0,0 | -6,4 a +6,4 | 1,000 | sem evidência de diferença |

Com poucas issues discordantes, o bootstrap percentil tende a dar intervalos estreitos demais; por isso a leitura usa o McNemar exato como critério (5%). p alto não prova equivalência. Bootstrap pareado com 10.000 reamostragens.

## Por repositório

| Repositório | Issues | Paper | Agentless Flash-Lite (r1) | Agentless Luna | Agente Luna |
|---|---|---|---|---|---|
| django | 14 | 8 | 6 | 9 | 12 |
| sympy | 14 | 4 | 4 | 8 | 9 |
| matplotlib | 4 | 1 | 1 | 1 | 3 |
| scikit-learn | 4 | 1 | 1 | 1 | 1 |
| pytest-dev | 3 | 1 | 0 | 0 | 1 |
| sphinx-doc | 3 | 1 | 1 | 2 | 1 |
| astropy | 1 | 0 | 0 | 0 | 0 |
| mwaskom | 1 | 1 | 1 | 1 | 1 |
| psf | 1 | 1 | 1 | 0 | 0 |
| pydata | 1 | 0 | 1 | 1 | 1 |
| pylint-dev | 1 | 0 | 1 | 1 | 1 |
| **Total** | **47** | **18** | **17** | **24** | **30** |

Resolvidas por pelo menos uma abordagem: 35/47; por nenhuma: 12.

## Em andamento

- Agente (mini-SWE-agent) · Gemini 3.1 Flash-Lite: 12/47 issues executadas. O agente com Flash-Lite roda no plano grátis (500 chamadas/dia, ~29 por issue); o runner retoma quando a cota renova.

Detalhe por issue: `results/summary/comparacao_por_issue.csv`.
