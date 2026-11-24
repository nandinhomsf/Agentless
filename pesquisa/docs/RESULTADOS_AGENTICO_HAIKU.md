# Resultados da abordagem agêntica com o Claude Haiku 5.5

Registro dos resultados da **abordagem agêntica** (agente nativo da Anthropic, o Claude Code em modo headless, com o **Haiku 5.5 em esforço `medium`**) nas **47 issues do SWE-bench Lite-S** da amostra do estudo, com as **seis métricas** escolhidas. O comparativo é com o Agentless (mesmo modelo, Flash-Lite e paper) nas mesmas issues. Os resultados do Agentless estão em `pesquisa/docs/RESULTADOS_HAIKU.md`.

Dados brutos em `pesquisa/results/haiku_agentic/`: `eval_report_lote1.json` (15 issues), `eval_report_lote2.json` (32 issues), `preds.jsonl` (patches originais), `preds_fixed.jsonl` (patches corrigidos, ver seção 5), `meta.jsonl` (custo, passos e duração por issue) e `trajectories/` (a trajetória completa de cada issue, 47 arquivos, ~4,2 MB).
Código: `pesquisa/scripts/agentic/run_agentic.py` (runner) e `pesquisa/scripts/agentic/fix_preds.py` (correção de patches).

> A issue de teste (`psf__requests-2317`), usada no piloto, **não faz parte das 47**.

---

## 1. Configuração

| | Agente nativo |
|---|---|
| Agente | Claude Code 2.1.330, modo `-p` com `--bare` (sem hooks, `CLAUDE.md` nem skills) |
| Modelo / esforço | `claude-haiku-5-5`, `--effort medium` |
| Ferramentas | `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep` (busca e fetch da web não habilitados) |
| Ambiente | container da imagem da instância do SWE-bench (repositório em `/testbed`, Conda `testbed`) |
| Rede | **livre**, como no experimento do Luna (o agente pode acessar a internet) |
| Entrada | o texto da issue e o prompt padrão do SWE-bench; **sem** os testes ocultos nem o patch oficial |
| Limites de segurança | US$ 0,50 por issue, 20 min por issue, parada global em US$ 6 (**nenhum foi acionado**) |
| Paralelismo | 4 issues ao mesmo tempo |
| Avaliação | o mesmo harness oficial do Agentless (`swebench.harness.run_evaluation`) |

---

## 2. As seis métricas

### Métrica 1: Taxa de resolução

| | Resolvidas | Taxa |
|---|---|---|
| **Agente nativo (Haiku 5.5 medium)** | **32/47** | **68,1%** |
| Agentless, Haiku 5.5 medium | 28/47 | 59,6% |
| Agentless, Flash-Lite | 17/47 | 36,2% |
| Agentless, GPT-4o (paper, mesmas 47) | 18/47 | 38,3% |

Por lote: agente **12/15 (80,0%)** no lote 1 e **20/32 (62,5%)** no lote 2. Todas as 47 tiveram patch, sem erro e sem patch vazio.

### Métrica 2: Teste de McNemar exato (pareado)

| Comparação | Só agente | Só outro | Ambos | Nenhum | p |
|---|---|---|---|---|---|
| Agente × Agentless-Haiku | 7 | 3 | 25 | 12 | **0,34** |
| Agente × Paper | 16 | 2 | 16 | 13 | **0,0013** |
| Agente × Agentless-Flash-Lite | 17 | 2 | 15 | 13 | **0,0007** |

### Métrica 3: Intervalo de confiança 95% (Wilson)

| | IC 95% |
|---|---|
| **Agente nativo** | **[54%, 80%]** |
| Agentless-Haiku | [45%, 72%] |
| Agentless-Flash-Lite | [24%, 50%] |
| Paper | [26%, 53%] |

### Métrica 4: Avaliação oráculo

**Não se aplica ao agente**: ele gera **um patch por issue**, então não há "melhor candidato" a escolher. Como referência, o teto do Agentless-Haiku com seus 6 patches é 33/47 (70,2%). O agente (68,1%) chega perto dele com um único patch.

### Métrica 5 (extra): Custo por issue resolvida, com tokens

Preços: US$ 0,10 por 1M de entrada, US$ 0,50 por 1M de saída, leitura de cache a 10% e escrita de cache a 125% da entrada.

| Componente | Tokens | Custo (US$) |
|---|---:|---:|
| Entrada nova | 818 | 0,0001 |
| Escrita em cache | 348.876 | 0,0436 |
| Leitura de cache | 2.277.406 | 0,0228 |
| Saída (inclui 63.421 de raciocínio) | 168.162 | 0,0841 |
| **Total** | **2.795.262** | **0,1505** |

| | Agente | Agentless (Haiku) | Agentless (Flash-Lite) | Paper |
|---|---|---|---|---|
| Custo por issue | **US$ 0,0032** | US$ 0,017 | US$ 0,018 | US$ 0,70 (reportado) |
| Custo por issue resolvida | **US$ 0,0047** | US$ 0,028 | US$ 0,051 | ~US$ 2,19 (derivado) |

Por issue: **8,3 passos** em média (mediana 7, máximo 25) e **38 s** em média (máximo 5 min 13 s). Soma de 29 min de agente; com 4 em paralelo, o agente das 47 levou cerca de **12 min de relógio** (lote 1: 7 min; lote 2: 5 min), mais 2 e 4 min de avaliação. O Agentless levou horas.

