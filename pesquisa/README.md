# Pesquisa: Agentless com LLMs baratos × abordagens agênticas

Trabalho da disciplina de IA Generativa do mestrado (UFF). O ponto de partida é
a replicação do paper **[Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489)**
(Xia, Deng, Dunn e Zhang, 2024) no SWE-bench Lite-S, trocando o GPT-4o por
modelos baratos. Depois, o Agentless é comparado com abordagens agênticas que
usam o mesmo modelo, nas mesmas issues.

Tudo o que é nosso está nesta pasta. O código do Agentless fica na raiz do
repositório, com as adaptações descritas em
[O que mudou no código do Agentless](#o-que-mudou-no-código-do-agentless).

## Resultados

Todas as execuções usam as **mesmas 47 issues** do SWE-bench Lite-S, sorteadas
com estratificação por repositório, e a avaliação oficial do SWE-bench em Docker.

<!-- comparacao:inicio -->
| Abordagem | Modelo | Resolvidas | US$ por issue resolvida |
|---|---|---|---|
| Agentless (paper) | GPT-4o | 18/47 (38,3%) | ≈1,83 (estimado) |
| Agentless, rodada 1 | Gemini 3.1 Flash-Lite | 17/47 (36,2%) | 0,051 |
| Agentless, rodada 2 | Gemini 3.1 Flash-Lite | 17/47 (36,2%) | 0,051 |
| Agentless | GPT-6 Luna | 24/47 (51,1%) | 0,026 |
| Agente (mini-SWE-agent) | GPT-6 Luna | 30/47 (63,8%) | 0,022 |
| Agentless | Claude Haiku 5.5 | sem dados no repositório | — |
| Agente (Claude Code) | Claude Haiku 5.5 | sem dados no repositório | — |
<!-- comparacao:fim -->

A tabela acima é gerada por `pesquisa/scripts/compare_all.py` a partir dos
relatórios de avaliação. Os relatórios do Haiku ainda não estão no repositório.
Pelos documentos da execução, o **Agentless com Haiku 5.5 resolveu 28/47
(59,6%)** e o **agente Claude Code com Haiku 5.5 resolveu 32/47 (68,1%)**
([RESULTADOS_HAIKU.md](docs/RESULTADOS_HAIKU.md),
[RESULTADOS_AGENTICO_HAIKU.md](docs/RESULTADOS_AGENTICO_HAIKU.md)).

Principais conclusões:

- **A replicação confirma o paper.** Com Flash-Lite e só 6 patches por issue
  (o paper usa 40), resolvemos 17/47, contra 18/47 do paper. Não há evidência
  de diferença (McNemar exato, p = 1,00), mas isso **não prova equivalência**:
  a diferença pareada é de −2,1 p.p., com IC 95% de [−14,9; +10,6].
- **O gargalo do Agentless é gerar, não escolher.** Se a seleção de patches
  fosse perfeita (oráculo), o Flash-Lite chegaria a 19/47. A seleção perde só 2
  issues.
- **Modelo melhor ajuda o Agentless:** trocar o Flash-Lite pelo Luna ganhou 9
  issues e perdeu 2 (p = 0,065).
- **Com o mesmo modelo, o agente resolveu mais que o Agentless**, mas a
  diferença não é significativa com 47 issues. Com o Luna, foram 7 issues a
  favor do agente contra 1 (p = 0,070); com o Haiku, 7 contra 3 (p = 0,34).
- **Custo por issue resolvida** ficou entre US$ 0,005 e US$ 0,05 em todas as
  nossas execuções, contra ≈US$ 1,83 estimados para o paper.

A execução do agente mini-SWE-agent com Flash-Lite foi interrompida em 33 de 47
issues, por causa da cota gratuita, e ficou fora da comparação.

## Documentos

| Documento | Conteúdo |
|---|---|
| [docs/EXPLICACAO_COMPLETA.md](docs/EXPLICACAO_COMPLETA.md) | O trabalho inteiro: método, amostra, decisões, problemas de ambiente, resultados e limitações da replicação |
| [docs/METRICAS_NOVAS.md](docs/METRICAS_NOVAS.md) | Custo por issue resolvida e diferença pareada com IC (bootstrap) |
| [docs/RESULTADOS_HAIKU.md](docs/RESULTADOS_HAIKU.md) | Agentless com Claude Haiku 5.5 |
| [docs/RESULTADOS_AGENTICO_HAIKU.md](docs/RESULTADOS_AGENTICO_HAIKU.md) | Agente Claude Code com Claude Haiku 5.5 |
| [results/summary/COMPARACAO.md](results/summary/COMPARACAO.md) | Todas as abordagens lado a lado: resolução, IC de Wilson, custo, testes pareados e resultado por repositório |
| [results/summary/RESUMO.md](results/summary/RESUMO.md) | Replicação com Flash-Lite: localização, seleção e oráculo |
| `results/summary/METRICAS_*.md` | Custo por etapa e comparações pareadas de cada execução |

## Estrutura

```
pesquisa/
  README.md                 este arquivo
  docs/                     documentos do trabalho (tabela acima)
  data/
    subset_15.txt           lote 1 (15 issues)
    subset_ext.txt          lote 2 (32 issues)
    subset_47.txt           união dos dois lotes, usada em todas as comparações
    subset_40.txt           amostra estratificada de onde saiu o lote 2
    paper_results/official_results.json   issues resolvidas pelo paper
  scripts/
    pipeline.sh             todas as etapas do Agentless, retomáveis
    configs/*.env           configuração de cada execução (modelo, amostras, issues)
    agentic/run_agent.py    agente mini-SWE-agent (Gemini ou OpenAI)
    agentic/run_agentic.py  agente Claude Code (Anthropic), com fix_preds.py
    summary.py              replicação: resolução, localização, seleção e oráculo
    compare_all.py          todas as abordagens lado a lado (COMPARACAO.md)
    extra_metrics.py        custo por issue resolvida e diferença pareada com IC
    compare_runs.py         localização: nossa execução × paper
    oracle_eval.py, oracle_run.sh   avaliação de todos os candidatos (oráculo)
    make_subset.py          filtro do Lite-S e amostragem estratificada
    runner.sh, status.sh, systemd/  execução sem supervisão
    download_data.sh        dados grandes que não ficam no repositório
  results/
    summary/                tabelas geradas pelos scripts
    <execução>/             relatório oficial (eval_report.json) e patches de cada execução
    agent_luna/             também o uso por issue e as trajetórias (.tar.gz)
    resultados_completos.tar.gz   artefatos intermediários da replicação com Flash-Lite
  requirements-replication.lock.txt   versões exatas para o Agentless
  requirements-agent.lock.txt         versões exatas para o mini-SWE-agent
  .env.example              modelo do arquivo de chaves
```

## O que mudou no código do Agentless

O método não foi alterado. As mudanças são de infraestrutura:

- **Novos backends de LLM** em `agentless/util/model.py`: `gemini` e `nvidia`
  (APIs compatíveis com OpenAI), `openai-reasoning` (GPT-6 Luna),
  `anthropic-compat` e `anthropic-native` (Claude Haiku 5.5). Todos com controle
  de requisições e tokens por minuto, novas tentativas em erros 429/500/503 e
  parada quando a cota diária acaba.
- **Embeddings locais** via `AGENTLESS_LOCAL_EMBED_MODEL`, no lugar dos da OpenAI
  (`agentless/fl/Index.py`).
- **Subconjunto de issues** via `AGENTLESS_INSTANCE_IDS_FILE`
  (`agentless/util/utils.py`).
- **Limite de contexto configurável** (`AGENTLESS_MAX_CONTEXT_LENGTH`; o padrão
  continua 128k).
- **Correções para retomar execuções interrompidas**, incluindo um bug do
  original no `retrieve.py`.

## Como reproduzir

Requisitos: Linux, Docker, ~120 GB de disco para as imagens do SWE-bench e as
chaves das APIs que for usar. Todos os comandos rodam **a partir da raiz do
repositório**.

```bash
# 1. ambiente Python 3.11 com as versões exatas usadas
uv venv --python 3.11 .venv
uv pip install -p .venv -r pesquisa/requirements-replication.lock.txt

# 2. chaves das APIs (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)
cp pesquisa/.env.example .env

# 3. dados grandes (estruturas dos repositórios e resultados do paper)
pesquisa/scripts/download_data.sh

# 4. Agentless: etapas de LLM e depois Docker (testes, seleção e avaliação)
CONFIG=pesquisa/scripts/configs/flashlite_reduced.env pesquisa/scripts/pipeline.sh llm
CONFIG=pesquisa/scripts/configs/flashlite_reduced.env pesquisa/scripts/pipeline.sh exec
# o mesmo com *_reduced_ext.env para o lote 2, e com luna_* ou haiku_* para os outros modelos

# 5. agente mini-SWE-agent (ambiente separado, versões mais novas)
uv venv --python 3.11 .venv-agent
uv pip install -p .venv-agent -r pesquisa/requirements-agent.lock.txt
CONFIG=pesquisa/scripts/configs/agent_luna.env pesquisa/scripts/pipeline.sh agentic

# 6. agente Claude Code (exige o claude CLI e ANTHROPIC_API_KEY no ambiente)
.venv/bin/python pesquisa/scripts/agentic/run_agentic.py --out pesquisa/results/haiku_agentic

# 7. tabelas
.venv/bin/python pesquisa/scripts/summary.py
.venv/bin/python pesquisa/scripts/compare_all.py
```

Observações:
- A cota gratuita do Flash-Lite é de **500 requisições por dia**. As duas
  execuções do Agentless juntas usam ~770 requisições, então levam 2 dias.
- `pesquisa/scripts/status.sh <config>` mostra o progresso.
- `pesquisa/scripts/runner.sh`, instalado como serviço com o modelo em
  `pesquisa/scripts/systemd/`, roda a fila sozinho e retoma depois de quedas de
  energia ou de internet.
- Para conferir a replicação sem rodar nada, extraia o pacote completo a partir
  da raiz (o pacote foi criado antes da reorganização, por isso o `--transform`):
  `tar -xzf pesquisa/results/resultados_completos.tar.gz --transform 's#^results/#pesquisa/results/#'`.

## Créditos e licença

Código original do Agentless © 2024 OpenAutoCoder, sob a
[licença MIT](../LICENSE). Cite o paper original:

```bibtex
@article{agentless,
  author    = {Xia, Chunqiu Steven and Deng, Yinlin and Dunn, Soren and Zhang, Lingming},
  title     = {Agentless: Demystifying LLM-based Software Engineering Agents},
  year      = {2024},
  journal   = {arXiv preprint},
}
```
