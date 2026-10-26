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

- **Não há diferença estatística** (teste de McNemar exato, p = 1,00), com uma
  configuração ~5 vezes mais barata em chamadas ao LLM.
- **Oráculo:** se a escolha do patch fosse perfeita, chegaríamos a 19/47. A
  seleção perde só 2 issues, e em 28 nenhum candidato funciona. **O gargalo é a
  geração de patches, não a seleção.**
- Os embeddings locais (`bge-small`) encontraram o arquivo certo em 91,5% das
  issues, contra 83,0% com os embeddings da OpenAI usados no paper.

Tabelas completas em [`results/summary/RESUMO.md`](results/summary/RESUMO.md).
Explicação de todo o trabalho (método, decisões, problemas e limitações) em
[`docs/EXPLICACAO_COMPLETA.md`](docs/EXPLICACAO_COMPLETA.md).

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
  runner.sh, status.sh, systemd/   execução sem supervisão
  download_data.sh         dados grandes que não ficam no repositório
data/subset_*.txt          as issues usadas (15, 40 e as 32 da extensão)
results/
  summary/                 RESUMO.md e por_issue.csv
  flashlite_reduced*/      relatório oficial e patch escolhido de cada issue
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
