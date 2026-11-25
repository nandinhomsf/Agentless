# Metodologia

Como os experimentos foram montados: a pergunta, o benchmark, as abordagens
comparadas, a amostra, as métricas e as ameaças à validade. Os números estão em
[`results/summary/COMPARACAO.md`](../results/summary/COMPARACAO.md).

---

## 1. Pergunta de pesquisa

O paper do Agentless (Xia et al., 2024) argumenta que um pipeline fixo, sem
agente, resolve issues de software tão bem quanto os agentes da época, com
menos custo e mais controle. Este trabalho pergunta:

> **Com o mesmo modelo de baixo custo, uma abordagem agêntica resolve mais issues
> do SWE-bench Lite-S que o Agentless? E a que custo?**

Para separar o efeito da abordagem do efeito do modelo, cada abordagem roda com
dois modelos (GPT-6 Luna e Claude Haiku 5.5). O Agentless publicado pelos autores
(GPT-4o) entra como referência.

---

## 2. Benchmark e critério de resolução

O **SWE-bench** (Jimenez et al., 2024) reúne issues reais de 12 projetos Python
populares (Django, sympy, scikit-learn, matplotlib, pytest, sphinx, astropy
etc.). Cada issue traz o commit do repositório no momento em que foi aberta, o
patch oficial dos desenvolvedores e os testes que acompanharam a correção.

**Critério de resolução.** O patch gerado é aplicado ao repositório dentro de um
contêiner Docker com o ambiente exato daquela versão do projeto, e são rodados
dois grupos de testes:

- **FAIL_TO_PASS:** testes que falhavam por causa do bug e precisam passar.
- **PASS_TO_PASS:** testes que já passavam e precisam continuar passando.

A issue conta como resolvida só se os dois grupos passarem. As ferramentas
**nunca veem esses testes**: eles servem apenas para a avaliação. Todas as
execuções usam o mesmo avaliador oficial (`swebench` 2.1.8).

**SWE-bench Lite** é um subconjunto de 300 issues mais autocontidas. **Lite-S**
são as 249 que restam depois do filtro proposto pelo próprio paper, que remove
issues com o patch exato no texto, sem informação suficiente ou com uma solução
enganosa.

---

## 3. Abordagens comparadas

### 3.1 Agentless (pipeline fixo)

O LLM executa cada etapa, mas não decide qual é o próximo passo e não usa
ferramentas.

1. **Localização hierárquica.** O LLM aponta os arquivos suspeitos a partir da
   estrutura de pastas. Em paralelo, há uma busca por embeddings no código. Em
   seguida, o LLM escolhe as classes e funções relevantes a partir de um
   esqueleto do código e, por fim, as linhas a editar. Essa última etapa é
   amostrada várias vezes.
2. **Reparo.** Para cada conjunto de locais, o LLM gera patches no formato
   *search/replace*.
3. **Validação e seleção.** Os patches passam pelos testes de regressão do
   repositório e por scripts de reprodução do bug gerados pelo LLM. Entre os que
   sobram, vence o mais frequente após normalização.

**Configuração usada** (igual para Luna e Haiku):

| Parâmetro | Paper | Nós |
|---|---|---|
| Conjuntos de locais de edição | 4 | **2** |
| Patches por conjunto | 10 | **3** |
| Patches por issue | 40 | **6** |
| Testes de reprodução gerados | 40 | **4** |
| Embeddings | `text-embedding-3-small` (OpenAI) | `bge-small-en-v1.5` (local) |

