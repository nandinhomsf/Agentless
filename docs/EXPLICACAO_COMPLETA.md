# Replicação do Agentless: o que foi feito, por quê e o que encontramos

Documento-base para a apresentação. Cobre o problema, o paper, todas as
decisões tomadas (com os motivos), os problemas encontrados, os resultados e o
que eles significam para a próxima etapa (a melhoria).

---

## 1. O problema que o paper ataca

### 1.1 Resolver issues do GitHub automaticamente

Uma *issue* é um relato de bug (ou pedido de funcionalidade) aberto num
repositório do GitHub. Resolver uma issue significa produzir um **patch**: uma
alteração no código-fonte (um *diff*) que corrige o problema.

A pergunta da área é: dado só o texto da issue e o repositório, um LLM consegue
gerar sozinho o patch correto?

### 1.2 O benchmark SWE-bench

O **SWE-bench** (Jimenez et al., 2024) é o benchmark padrão para essa tarefa.
Cada problema é uma issue real de um de 12 projetos Python populares (Django,
sympy, scikit-learn, matplotlib, pytest, sphinx, astropy etc.) junto com:

- o **commit** do repositório no momento em que a issue foi aberta;
- o **patch oficial** (*gold patch*) que os desenvolvedores escreveram;
- os **testes** que os desenvolvedores adicionaram junto com a correção.

**Como se decide se uma issue foi resolvida.** O patch da ferramenta é aplicado
ao repositório, dentro de um container **Docker** com o ambiente exato daquela
versão do projeto, e dois grupos de testes são rodados:

- **FAIL_TO_PASS**: testes que falhavam antes da correção e devem passar depois.
  Eles verificam se o bug foi de fato corrigido.
- **PASS_TO_PASS**: testes que já passavam e devem continuar passando. Eles
  verificam se nada foi quebrado.

A issue conta como **resolvida** só se os dois grupos passarem. A ferramenta
**nunca vê esses testes**; eles servem apenas para a avaliação.

**SWE-bench Lite** é um subconjunto de **300** issues, mais autocontidas e
focadas em correção de bugs. É o conjunto usado na tabela principal do paper.

### 1.3 Agentes × Agentless

Em 2024, as abordagens de ponta eram **agentes**: o LLM recebe ferramentas
(abrir arquivo, buscar, editar, rodar comandos) e decide sozinho, em dezenas de
turnos, o que fazer em seguida (Devin, SWE-agent, OpenDevin, AutoCodeRover...).

O paper argumenta que agentes têm três problemas:

1. **ferramentas complexas**, que o LLM usa de forma errada;
2. **pouco controle** sobre as decisões, que viram trajetórias de 30 a 40 turnos
   difíceis de depurar;
3. **pouca autorreflexão**: um passo errado contamina todos os seguintes.

A pergunta do paper: **precisamos mesmo de agentes complexos?**

---

## 2. O paper: Agentless (Xia, Deng, Dunn, Zhang, UIUC, 2024, arXiv 2407.01489)

### 2.1 A ideia

Um pipeline **fixo**, com três fases. O LLM executa cada etapa, mas **não decide
qual é o próximo passo** e não usa ferramentas.

### 2.2 Fase 1: localização hierárquica

O objetivo é descobrir **onde** editar, afunilando de arquivos para linhas.

1. **Arquivos.**
   - O LLM recebe a issue e a **estrutura de pastas** do repositório (como o
     comando `tree`) e aponta os arquivos mais suspeitos.
   - Em paralelo, uma **busca por embeddings**: o LLM primeiro descarta pastas
     irrelevantes; o código restante é dividido em trechos, e são buscados os
     trechos mais parecidos com o texto da issue.
   - As duas listas são combinadas e ficam os **3 arquivos** mais citados.
2. **Elementos.** Para cada arquivo, o LLM recebe só um "esqueleto" (assinaturas
   de classes e funções, sem o corpo) e escolhe as classes e funções relevantes.
