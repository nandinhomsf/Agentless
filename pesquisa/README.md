# Agentless × abordagem agêntica com LLMs de baixo custo

Trabalho da disciplina de IA Generativa do mestrado (UFF). Parte do paper
**[Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489)**
(Xia, Deng, Dunn e Zhang, 2024), que propõe um pipeline fixo, sem agente, para
resolver issues de software, e pergunta:

> **Com o mesmo modelo de baixo custo, uma abordagem agêntica resolve mais issues
> do SWE-bench Lite-S que o Agentless? E a que custo?**

Cada abordagem roda com dois modelos, **GPT-6 Luna** e **Claude Haiku 5.5**, nas
mesmas 47 issues e com a avaliação oficial do SWE-bench em Docker. O Agentless
publicado pelos autores (GPT-4o) entra como referência.

Tudo o que é desta pesquisa está nesta pasta. O código do Agentless fica na raiz
do repositório, com as adaptações descritas em
[O que mudou no código do Agentless](#o-que-mudou-no-código-do-agentless).

## Resultados

<!-- comparacao:inicio -->
| Abordagem | Modelo | Resolvidas | IC 95% | US$ por issue resolvida |
|---|---|---|---|---|
| Agentless (paper) | GPT-4o | 18/47 (38,3%) | 26–53% | ≈2,19 |
| Agentless | GPT-6 Luna | **24/47 (51,1%)** | 37–65% | 0,026 |
| Agente (mini-SWE-agent) | GPT-6 Luna | **30/47 (63,8%)** | 50–76% | 0,022 |
| Agentless | Claude Haiku 5.5 | **28/47 (59,6%)** | 45–72% | 0,028 |
| Agente (Claude Code) | Claude Haiku 5.5 | **32/47 (68,1%)** | 54–80% | 0,005 |
<!-- comparacao:fim -->

Principais achados:

- **Com o mesmo modelo, o agente resolveu mais que o Agentless nos dois casos**,
  mas sem significância estatística com 47 issues: com o Luna, 7 issues a favor
  do agente contra 1 (McNemar p = 0,070); com o Haiku, 7 contra 3 (p = 0,34).
- **O agente também saiu mais barato por issue resolvida** nos dois modelos: com
  o Luna, US$ 0,022 contra 0,026; com o Haiku, US$ 0,005 contra 0,028. Todas as
  execuções custaram menos de US$ 0,03 por issue resolvida, contra cerca de
  US$ 2,19 do paper com GPT-4o.
- **Contra o paper**, os dois agentes e o Agentless com Haiku resolveram
  significativamente mais (p ≤ 0,021). O Agentless com Luna não teve diferença
  significativa (p = 0,18).
- **O Agentless perde pouco na seleção do patch.** Se a escolha fosse perfeita
  (oráculo), o Luna iria de 24 para 28 issues e o Haiku de 28 para 33. Com um
  único patch por issue, os agentes chegam perto desse teto.
- **10 issues não foram resolvidas por nenhuma das quatro execuções**, todas com
  patch oficial pequeno, num único arquivo (lista em
  [COMPARACAO.md](results/summary/COMPARACAO.md#não-resolvidas-por-nenhuma-das-nossas-execuções-10)).

## Documentos

| Documento | Conteúdo |
|---|---|
| [docs/METODOLOGIA.md](docs/METODOLOGIA.md) | Pergunta, benchmark, abordagens, amostra, métricas, ameaças à validade e correções no ambiente Docker |
| [results/summary/COMPARACAO.md](results/summary/COMPARACAO.md) | Todas as execuções lado a lado: resolução, IC de Wilson, custo, testes pareados, resultado por repositório e issues não resolvidas |
| [results/summary/agentless_luna/RESUMO.md](results/summary/agentless_luna/RESUMO.md) | Agentless com Luna: localização, seleção de patch, oráculo e custo por etapa |
| [results/summary/agentless_haiku/RESUMO.md](results/summary/agentless_haiku/RESUMO.md) | Agentless com Haiku: localização, seleção de patch, oráculo e custo por etapa |
| [results/summary/METRICAS_AGENTE_LUNA.md](results/summary/METRICAS_AGENTE_LUNA.md) | Agente com Luna: custo e comparação pareada com o Agentless |
| [docs/RESULTADOS_HAIKU.md](docs/RESULTADOS_HAIKU.md) | Agentless com Haiku: relatório da execução |
| [docs/RESULTADOS_AGENTICO_HAIKU.md](docs/RESULTADOS_AGENTICO_HAIKU.md) | Agente Claude Code com Haiku: relatório da execução |

## Estrutura

```
pesquisa/
├── README.md
├── docs/                       metodologia e relatórios das execuções do Haiku
├── data/
│   ├── subset_15.txt           lote 1 (15 issues)
│   ├── subset_ext.txt          lote 2 (32 issues)
│   ├── subset_47.txt           as 47 issues de todas as comparações
│   ├── subset_40.txt           amostra estratificada de onde saiu o lote 2
│   └── paper_results/official_results.json   issues resolvidas pelo paper
├── scripts/
│   ├── pipeline.sh             Agentless: todas as etapas, retomáveis
│   ├── configs/*.env           uma configuração por execução
│   ├── agentic/run_agent.py    agente mini-SWE-agent
│   ├── agentic/run_agentic.py  agente Claude Code (e fix_preds.py)
│   ├── compare_all.py          tabela comparativa (COMPARACAO.md e o bloco acima)
│   ├── summary.py              localização, seleção e oráculo do Agentless
│   ├── extra_metrics.py        custo por etapa e diferença pareada
│   ├── oracle_eval.py, oracle_run.sh   avaliação de todos os candidatos
│   ├── compare_runs.py         localização: nossa execução × paper
│   ├── make_subset.py          filtro do Lite-S e amostragem estratificada
│   ├── status.sh               progresso de uma execução
│   └── download_data.sh        dados grandes que não ficam no repositório
├── results/
│   ├── summary/                tabelas geradas pelos scripts
│   ├── luna_reduced*/          Agentless com Luna (lotes 1 e 2): relatório oficial e patches
│   ├── haiku_reduced*/         Agentless com Haiku (lotes 1 e 2): relatório oficial e patches
│   ├── agent_luna/             agente com Luna: relatório, patches, uso e trajetórias (.tar.gz)
│   └── haiku_agentic/          agente com Haiku: relatórios, patches, custo e trajetórias (.tar.gz)
├── requirements-replication.lock.txt   versões exatas para o Agentless
├── requirements-agent.lock.txt         versões exatas para o mini-SWE-agent
└── .env.example                modelo do arquivo de chaves
```

Os artefatos intermediários do Agentless (localização, candidatos, testes de
reprodução) e os logs ficam fora do repositório por tamanho; os scripts os
regeneram.

## O que mudou no código do Agentless

O método não foi alterado. As mudanças são de infraestrutura:

- **Novos backends de LLM** em `agentless/util/model.py`: `openai-reasoning`
  (GPT-6 Luna), `anthropic-native` e `anthropic-compat` (Claude Haiku 5.5),
  além de `gemini` e `nvidia`. Todos com controle de requisições e tokens por
  minuto, novas tentativas em erros 429/500/503 e sem gravar respostas vazias.
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
chaves `OPENAI_API_KEY` e `ANTHROPIC_API_KEY`. Todos os comandos rodam **a partir
da raiz do repositório**.

```bash
# 1. ambiente Python 3.11 com as versões exatas usadas
uv venv --python 3.11 .venv
uv pip install -p .venv -r pesquisa/requirements-replication.lock.txt
cp pesquisa/.env.example .env            # e preencha as chaves

# 2. dados grandes (estruturas dos repositórios e resultados do paper)
pesquisa/scripts/download_data.sh

# 3. Agentless: etapas de LLM e depois Docker (testes, seleção e avaliação)
for c in luna_reduced luna_reduced_ext haiku_reduced haiku_reduced_ext; do
  CONFIG=pesquisa/scripts/configs/$c.env pesquisa/scripts/pipeline.sh llm
  CONFIG=pesquisa/scripts/configs/$c.env pesquisa/scripts/pipeline.sh exec
done

# 4. agente mini-SWE-agent com Luna (ambiente separado, versões mais novas)
uv venv --python 3.11 .venv-agent
uv pip install -p .venv-agent -r pesquisa/requirements-agent.lock.txt
CONFIG=pesquisa/scripts/configs/agent_luna.env pesquisa/scripts/pipeline.sh agentic

# 5. agente Claude Code com Haiku (exige o claude CLI; avaliação no comentário do script)
.venv/bin/python pesquisa/scripts/agentic/run_agentic.py --out pesquisa/results/haiku_agentic

# 6. oráculo e tabelas
pesquisa/scripts/oracle_run.sh luna_reduced luna_reduced_ext
.venv/bin/python pesquisa/scripts/summary.py
.venv/bin/python pesquisa/scripts/compare_all.py
```

`pesquisa/scripts/status.sh <config>` mostra o progresso de uma execução.

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