A redução é uma ablação controlada: a Figura 6 do paper mostra que o ganho com
mais amostras satura rápido. O código dos autores foi usado sem mudança de
método; as adaptações de infraestrutura estão listadas no
[README](../README.md#o-que-mudou-no-código-do-agentless). Na execução do Luna,
a lista de testes que passam no código original foi reaproveitada de uma execução
anterior nas mesmas issues; ela não depende do modelo.

### 3.2 Agente mini-SWE-agent (com GPT-6 Luna)

O [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) 2.4.6, dos
autores do SWE-agent e do SWE-bench, tem uma única ferramenta, o bash. Ele
explora o repositório, roda comandos e edita arquivos em vários turnos, até
enviar um `git diff`. Runner: `scripts/agentic/run_agent.py`.

| Parâmetro | Valor |
|---|---|
| Limite de passos | 50 por issue |
| Limites de gasto | US$ 0,50 por issue e US$ 5 no total |
| Tentativas | uma por issue (o Agentless gera 6 patches e escolhe um) |
| Ambiente | as mesmas imagens Docker do SWE-bench usadas na avaliação |
| Envio | se o limite de passos acabar sem envio, o `git diff` atual é enviado |

### 3.3 Agente Claude Code (com Claude Haiku 5.5)

O Claude Code roda em modo não interativo (`claude -p --bare`, sem hooks,
`CLAUDE.md` nem skills) dentro do contêiner de cada issue, com as ferramentas
`Bash`, `Edit`, `Write`, `Read`, `Glob` e `Grep`. Busca e acesso à web não foram
habilitados como ferramentas. Recebe o texto da issue e o prompt padrão do
SWE-bench. Runner: `scripts/agentic/run_agentic.py`.

| Parâmetro | Valor |
|---|---|
| Limites | US$ 0,50 e 20 minutos por issue; parada global em US$ 6 (nenhum foi atingido) |
| Tentativas | uma por issue |
| Paralelismo | 4 issues ao mesmo tempo |

Um patch (`psf__requests-863`) foi contaminado na extração com arquivos que já
existiam na imagem. Ele foi corrigido com `scripts/agentic/fix_preds.py` antes
da avaliação, mantendo só a edição real do agente. Detalhes em
[RESULTADOS_AGENTICO_HAIKU.md](RESULTADOS_AGENTICO_HAIKU.md).

### 3.4 Modelos

| Modelo | Uso | Raciocínio | Preço (US$ por 1M tokens, entrada/saída) |
|---|---|---|---|
| GPT-6 Luna (OpenAI) | Agentless e mini-SWE-agent | esforço `medium` | 0,10 / 0,50 |
| Claude Haiku 5.5 (Anthropic) | Agentless e Claude Code | esforço `medium` | 0,10 / 0,50 |
| GPT-4o (paper) | Agentless publicado | sem raciocínio | valor reportado pelo paper |

---

## 4. Amostra

```
SWE-bench Lite (300 issues)
   │  filtro do paper → reproduzido, resulta exatamente em 249
   ▼
SWE-bench Lite-S (249 issues)
   │  amostragem aleatória estratificada por repositório, semente 42
   ├──► subset_40 (40 issues)
   └──► subset_15 (15 issues), sorteada separadamente

Lote 1: as 15 issues do subset_15
Lote 2: as 32 do subset_40 que não estão no subset_15
Total: 47 issues distintas (data/subset_47.txt)
```

- **Por que estratificar:** o Django é cerca de 1/3 do benchmark e o sympy cerca
  de 1/4. Uma amostra pequena e puramente aleatória poderia ficar concentrada
  num repositório só.
- **Comparação com o paper nas mesmas issues:** os autores publicaram o resultado
  por issue (`swe-bench/experiments`, `20241028_agentless-1.5_gpt4o`, 96/300).
  Por isso todas as comparações usam a mesma lista de 47 issues. Nela, o paper
  resolve 18 (38,3%), mais que os 32% do Lite inteiro, porque o Lite-S é mais
  fácil.

---

## 5. Métricas

| Métrica | Pergunta que responde | Como é calculada |
|---|---|---|
| **Taxa de resolução (TR)** | Quantas issues cada abordagem resolve? | $TR = IR/47$, com o critério da seção 2 |
| **IC de Wilson (95%)** | Quão incerta é cada taxa? | Intervalo de Wilson (1927) para uma proporção binomial, adequado a amostras pequenas (Brown et al., 2001). Com 47 issues, cerca de ±13 p.p. |
| **Teste exato de McNemar** | A diferença entre duas abordagens é significativa? | Usa só as issues discordantes, $b$ (só A resolve) e $c$ (só B resolve). Sob $H_0$, $b \sim \mathrm{Binomial}(b+c, 1/2)$; $p = \min\{1, 2\sum_{i=0}^{\min(b,c)} \binom{b+c}{i} 2^{-(b+c)}\}$. Significância a 5% |
| **Diferença pareada com bootstrap** | Qual o tamanho plausível da diferença? | $\Delta = (b-c)/n$; IC 95% pelos percentis 2,5% e 97,5% de 10.000 reamostragens pareadas das issues (semente fixa). Indica magnitude; o critério de significância é o McNemar |
| **Oráculo** (só Agentless) | O gargalo está em gerar ou em escolher o patch? | Todos os patches candidatos distintos são avaliados; a issue conta se ao menos um a resolve. É o limite superior de uma seleção perfeita |
| **Localização** (só Agentless) | Em que etapa o pipeline erra? | Fração das issues em que o arquivo do patch oficial foi encontrado em cada etapa |
| **Custo por issue resolvida** | Quanto custa cada acerto? | $C = \frac{T_{in}}{10^6}P_{in} + \frac{T_{out}}{10^6}P_{out}$ com os tokens registrados e o preço de tabela; $C/IR$. No Claude Code, custo informado pelo provedor (inclui cache) |

Implementação: `scripts/compare_all.py` (TR, Wilson, McNemar, bootstrap, custo),
`scripts/summary.py` (localização, seleção, oráculo) e
`scripts/extra_metrics.py` (custo por etapa).

---

## 6. Ameaças à validade

- **Tamanho da amostra.** 47 issues dão intervalos de cerca de ±13 p.p.
  Diferenças menores que isso não são detectáveis, e várias comparações ficam
  sem evidência de diferença. Isso não equivale a mostrar que as abordagens são
  iguais.
- **União de duas amostras.** As 47 issues vêm de duas amostras estratificadas,
  e não de uma só. A proporção por repositório fica próxima da do Lite-S, mas
  não é exata.
- **Uma execução por configuração.** Com temperatura e raciocínio, os resultados
  variam entre execuções. Cada configuração de Luna e Haiku rodou uma vez.
- **Agentes diferentes por modelo.** O mini-SWE-agent roda com o Luna e o Claude
  Code com o Haiku. A comparação agente × Agentless é limpa dentro de cada
  modelo, mas comparar os dois agentes entre si mistura modelo e ferramenta.
- **Configuração diferente do paper.** Contra o paper, mudam ao mesmo tempo o
  modelo e a configuração (6 contra 40 patches). Não dá para separar os dois
  efeitos.
- **Vazamento de dados.** As issues e os patches do SWE-bench são públicos desde
  2023 e podem estar no treino dos modelos. Vale para todas as abordagens e para
  o paper.
- **Acesso à internet dos agentes.** Os contêineres dos agentes tinham rede, então
  em tese um agente poderia buscar a correção publicada. A varredura dos comandos
  não encontrou acesso à rede: 0 de 798 comandos no mini-SWE-agent com Luna e 0
  comandos suspeitos nas 47 trajetórias do Claude Code com Haiku. É uma busca
  por texto, não uma análise qualitativa completa.
- **Issue não resolvível no ambiente.** Em `psf__requests-863`, o próprio patch
  oficial falha, por um teste que depende de rede. A issue conta como não
  resolvida em todas as nossas execuções; o paper, avaliado em 2024, a resolveu.
- **Ambiente Docker corrigido.** Três imagens precisaram de correções de versão
  de pacotes (Apêndice A), e quatro issues da execução do Haiku usaram as
  imagens oficiais do Docker Hub. Nenhuma correção altera os testes ou o código
  avaliado.
- **Oráculo do Haiku fora do repositório.** O oráculo do Agentless com Haiku
  foi avaliado na máquina daquela execução; o repositório traz o resultado
  registrado em [RESULTADOS_HAIKU.md](RESULTADOS_HAIKU.md), mas não os relatórios
  do oráculo. O oráculo do Luna pode ser refeito com `scripts/oracle_run.sh`.
- **Preços.** O custo usa preços de tabela, que mudam com o tempo. As tentativas
  repetidas por falha de API não ficam registradas, então o custo real pode ser
  um pouco maior.

---

## 7. Execução

- **Pipeline** (`scripts/pipeline.sh`): roda as etapas do Agentless na ordem do
  README oficial. Cada etapa pula o que já foi feito, então qualquer interrupção
  é retomável. O controle de ritmo respeita os limites de requisições e tokens
  por minuto, e erros 429/500/503 são tentados de novo com espera crescente.
- **Máquinas:** o Luna rodou num notebook com 12 GB de RAM, com um contêiner de
  teste por vez; o Haiku rodou numa máquina com 24 GB, com 4 a 6 contêineres em
  paralelo. Isso muda o tempo, não o resultado.
- **Docker:** cerca de 50 imagens (base, ambientes por versão de projeto e uma
  por issue), cerca de 110 GB em disco.

---

## Apêndice A. Correções no ambiente de avaliação (Docker)

O avaliador de 2024 instala pacotes conda e pip na versão do dia em que constrói
as imagens. Pacotes lançados depois quebraram três situações. Nenhuma correção
altera testes ou código avaliado; elas só devolvem o ambiente ao comportamento
da época.

**A.1 Ambiente do scikit-learn** (`sweb.env.x86_64.3a59860bcd0dab8bbfb2ff`)

1. O script de ativação do pacote conda `qt-main` lê a variável
   `QT_XCB_GL_INTEGRATION` sem defini-la. Como os scripts do avaliador rodam com
   `set -u`, o `conda activate testbed` aborta.
2. O pip 25.3 ou mais novo removeu a opção `--no-use-pep517`, que o avaliador usa
   para instalar o repositório.

Correção, aplicada só a essa imagem e marcada com o nome que o avaliador espera:
a imagem foi construída a partir do contexto de build do próprio avaliador, sem o
`-u` no `setup_env.sh`; uma camada extra dá valor padrão vazio a
`QT_XCB_GL_INTEGRATION`; outra fixa `pip==24.0` no ambiente `testbed`.

**A.2 Camada de compatibilidade na imagem base**

Sobre `sweb.base.x86_64:latest` (a original foi guardada como
`sweb.base.x86_64:original-2024`): `ENV QT_XCB_GL_INTEGRATION=none` e
`conda config --add pinned_packages "pip<25.3"`. O avaliador identifica a imagem
base só pelo nome, então só as imagens construídas depois herdam a camada.

**A.3 Ambiente do pylint** (`sweb.env.x86_64.0c609b65ef40b42410cb20`)

O pip 25 ou mais novo não cai mais para o `setup.py develop` quando o backend de
build não tem `build_editable` (PEP 660), e o pylint 2.15 fixa
`setuptools~=62.6`. Por isso, o `pip install -e .` falhava na imagem da issue
`pylint-dev__pylint-7993`. Correção: uma camada extra fixando `pip==24.0`.

---

## Glossário

| Termo | Significado |
|---|---|
| Issue | Relato de bug num repositório do GitHub |
| Patch / diff | Alteração no código que corrige o bug |
| Patch oficial (*gold patch*) | Patch escrito pelos desenvolvedores do projeto |
| Harness | O avaliador oficial do SWE-bench, que roda os testes no Docker |
| Teste de regressão | Teste existente que não pode quebrar |
| Teste de reprodução | Script gerado pelo LLM que mostra o bug |
| Embedding | Vetor que representa o significado de um texto, usado na busca por similaridade |
| Oráculo | Melhor resultado possível escolhendo sempre o candidato certo |
| Trajetória | Registro de todos os passos (pensamentos e comandos) de um agente numa issue |
| IC 95% | Intervalo de confiança de 95% |

## Referências

- Xia, C. S.; Deng, Y.; Dunn, S.; Zhang, L. *Agentless: Demystifying LLM-based Software Engineering Agents.* arXiv:2407.01489, 2024.
- Jimenez, C. E. et al. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR, 2024.
- Wilson, E. B. *Probable inference, the law of succession, and statistical inference.* JASA 22(158), 1927.
- Brown, L. D.; Cai, T. T.; DasGupta, A. *Interval estimation for a binomial proportion.* Statistical Science 16(2), 2001.
- McNemar, Q. *Note on the sampling error of the difference between correlated proportions or percentages.* Psychometrika 12(2), 1947.