Só chamadas ao LLM. O custo do Agentless não inclui o tempo de CPU dos embeddings locais.

### Métrica 6 (extra): Diferença pareada com IC (bootstrap, 10.000 reamostragens)

| Comparação | Diferença | IC 95% | Conclusão |
|---|---|---|---|
| Agente − Agentless-Haiku | **+8,5 p.p.** | [−4,3, +21,3] | **inconclusivo** (o IC inclui 0 e passa da margem de ±10 p.p.) |
| Agente − Paper | **+29,8 p.p.** | [+14,9, +44,7] | diferença significativa |
| Agente − Agentless-Flash-Lite | **+31,9 p.p.** | [+17,0, +48,9] | diferença significativa |

---

## 3. Comparativo final

| | Resolvidas | IC 95% | Custo por issue | Custo por resolvida | Oráculo |
|---|---|---|---|---|---|
| **Agente nativo, Haiku 5.5** | **32/47 (68,1%)** | [54%, 80%] | US$ 0,0032 | US$ 0,0047 | n/a |
| Agentless, Haiku 5.5 | 28/47 (59,6%) | [45%, 72%] | US$ 0,017 | US$ 0,028 | 33/47 (70,2%) |
| Agentless, Flash-Lite | 17/47 (36,2%) | [24%, 50%] | US$ 0,018 | US$ 0,051 | 19/47 (40,4%) |
| Agentless, GPT-4o (paper) | 18/47 (38,3%) | [26%, 53%] | US$ 0,70 | ~US$ 2,19 | n/d nas 47 |

**Leitura:** com o mesmo modelo, o agente resolveu mais (+8,5 p.p.), mas **a diferença não é significativa** com 47 issues, e custou cerca de 5× menos em tokens de LLM e levou muito menos tempo.

## 4. Resolução por repositório

| Repositório | Issues | Paper | Flash-Lite | Agentless-Haiku | **Agente** |
|---|---:|---:|---:|---:|---:|
| django | 14 | 8 | 6 | 11 | **14** |
| sympy | 14 | 4 | 4 | 8 | **10** |
| matplotlib | 4 | 1 | 1 | 1 | **2** |
| scikit-learn | 4 | 1 | 1 | 2 | **1** |
| pytest-dev | 3 | 1 | 0 | 2 | **2** |
| sphinx-doc | 3 | 1 | 1 | 1 | **0** |
| psf (requests) | 1 | 1 | 1 | 0 | **0** |
| mwaskom | 1 | 1 | 1 | 1 | **1** |
| pydata | 1 | 0 | 1 | 1 | **1** |
| pylint-dev | 1 | 0 | 1 | 1 | **1** |
| astropy | 1 | 0 | 0 | 0 | **0** |
| **Total** | **47** | **18** | **17** | **28** | **32** |

- **Só o agente** (7): `django-11620`, `django-11815`, `django-13158`, `matplotlib-23987`, `sympy-12236`, `sympy-14396`, `sympy-21379`.
- **Só o Agentless-Haiku** (3): `scikit-learn-25500`, `sphinx-10325`, `sympy-18835`.
- **Nenhum dos dois** (12): `astropy-7746`, `matplotlib-23299`, `matplotlib-25498`, `pytest-5221`, `requests-863`, `scikit-learn-13497`, `scikit-learn-14983`, `sphinx-10451`, `sphinx-8721`, `sympy-12454`, `sympy-14308`, `sympy-14317`.

---

## 5. Ressalvas para a interpretação

1. **Correção de patch:** o runner extraiu os patches com `git add -A -N .`, o que incluiu arquivos que já existiam na imagem como se fossem do agente. Isso contaminou **um** patch, o do `psf__requests-863` (16.557 linhas, 69 arquivos de `build/lib/...`). Ele foi corrigido com `fix_preds.py` (17 linhas, só a edição real em `requests/models.py`) **antes** da avaliação, e os outros 46 ficaram idênticos. O runner foi corrigido para as próximas execuções. Os patches originais continuam em `preds.jsonl`.
2. **`requests-863` não é resolvível neste ambiente:** o patch oficial também falha (por um teste que depende de rede, `test_connection_keepalive_and_close`). Vale para todas as abordagens.
3. **Rede livre:** a varredura dos comandos `Bash` nas 47 trajetórias (busca por `github`, `pip install/download`, `git clone/fetch`, `curl`, `wget`, `PyPI` e similares) achou **0 comandos suspeitos**. É uma busca por texto. A análise qualitativa completa das trajetórias, e o risco de "cola", ficam para uma etapa posterior.
4. **Agentes diferentes:** o seu colega usou o agente nativo do Luna, e este usa o Claude Code. A diferença entre os modelos mistura modelo e agente.
5. **Configuração mínima:** o Claude Code rodou com `--bare` (sem hooks, `CLAUDE.md` nem skills) e com um prompt padrão do SWE-bench, e não com o prompt padrão da ferramenta.
6. **Quatro issues em imagens oficiais do Docker Hub** (`matplotlib-23987`, `scikit-learn-25500` e `25570`, `pylint-7993`), como no Agentless.
7. **Uma rodada só e amostra de 47:** os intervalos são largos, e a diferença entre o agente e o Agentless com o mesmo Haiku (+8,5 p.p.) não é conclusiva.
8. **Possível contaminação de treino:** as issues do SWE-bench são públicas, e o paper reconhece esse risco como ameaça interna. Vale para todas as abordagens.
