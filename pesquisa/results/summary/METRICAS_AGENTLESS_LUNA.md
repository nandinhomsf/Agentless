## Métricas extras

### Custo e tokens (Agentless Luna: gpt-6-luna; US$ 0.1/0.5 por 1M tokens entrada/saída)

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
| Agentless Luna | 24/47 (51.1%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Agentless Luna − paper): **+12.8 p.p.**, IC 95% bootstrap pareado [-2.1, +27.7] p.p. (10.000 reamostragens)
- Discordâncias: só Agentless Luna 10 · só paper 4 · ambos 14 · nenhum 19 · McNemar exato p = 0.18
- Conclusão: inconclusivo (IC largo demais para afirmar equivalência ou diferença)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
