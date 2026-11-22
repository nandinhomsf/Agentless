# genai-agentless: replicação do Agentless com LLM gratuito

Replicação do paper **[Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489)**
(Xia, Deng, Dunn e Zhang, 2024) no SWE-bench Lite-S, usando um LLM de plano
gratuito (Gemini 3.1 Flash-Lite) no lugar do GPT-4o. Trabalho da disciplina de
IA Generativa do mestrado.

Este repositório é um fork do [código oficial do Agentless](https://github.com/OpenAutoCoder/Agentless),
com o histórico dos autores preservado. As nossas mudanças estão nos commits por
cima do original.

## Resultado

Comparação nas **mesmas 47 issues** do SWE-bench Lite-S, sorteadas com
estratificação por repositório:

| | Patches por issue | Resolvidas | IC 95% |
|---|---|---|---|
| Agentless do paper (GPT-4o) | 4 × 10 = 40 | 18/47 (38,3%) | [26%, 53%] |
| **Esta replicação (Gemini 3.1 Flash-Lite, grátis)** | **2 × 3 = 6** | **17/47 (36,2%)** | [24%, 50%] |

- **Não há evidência de diferença** (McNemar exato, p = 1,00), com uma
  configuração ~5 vezes mais barata em chamadas ao LLM. Isso **não prova
  equivalência**: a diferença pareada é de −2,1 p.p., com IC 95% de
  [−14,9; +10,6] p.p. (bootstrap), então a amostra é pequena demais para concluir.
- **Custo:** US$ 0,86 no total, ou **US$ 0,051 por issue resolvida**, contra
  US$ 0,70 *por issue* reportados no paper com GPT-4o.
- **Oráculo:** se a escolha do patch fosse perfeita, chegaríamos a 19/47. A
  seleção perde só 2 issues, e em 28 nenhum candidato funciona. **O gargalo é a
  geração de patches, não a seleção.**
- Os embeddings locais (`bge-small`) encontraram o arquivo certo em 91,5% das
  issues, contra 83,0% com os embeddings da OpenAI usados no paper.

Tabelas completas em [`results/summary/RESUMO.md`](results/summary/RESUMO.md).
Explicação de todo o trabalho (método, decisões, problemas e limitações) em
[`docs/EXPLICACAO_COMPLETA.md`](docs/EXPLICACAO_COMPLETA.md).

## Agentless × agente

Depois da replicação, rodamos nas mesmas 47 issues o Agentless com outro modelo
barato (GPT-6 Luna) e um agente, o mini-SWE-agent (detalhes em
[Abordagem agêntica](#abordagem-agêntica-comparação)), com os dois modelos:

<!-- comparacao:inicio -->
| Abordagem | Modelo | Resolvidas | US$ por issue resolvida |
|---|---|---|---|
| Agentless (paper) | GPT-4o | 18/47 (38,3%) | ≈1,83 (estimado) |
| Agentless, rodada 1 | Gemini 3.1 Flash-Lite | 17/47 (36,2%) | 0,051 |
| Agentless, rodada 2 | Gemini 3.1 Flash-Lite | 17/47 (36,2%) | 0,051 |
| Agentless | GPT-6 Luna | 24/47 (51,1%) | 0,026 |
| Agente (mini-SWE-agent) | GPT-6 Luna | 30/47 (63,8%) | 0,022 |
| Agente (mini-SWE-agent) | Gemini 3.1 Flash-Lite | em andamento (12/47) | — |
<!-- comparacao:fim -->

- **Com o Luna, o agente superou o Agentless:** resolveu 7 issues que o
  Agentless não resolveu e perdeu só 1 (McNemar p = 0,07, um indício que não
  chega a ser significativo). Também saiu mais barato por issue resolvida.
- **Trocar o Flash-Lite pelo Luna ajudou o Agentless:** 9 issues ganhas e 2
  perdidas (p = 0,07), com custo total menor.
- **O agente com Luna supera o paper** (16 contra 4 issues discordantes,
  p = 0,01) e o Agentless com Flash-Lite (15 contra 2, p = 0,002).

Tabelas completas, testes pareados e o detalhe por repositório estão em
[`results/summary/COMPARACAO.md`](results/summary/COMPARACAO.md), gerado por
`scripts/compare_all.py`.

## O que mudou em relação ao Agentless original

O método não foi alterado. As mudanças são de infraestrutura:

- **Backends `gemini` e `nvidia`** (APIs compatíveis com OpenAI), com controle de
  requisições e tokens por minuto, parada na cota diária, novas tentativas em
  erros 429/500/503 e sem gravar respostas vazias (`agentless/util/model.py`,
  `agentless/util/api_requests.py`).
- **Embeddings locais** via `AGENTLESS_LOCAL_EMBED_MODEL`, no lugar dos da OpenAI
  (`agentless/fl/Index.py`).
- **Subconjunto de issues** via `AGENTLESS_INSTANCE_IDS_FILE`
  (`agentless/util/utils.py`).
- **Limite de contexto configurável** (`AGENTLESS_MAX_CONTEXT_LENGTH`; o padrão
  continua 128k).
- **Correções para retomar execuções interrompidas**, incluindo um bug do
  original no `retrieve.py`.
- **Versões de 2024 fixadas** em `requirements-replication.lock.txt`. O
  `swebench` 5.x e o `modal` 1.x quebram o código original.

## Como reproduzir

Requisitos: Linux, Docker, ~120 GB de disco para as imagens do SWE-bench e uma
chave gratuita do Gemini ([AI Studio](https://aistudio.google.com/apikey)).

```bash
# 1. ambiente Python 3.11 com as versões exatas usadas
uv venv --python 3.11 .venv
uv pip install -p .venv -r requirements-replication.lock.txt

# 2. chave da API
cp .env.example .env        # e preencha GEMINI_API_KEY

# 3. dados grandes (estruturas dos repositórios e resultados do paper)
scripts/download_data.sh

# 4. pipeline: etapas de LLM e depois Docker (testes, seleção e avaliação)
CONFIG=scripts/configs/flashlite_reduced.env scripts/pipeline.sh llm
CONFIG=scripts/configs/flashlite_reduced.env scripts/pipeline.sh exec
# o mesmo com scripts/configs/flashlite_reduced_ext.env para as outras 32 issues

# 5. resumo agregado e comparação com o paper
.venv/bin/python scripts/summary.py
```

Observações:
- A cota gratuita do Flash-Lite é de **500 requisições por dia**. As duas
  execuções juntas usam ~770 requisições, então levam 2 dias.
- `scripts/status.sh <config>` mostra o progresso.
- `scripts/runner.sh`, instalado como serviço com o modelo em `scripts/systemd/`,
  roda a fila sozinho e retoma depois de quedas de energia ou de internet.
- Para conferir os resultados sem rodar nada, extraia o pacote completo:
  `tar -xzf results/resultados_completos.tar.gz`. Ele traz todos os artefatos
  intermediários, os logs e os relatórios de avaliação (inclusive do oráculo).

## Abordagem agêntica (comparação)

Para comparar o Agentless com um agente, usamos o
[mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) (dos autores do
SWE-agent e do SWE-bench). O agente tem só uma ferramenta, o bash: ele explora o
repositório, roda comandos e edita arquivos em vários turnos, até enviar um
`git diff`. O runner próprio fica em `scripts/agentic/run_agent.py`.

Para a comparação ser justa, o agente usa:
- **o mesmo LLM**: Gemini 3.1 Flash-Lite, no mesmo endpoint, com `reasoning_effort=none`;
- **as mesmas 47 issues** (`data/subset_47.txt`);
- **as mesmas imagens Docker** e **a mesma avaliação** do SWE-bench.

O que é próprio do agente:
- **Limite de 50 passos por issue** (o padrão do mini-SWE-agent é 250). Cada
  passo é uma chamada ao LLM, e a cota grátis é de 500 chamadas por dia.
- **Temperatura 0**, com uma única tentativa por issue. O Agentless gera 6
  patches e escolhe um.
- **Autosubmit**: se o agente atingir o limite de passos sem enviar o patch, o
  `git diff` atual é enviado, como faz o SWE-agent.
- **Cota diária**: quando ela acaba, a issue em andamento é descartada e refeita
  do zero no dia seguinte. Ela não conta como patch vazio.

**Outro modelo, GPT-6 Luna** (`scripts/configs/agent_luna.env`): o mesmo agente,
com as mesmas issues e limites, usando o `gpt-6-luna` da OpenAI (US$ 0,10 por 1M
tokens de entrada e US$ 0,50 por 1M de saída) com `reasoning_effort=medium`,
como na config do Luna para o Agentless. Por ser pago, tem dois tetos de gasto:
US$ 0,50 por issue e US$ 5 no total (`AGENT_BUDGET`). Ao atingir o teto total, a
execução para e pode ser retomada depois.

```bash
# ambiente separado: o mini-SWE-agent precisa de versões mais novas que as do Agentless
uv venv --python 3.11 .venv-agent
uv pip install -p .venv-agent -r requirements-agent.lock.txt

CONFIG=scripts/configs/agent_flashlite.env scripts/pipeline.sh agentic

# mesmo agente com o GPT-6 Luna da OpenAI (pago: exige OPENAI_API_KEY no .env)
CONFIG=scripts/configs/agent_luna.env scripts/pipeline.sh agentic

# custo, tokens e diferença pareada contra o Agentless e contra o paper
.venv/bin/python scripts/extra_metrics.py --nome Agente \
    --runs results/agent_flashlite:data/subset_47.txt \
    --contra results/flashlite_reduced:data/subset_15.txt \
             results/flashlite_reduced_ext:data/subset_ext.txt \
    --out results/summary/METRICAS_AGENTE.md
```

## Estrutura

```
agentless/                 código do Agentless (original + adaptações acima)
scripts/
  pipeline.sh              todas as etapas do paper, retomáveis
  configs/*.env            configuração de cada execução (modelo, amostras, issues)
  make_subset.py           filtro do Lite-S e amostragem estratificada
  summary.py               tabelas agregadas e CSV por issue
  oracle_eval.py / oracle_run.sh   avaliação de todos os candidatos (oráculo)
  compare_runs.py          localização: replicação × paper
  extra_metrics.py         custo por issue resolvida e diferença pareada com IC
  agentic/run_agent.py     abordagem agêntica (mini-SWE-agent) com o mesmo LLM
  compare_all.py           todas as abordagens lado a lado (COMPARACAO.md)
  runner.sh, status.sh, systemd/   execução sem supervisão
  download_data.sh         dados grandes que não ficam no repositório
data/subset_*.txt          as issues usadas (15, 40, as 32 da extensão e a união de 47)
results/
  summary/                 RESUMO.md, COMPARACAO.md e as tabelas por issue
  flashlite_reduced*/, luna_reduced*/   relatório oficial e patch escolhido de cada issue
  agent_*/                 agente: relatório, patches, uso por issue e trajetórias (.tar.gz)
  resultados_completos.tar.gz   todos os artefatos (33 MB)
docs/EXPLICACAO_COMPLETA.md     o trabalho inteiro explicado
```

## Créditos e licença

Código original © 2024 OpenAutoCoder, sob a [licença MIT](LICENSE), mantida neste
fork. Se usar este trabalho, cite o paper original:

```bibtex
@article{agentless,
  author    = {Xia, Chunqiu Steven and Deng, Yinlin and Dunn, Soren and Zhang, Lingming},
  title     = {Agentless: Demystifying LLM-based Software Engineering Agents},
  year      = {2024},
  journal   = {arXiv preprint},
}
```