3. **Linhas de edição.** O LLM recebe o código completo desses elementos e aponta
   as linhas exatas. Essa etapa é **amostrada várias vezes** (no paper, **4
   vezes**), o que gera 4 conjuntos de locais diferentes.

### 2.3 Fase 2: reparo

Para cada conjunto de locais, o LLM recebe o código ao redor (±10 linhas) e gera
patches no formato **Search/Replace** ("procure este trecho, substitua por
este"). É mais barato e confiável que reescrever o arquivo inteiro.

No paper são **10 patches por conjunto de locais** (1 com temperatura 0, o
"greedy", e 9 amostrados com temperatura 0,8). Daí o **4×10 = 40 patches por
issue**.

### 2.4 Fase 3: validação e seleção do patch

Com 40 candidatos, é preciso escolher **um** para submeter.

1. **Testes de regressão.** São rodados os testes que já existem no repositório
   e passam no código original. O LLM remove os que deveriam mudar com a
   correção. Ficam os patches com **menos falhas**.
2. **Testes de reprodução.** O LLM escreve um script que reproduz o bug e imprime
   "Issue reproduced" (bug presente) ou "Issue resolved" (bug corrigido).
   - No paper são gerados **40 scripts**.
   - Ficam só os que imprimem "Issue reproduced" no código original.
   - Entre eles, o mais frequente é o escolhido.
   - Ficam os patches que fazem esse script imprimir "Issue resolved".
3. **Votação por maioria.** Os patches restantes são normalizados (código
   reformatado e comentários removidos) e o mais frequente vence.

### 2.5 Resultados do paper

- **SWE-bench Lite:** **96/300 = 32,0%** resolvidas com GPT-4o, a **US$ 0,70 por
  issue**. Foi o melhor resultado entre as ferramentas de código aberto da época.
- **Lite-S:** os autores classificaram manualmente as 300 issues e encontraram
  problemas no benchmark:
  - 4,3% trazem o patch exato no texto da issue;
  - 10% não têm informação suficiente;
  - 5% sugerem uma solução enganosa.
  Removendo essas, sobra o **SWE-bench Lite-S, com 249 issues**, onde o Agentless
  faz 84/249 = 33,7%.
- **Ablações** (quanto cada parte contribui):
  - só a votação por maioria: 77; com regressão: 81; com reprodução: 96;
  - considerando **todos** os 40 patches, e não só o escolhido, o teto seria
    **126/300 = 42%**.
- **Impacto:** a OpenAI adotou o Agentless para apresentar o GPT-4o e o o1 no
  SWE-bench Verified.

---

## 3. O nosso trabalho: objetivo e restrições

**Objetivo:** (1) replicar o paper; (2) propor e testar uma melhoria.

**Restrições que guiaram todas as decisões:**

| Restrição | Consequência |
|---|---|
| LLM **gratuito** | GPT-4o estava fora de cogitação (~US$ 210 para as 300 issues) |
| Notebook com **12 GB de RAM**, sem GPU dedicada | sem LLM local grande; Docker com 1 container por vez |
| Prazo de **poucos dias** para a replicação | subconjunto de issues em vez das 300 |
| Energia e internet instáveis em casa | o pipeline precisou ser retomável |

---

## 4. Como replicamos

### 4.1 Base: o código oficial

Usamos o código aberto dos autores (github.com/OpenAutoCoder/Agentless, versão
de dezembro de 2024) e o avaliador oficial do SWE-bench, versão 2.1.8, da mesma
época. **O método não foi reescrito.** As mudanças são adaptações de
infraestrutura, todas listadas na seção 7.

### 4.2 De onde vieram as 47 issues

```
SWE-bench Lite (300 issues)
   │  filtro do próprio paper (seção 6.2): remove "informação insuficiente",
   │  "solução enganosa" e "patch exato na issue"
   ▼
SWE-bench Lite-S (249 issues)   ← reproduzimos o filtro e obtivemos exatamente 249
   │  amostragem aleatória ESTRATIFICADA POR REPOSITÓRIO, semente 42
   ├──► amostra de 40 issues (subset_40)
   └──► amostra de 15 issues (subset_15)     ← sorteadas separadamente

Execução 1: as 15 issues do subset_15
Execução 2 ("extensão"): as 32 do subset_40 que não estão no subset_15 (8 se repetem)
Total: 15 + 32 = 47 issues distintas
```

**Por que Lite-S e não Lite:** é a versão "limpa" proposta pelo próprio paper.
Ela evita issues impossíveis (sem informação) ou triviais (com a resposta no
texto).

**Por que estratificar por repositório:** o Django é ~1/3 do benchmark e o sympy
~1/4. Uma amostra pequena e puramente aleatória poderia, por azar, ficar quase
toda num repositório só. A estratificação mantém a proporção do Lite-S.

**Por que 15 e depois 47:**
- Começamos com 40 issues.
- Quando o LLM gratuito se mostrou lento e com cota baixa (seção 5), reduzimos
  para 15 para caber no prazo.
- Quando migramos para um modelo rápido, sobrou capacidade e completamos as 32
  restantes do subset_40.

*Observação honesta:* as 47 são a **união de duas amostras estratificadas**, e
não uma única amostra. A proporção por repositório continua próxima da do Lite-S,
mas não é exata.

**Comparação justa com o paper.** Os autores publicaram os resultados de cada
issue (repositório `swe-bench/experiments`, pasta
`20241028_agentless-1.5_gpt4o`, com 96/300, o mesmo número do paper) e todos os
artefatos intermediários. Por isso comparamos **na mesma lista de issues**, e
não com os 32% do paper inteiro. Nessas 47, o paper resolve 18 (38,3%). É mais
que 32% porque o Lite-S é mais fácil e a amostra é pequena.

### 4.3 O modelo: Gemini 3.1 Flash-Lite, e por que ele

O modelo mudou três vezes. Cada mudança teve um motivo medido:

| Tentativa | O que aconteceu | Decisão |
|---|---|---|
| **Gemini 3.8 Flash** (gratuito) | Cota real de **20 requisições por dia**. O Agentless faz ~90 por issue | Inviável |
| **NVIDIA NIM** (Qwen3-Coder etc.) | Exigiria cadastro e contato com o suporte; sem tempo | Descartado |
| **Gemma 4 31B** (mesma chave do Gemini) | Funcionou, mas: ~1 a 5 min por resposta; raciocínio de >5 mil tokens embutido na resposta (cortava o patch); limite de **16 mil tokens de entrada por minuto**; erros 503 frequentes; em 15/10 o endpoint passou a dar **erro 500 em qualquer pedido** | Abandonado (a localização feita com ele foi guardada) |
| **Gemini 3.1 Flash-Lite** | Responde em segundos; aceita `reasoning_effort=none` (sem raciocínio, como o GPT-4o); aceita prompts grandes; cota de **500 requisições por dia** e **15 por minuto** | **Usado na replicação final** |

**Por que "sem raciocínio" importa:** o GPT-4o do paper não é um modelo de
raciocínio. Desligar o raciocínio do Flash-Lite deixa o experimento mais
parecido com o original.

### 4.4 Configuração reduzida: 2×3 patches e 4 testes (contra 4×10 e 40)

| Parâmetro | Paper | Nós | Por quê |
|---|---|---|---|
| Conjuntos de locais de edição | 4 | **2** | cota |
| Patches por conjunto | 10 | **3** | cota |
| **Patches por issue** | **4×10 = 40** | **2×3 = 6** | cota |
| Testes de reprodução gerados | 40 | **4** | cota |
| **Chamadas ao LLM por issue** | **~88** | **~16** | — |

**A conta:** com 500 requisições por dia, a configuração do paper permitiria
~5 issues por dia. A reduzida permite ~30.

**Por que isso ainda é uma replicação válida:** a Figura 6 do paper mostra que o
ganho com mais amostras satura rápido. Com só 1 patch por conjunto de locais, o
paper já resolve 80 das 96 issues. Reduzir as amostras é uma **ablação
controlada**, e os nossos resultados confirmam que pouco se perde (seção 8).

### 4.5 Outras adaptações (sem mudar o método)

- **Embeddings:** o paper usa o `text-embedding-3-small` da OpenAI, que é pago.
  Trocamos pelo **`BAAI/bge-small-en-v1.5`**, que roda localmente na CPU e é
  gratuito. Os trechos de código continuam com 512 tokens.
- **Limite de contexto:** voltou ao do paper (128 mil tokens) com o Flash-Lite.
  Ele só tinha sido reduzido na tentativa com o Gemma.
- **Testes de regressão:** como no paper, rodamos os testes existentes e o LLM
  filtra a lista. **Não** usamos o campo PASS_TO_PASS do benchmark, que daria
  uma vantagem indevida.

---

## 5. Linha do tempo resumida

| Data | Evento |
|---|---|
| 14/10 | Leitura do paper, ambiente montado, chave do Gemini, Flash com 20 req/dia, troca para Gemma |
| 14/10 | **Falta de memória (OOM)**: builds Docker em paralelo com o LLM derrubaram o VS Code |
| 15/10 | Gemma: limite de 16k tokens/min; uma issue grande demais; Gemma passa a dar erro 500 |
| 15/10 | Troca para Flash-Lite; LLM das 15 issues em **36 min**; Docker a seguir |
| 15–16/10 | Correção das imagens Docker do scikit-learn; execução 1 termina: **4/15** |
| 16/10 | Fila automática criada; extensão para +32 issues; **cota diária de 500 esgota** às 12h30 |
| 16/10 | Internet cai de madrugada; o pipeline espera e retoma sozinho |
| 17/10 | Extensão termina: **13/32**. Total: **17/47** |
| 24–26/10 | Diagnóstico da seleção e **oráculo**: 19/47 |

---

## 6. A infraestrutura de execução

- **Pipeline** (`scripts/pipeline.sh`): roda as etapas do README oficial. Cada
  etapa **pula o que já foi feito**, então qualquer interrupção é retomável.
- **Controle de ritmo do LLM:** respeita requisições/minuto e tokens/minuto. Na
  cota diária, para e espera. Em erros 429/500/503, espera cada vez mais antes de
  tentar de novo. **Nunca grava resposta vazia**: se falhar, a issue é refeita
  depois.
- **Fila automática** (`scripts/runner.sh` e o serviço `agentless-runner`):
  inicia junto com o computador, espera a internet e o Docker e continua a fila.
  Sobreviveu a uma queda de internet de ~5h30.
- **Docker:** ~50 imagens (base, ambientes por versão de projeto e uma por
  issue), ~110 GB em disco. Um container por vez, para não estourar a RAM.

---

## 7. Problemas encontrados e correções

Os detalhes técnicos estão no Apêndice A e na configuração de cada
execução.

| Problema | Causa | Correção |
|---|---|---|
| Código não rodava com bibliotecas atuais | `swebench` 5.x e `modal` 1.x mudaram de API | Versões de 2024 fixadas (`requirements-replication.lock.txt`) |
| `--model` só aceitava modelos da OpenAI/Anthropic | lista fixa no código | lista removida e backend `gemini` adicionado |
| Respostas vazias gravadas como resultado | código original desiste após 40 tentativas e grava `""` | falha explícita; a issue é refeita depois |
| Gemma: o raciocínio vinha na resposta e cortava o patch | modelo de raciocínio | remoção do bloco `<thought>` e mais orçamento de tokens |
| Gemma: um prompt de 17k tokens nunca era aceito | limite de 16k tokens/min | limite de contexto configurável (só nessa tentativa) |
| **Bug do código original:** `retrieve.py` falhava ao retomar | usa o `logger` antes de criá-lo | 1 linha corrigida |
| `combine.py` falhava ao retomar | recusa sobrescrever a saída | etapa pulada se já feita |
| **Falta de memória** derrubou o VS Code | builds Docker em paralelo com o LLM | nunca em paralelo; 1 worker; processos fora do VS Code |
| Imagem Docker do **scikit-learn** não construía | o pacote `qt-main` do conda (atual) falha com `set -u`; o pip 25.3+ removeu `--no-use-pep517` | camadas extras na imagem: variável definida e `pip==24.0` |
| Imagem do **pylint** não construía | o pip 26 removeu o modo editável antigo | `pip==24.0` na imagem |

**Por que tantos problemas de versão:** o avaliador de 2024 instala pacotes "do
dia" ao construir as imagens. Dois anos depois, vários desses pacotes mudaram de
comportamento. As correções **não alteram os testes nem o código avaliado**; só
devolvem o ambiente ao comportamento da época.

---

## 8. Resultados

### 8.1 Resolução (47 issues)

| | Resolvidas | IC 95% |
|---|---|---|
| Paper (GPT-4o, 40 patches, 40 testes) | **18/47 (38,3%)** | [26%, 53%] |
| Nós (Flash-Lite, 6 patches, 4 testes) | **17/47 (36,2%)** | [24%, 50%] |

- Os dois resolveram 12; só nós, 5; só o paper, 6; nenhum dos dois, 24.
- Execução 1 (15 issues): paper 6, nós 4. Extensão (32): paper 12, nós 13.
- Por repositório: a maior diferença está no Django (8 contra 6).

**Como ler a estatística:**
- **IC 95% (Wilson):** a faixa onde a taxa "verdadeira" provavelmente está. Com
  47 issues, a faixa tem ~±13 pontos percentuais, e as duas faixas se sobrepõem
  quase inteiras.
- **Teste de McNemar (exato):** compara os dois sistemas **nas mesmas issues**,
  olhando só os desacordos (5 contra 6). Deu **p = 1,00**: não há diferença
  estatística.

### 8.2 Localização (o arquivo do patch oficial foi encontrado?)

| Etapa | Paper | Nós |
|---|---|---|
| Arquivos via LLM | 85,1% | 80,9% |
| Arquivos via embeddings | 83,0% | **91,5%** |
| Arquivos combinados | 91,5% | 87,2% |
| Elementos relacionados | 85,1% | 83,0% |
| Patch final no arquivo certo | 70,2% | **76,6%** |

### 8.3 Diagnóstico da seleção (nossa execução)

| Situação | Issues | Resolvidas |
|---|---|---|
| Com teste de reprodução e ≥1 patch passando nele | 18 | 55,6% |
| Com teste, mas nenhum patch passa | 19 | 26,3% |
| Sem teste de reprodução válido | 10 | 20,0% |

- Patches distintos por issue: **3,3 em média** (de 6 gerados); 7 issues
  tiveram um único patch distinto.

### 8.4 Oráculo: o melhor possível com os patches gerados

Avaliamos no Docker **todos os 156 patches distintos** para saber em quantas
issues **algum** candidato estava correto.

| | Resolvidas |
|---|---|
| Patch escolhido pelo Agentless | 17/47 (36,2%) |
| **Oráculo** (melhor candidato possível) | **19/47 (40,4%)** |

Só **2 issues** foram perdidas na escolha (`django__django-12915` e
`matplotlib__matplotlib-25498`). No paper, a distância era de 96 para 126 (10
pontos percentuais); no nosso caso, é de 4 pontos.

---

## 9. Interpretação

1. **A replicação confirma a tese do paper.** Um pipeline simples e fixo, sem
   agente, resolve ~36–38% das issues do Lite-S, mesmo com um modelo bem menor e
   gratuito.
2. **40 patches e 40 testes não são necessários** para chegar a esse patamar.
   Com 6 e 4, empatamos estatisticamente. Isso reforça a saturação mostrada na
   Figura 6 do paper e reduz o custo em ~5 vezes.
3. **Embeddings locais e gratuitos bastam.** O `bge-small` encontrou o arquivo
   certo com mais frequência que os embeddings da OpenAI.
4. **Os testes de reprodução são a peça que mais pesa**: 41% de resolução com
   teste, contra 20% sem. Mas eles também erram: em 5 issues rejeitaram todos os
   patches, inclusive o correto.
5. **O gargalo agora é gerar, não escolher.** O oráculo mostra que a seleção já
   aproveita quase tudo o que existe: 17 de 19 possíveis. Para resolver mais
   issues, é preciso **gerar patches corretos onde hoje não há nenhum**: há 28
   issues em que nenhum dos candidatos resolve.

---

## 10. Limitações (ameaças à validade)

- **Tamanho da amostra:** 47 issues dão intervalos de ~±13 pontos percentuais.
  Diferenças pequenas não são detectáveis.
- **União de duas amostras:** as 47 issues não formam uma única amostra
  estratificada (seção 4.2).
- **Modelo diferente:** a comparação mistura o efeito do modelo (Flash-Lite ×
  GPT-4o) com o da configuração (6 × 40 patches). Não dá para separar os dois.
- **Vazamento de dados:** as issues e os patches do SWE-bench são públicos desde
  2023 e podem estar no treino dos modelos. Vale para o paper e para nós.
- **Ambiente Docker corrigido** em duas imagens (scikit-learn e pylint). Os
  testes não mudaram.
- **Métrica de linhas:** a nossa medida de "linhas corretas" é mais rígida que a
  do paper, então serve só como aproximação. Por isso a apresentação usa a
  métrica de arquivo.
- **Plano gratuito:** cota, sobrecargas (503) e mudanças de modelo fora do nosso
  controle. Isso também é um achado: replicar com recursos gratuitos é possível,
  mas frágil.

---

## 11. Próxima etapa: a melhoria (atualizada pelo oráculo)

Como o oráculo mostrou pouco espaço na seleção (+2 issues no máximo), as
melhorias que **atacam a seleção** têm ganho limitado. As que **geram patches
melhores** têm até 28 issues em aberto.

| Proposta | Ataca | Ganho máximo | Custo de LLM |
|---|---|---|---|
| Votação com vários testes de reprodução | seleção | ≤ 2 issues | zero |
| Juiz LLM para desempatar | seleção | ≤ 2 issues | ~47 chamadas |
| **Refinamento com feedback de execução** (1 rodada) | geração | até 28 issues | ~100–200 chamadas |
| Mais diversidade de patches | geração | até 28 issues | proporcional |

**Recomendação: refinamento com feedback de execução.** Nas issues em que nenhum
patch passa no teste de reprodução, ou em que todos quebram testes de regressão,
o LLM recebe o patch e a **saída do teste que falhou** e faz **uma** correção.

Por que essa proposta:
- **ataca exatamente o gargalo** apontado pelo oráculo;
- é **um meio-termo controlado** entre o Agentless e os agentes: um único ciclo
  de feedback, determinístico e auditável, o que testa a tese do paper de que
  loops de feedback não compensam;
- **cabe na cota gratuita**: ~1 dia de execução;
- **é comparável com rigor**: as mesmas 47 issues, o mesmo modelo e o mesmo
  teste de McNemar contra o nosso próprio resultado (17/47).

---

## 12. Glossário

| Termo | Significado |
|---|---|
| Issue | Relato de bug num repositório do GitHub |
| Patch / diff | Alteração no código que corrige o bug |
| Gold patch | Patch oficial escrito pelos desenvolvedores |
| FAIL_TO_PASS | Testes que só passam com o bug corrigido |
| PASS_TO_PASS | Testes que devem continuar passando |
| Harness | O avaliador oficial do SWE-bench (roda os testes no Docker) |
| Teste de regressão | Teste existente que não pode quebrar |
| Teste de reprodução | Script gerado pelo LLM que mostra o bug |
| Greedy / temperatura | Temperatura 0 dá a resposta mais provável; 0,8 dá respostas variadas (amostras) |
| Embedding | Vetor que representa o significado de um texto, usado na busca por similaridade |
| Oráculo | Melhor resultado possível escolhendo sempre o candidato certo (limite superior) |
| Cota RPD / RPM / TPM | Requisições por dia / por minuto / tokens por minuto |
| IC 95% | Intervalo de confiança de 95% |
| McNemar | Teste estatístico para comparar dois sistemas nos mesmos itens |

---

## 13. Onde está cada coisa

| O quê | Onde |
|---|---|
| Resumo agregado (tabelas) | `results/summary/RESUMO.md` (gerado por `scripts/summary.py`) |
| Resultado por issue (planilha) | `results/summary/por_issue.csv` |
| Relatório oficial e patches escolhidos | `results/flashlite_reduced*/eval_report.json` e `all_preds.jsonl` |
| Todos os artefatos intermediários, logs e relatórios do oráculo | `results/resultados_completos.tar.gz` (`tar -xzf` na raiz do repositório) |
| Configuração de cada execução | `scripts/configs/*.env` |
| Listas de issues | `data/subset_15.txt`, `data/subset_40.txt`, `data/subset_ext.txt` |
| Resultados publicados pelo paper | `data/paper_results/official_results.json`; o restante vem de `scripts/download_data.sh` |
| Versões exatas das bibliotecas | `requirements-replication.lock.txt` |
| Pipeline, fila, status, oráculo, resumo | `scripts/pipeline.sh`, `scripts/runner.sh`, `scripts/status.sh`, `scripts/oracle_eval.py`, `scripts/summary.py` |
| Serviço de retomada automática | `scripts/systemd/agentless-runner.service` |

A tentativa com o Gemma 4 31B não está no repositório: ela foi abandonada antes
do reparo e não entra em nenhum resultado.

---

## Apêndice A. Correções no ambiente de avaliação (Docker)

O avaliador de 2024 (`swebench` 2.1.8) instala pacotes conda/pip na versão
atual no momento em que constrói as imagens. Pacotes lançados depois disso
quebraram três situações. Nenhuma correção altera testes ou código avaliado.

**A.1 Ambiente do scikit-learn** (`sweb.env.x86_64.3a59860bcd0dab8bbfb2ff`)

1. O script de ativação do pacote conda `qt-main` lê a variável
   `QT_XCB_GL_INTEGRATION` sem defini-la. Como todos os scripts do avaliador
   rodam com `set -u`, o `conda activate testbed` aborta, tanto na construção do
   ambiente quanto na instalação do repositório e em cada execução de testes.
2. O pip 25.3 ou mais novo removeu a opção `--no-use-pep517`, que o avaliador
   usa para instalar o repositório.

Correção, aplicada só a essa imagem e marcada com o nome que o avaliador espera
(para ele reutilizá-la):
- a imagem foi construída a partir do próprio contexto de build do avaliador,
  só sem o `-u` no `setup_env.sh`;
- uma camada extra dá um valor padrão vazio a `QT_XCB_GL_INTEGRATION` no
  início do `qt-main_activate.sh`;
- uma camada extra fixa `pip==24.0` no ambiente `testbed`.

Corrigir o avaliador em vez da imagem mudaria o hash de todas as imagens de
ambiente e obrigaria a reconstruir todas.

**A.2 Camada de compatibilidade na imagem base** (a partir da extensão de 32 issues)

Para evitar as mesmas falhas em imagens construídas depois, foi adicionada uma
camada sobre `sweb.base.x86_64:latest` (a original ficou guardada como
`sweb.base.x86_64:original-2024`): `ENV QT_XCB_GL_INTEGRATION=none` e
`conda config --add pinned_packages "pip<25.3"`. O avaliador identifica a imagem
base só pelo nome, então as imagens já construídas não mudam; só as construídas
depois herdam a camada.

**A.3 Ambiente do pylint** (`sweb.env.x86_64.0c609b65ef40b42410cb20`)

Essa imagem tinha o pip 26.0.1. O pip 25 ou mais novo não cai mais para o
`setup.py develop` quando o backend de build não tem `build_editable` (PEP 660),
e o pylint 2.15 fixa `setuptools~=62.6`. Por isso, o `pip install -e .` falhava
ao construir a imagem da issue `pylint-dev__pylint-7993`. Correção: uma camada
extra fixando `pip==24.0` no ambiente `testbed`, marcada com o mesmo nome.

**Como refazer:** os Dockerfiles das camadas são de uma ou duas linhas; o
conteúdo de cada uma está descrito acima.
