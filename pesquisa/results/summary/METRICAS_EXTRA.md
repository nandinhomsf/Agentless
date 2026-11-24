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
