## Métricas extras

### Custo e tokens (Agente Luna: gpt-6-luna; US$ 0.1/0.5 por 1M tokens entrada/saída)

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---|---|---|
| Localização: arquivos (LLM) | 0 | 0 | 0.000 |
| Localização: arquivos irrelevantes | 0 | 0 | 0.000 |
| Localização: elementos relacionados | 0 | 0 | 0.000 |
| Localização: linhas de edição | 0 | 0 | 0.000 |
| Geração de patches | 0 | 0 | 0.000 |
| Testes de reprodução | 0 | 0 | 0.000 |
| Seleção de testes de regressão | 0 | 0 | 0.000 |
| Agente (mini-SWE-agent, todas as chamadas) | 5,801,434 | 167,488 | 0.664 |
| **Total** | **5,801,434** | **167,488** | **0.664** |

- Custo por issue: US$ 0.014 (47 issues)
- Custo por issue resolvida: US$ 0.022 (30 resolvidas)
- Tokens por issue: 123,435 entrada, 3,564 saída
- Referência do paper (GPT-4o, reportado): US$ 0.70 por issue

_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._

### Diferença pareada vs. paper (mesmas issues)

| | Resolvidas |
|---|---|
| Agente Luna | 30/47 (63.8%) |
| Paper (mesmas 47 issues) | 18/47 (38.3%) |

- Diferença (Agente Luna − paper): **+25.5 p.p.**, IC 95% bootstrap pareado [+8.5, +42.6] p.p. (10.000 reamostragens)
- Discordâncias: só Agente Luna 16 · só paper 4 · ambos 14 · nenhum 13 · McNemar exato p = 0.01
- Conclusão: diferença significativa (IC exclui 0)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._

### Diferença pareada vs. Agentless Luna (mesmas issues)

| | Resolvidas |
|---|---|
| Agente Luna | 30/47 (63.8%) |
| Agentless Luna | 24/47 (51.1%) |

- Diferença (Agente Luna − Agentless Luna): **+12.8 p.p.**, IC 95% bootstrap pareado [+2.1, +25.5] p.p. (10.000 reamostragens)
- Discordâncias: só Agente Luna 7 · só Agentless Luna 1 · ambos 23 · nenhum 16 · McNemar exato p = 0.07
- Conclusão: diferença significativa (IC exclui 0)

_A margem de equivalência é uma escolha do estudo (`--margem`); p alto no McNemar não prova equivalência._
