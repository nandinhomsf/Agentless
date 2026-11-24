## Métricas extras

### Custo e tokens (Haiku 5.5 (medium): claude-haiku-5-5; US$ 0.1/0.5 por 1M tokens entrada/saída)

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
| Haiku 5.5 (medium) | 28/47 (59.6%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Haiku 5.5 (medium) − paper): **+21.3 p.p.**, IC 95% bootstrap pareado [+4.3, +36.2] p.p. (10.000 reamostragens)
- Discordâncias: só Haiku 5.5 (medium) 13 · só paper 3 · ambos 15 · nenhum 16 · McNemar exato p = 0.02
- Conclusão: diferença significativa (IC exclui 0)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
