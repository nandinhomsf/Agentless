## Métricas extras

### Custo e tokens (Flash-Lite rodada 2: gemini-3.1-flash-lite; US$ 0.25/1.5 por 1M tokens entrada/saída)

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---|---|---|
| Localização: arquivos (LLM) | 241,853 | 1,447 | 0.063 |
| Localização: arquivos irrelevantes | 244,438 | 7,350 | 0.072 |
| Localização: elementos relacionados | 264,296 | 1,768 | 0.069 |
| Localização: linhas de edição | 452,262 | 3,280 | 0.118 |
| Geração de patches | 413,082 | 134,801 | 0.305 |
| Testes de reprodução | 172,548 | 115,289 | 0.216 |
| Seleção de testes de regressão | 79,571 | 1,748 | 0.023 |
| **Total** | **1,868,050** | **265,683** | **0.866** |

- Custo por issue: US$ 0.018 (47 issues)
- Custo por issue resolvida: US$ 0.051 (17 resolvidas)
- Tokens por issue: 39,746 entrada, 5,653 saída
- Referência do paper (GPT-4o, reportado): US$ 0.70 por issue

_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._

### Diferença pareada vs. paper (mesmas issues)

| | Resolvidas |
|---|---|
| Flash-Lite rodada 2 | 17/47 (36.2%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Flash-Lite rodada 2 − paper): **-2.1 p.p.**, IC 95% bootstrap pareado [-17.0, +12.8] p.p. (10.000 reamostragens)
- Discordâncias: só Flash-Lite rodada 2 6 · só paper 7 · ambos 11 · nenhum 23 · McNemar exato p = 1.00
- Conclusão: inconclusivo (IC largo demais para afirmar equivalência ou diferença)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._

### Diferença pareada vs. rodada 1 (mesmas issues)

| | Resolvidas |
|---|---|
| Flash-Lite rodada 2 | 17/47 (36.2%) |
| rodada 1 | 17/47 (36.2%) |

- Diferença (Flash-Lite rodada 2 − rodada 1): **+0.0 p.p.**, IC 95% bootstrap pareado [-6.4, +6.4] p.p. (10.000 reamostragens)
- Discordâncias: só Flash-Lite rodada 2 1 · só rodada 1 1 · ambos 16 · nenhum 29 · McNemar exato p = 1.00
- Conclusão: equivalente dentro da margem de ±10 p.p.

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
