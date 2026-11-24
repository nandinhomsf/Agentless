# Métricas novas do estudo

Duas métricas adicionadas ao projeto para comparar as abordagens (Agentless, agêntica e modelos diferentes) além da taxa de resolução.

| | |
|---|---|
| **Código** | [`pesquisa/scripts/extra_metrics.py`](../scripts/extra_metrics.py) |
| **Saída** | `pesquisa/results/summary/METRICAS_EXTRA.md` (e seção extra no fim do `RESUMO.md`) |
| **Uso** | `.venv/bin/python pesquisa/scripts/extra_metrics.py` |

O `pesquisa/scripts/summary.py` chama o mesmo código no fim da execução. Se a parte nova falhar, o `RESUMO.md` original já foi escrito e continua igual.

---

## 1. Custo por issue resolvida (com tokens por etapa)

**Pergunta:** quanto custa, em dólares, cada issue que a abordagem consegue resolver? E em que etapa do pipeline os tokens são gastos?

### Como é calculada

1. Lê os tokens de entrada (`prompt_tokens`) e de saída (`completion_tokens`) que o Agentless já grava nos `.jsonl` (campo `usage`).
2. Soma por etapa e por issue:

   | Etapa | Arquivo | Campo lido |
   |---|---|---|
   | Localização: arquivos (LLM) | `file_level/loc_outputs.jsonl` | `file_traj` |
   | Localização: arquivos irrelevantes | `file_level_irrelevant/loc_outputs.jsonl` | `file_traj` |
   | Localização: elementos relacionados | `related_elements/loc_outputs.jsonl` | `related_loc_traj` |
   | Localização: linhas de edição | `edit_location_samples/loc_outputs.jsonl` | `edit_loc_traj` |
   | Geração de patches | `repair_sample_*/output.jsonl` | `traj` |
   | Testes de reprodução | `reproduction_test_samples/output.jsonl` | `traj` |
   | Seleção de testes de regressão | `select_regression/output.jsonl` | `traj` |

   > Cada arquivo carrega as trajetórias das etapas anteriores. Por isso só o **campo próprio** de cada etapa é lido; somar tudo contaria os mesmos tokens mais de uma vez.

3. Calcula o custo:

   ```text
   custo (US$)               = entrada/1e6 × preço_entrada + saída/1e6 × preço_saída
   custo por issue           = custo total / nº de issues
   custo por issue resolvida = custo total / nº de issues resolvidas
   ```

4. Os preços ficam na tabela `PRECOS` do script (US$ por 1M de tokens). Ajuste ao rodar com outro modelo, ou use `--preco ENTRADA SAIDA`.

### Exemplo de uso com outro modelo

```bash
.venv/bin/python pesquisa/scripts/extra_metrics.py \
    --modelo claude-haiku-5-5 --nome "Haiku 5.5" \
    --runs pesquisa/results/haiku_reduced:pesquisa/data/subset_15.txt \
           pesquisa/results/haiku_reduced_ext:pesquisa/data/subset_ext.txt
```

### Limites e cuidados

- Mede apenas chamadas ao LLM. Embeddings locais e Docker não entram (custo próximo de zero).
- Tentativas repetidas por falha de API não deixam rastro nos `.jsonl`, então o custo real pode ser um pouco maior.
- Os tokens são os reportados pela API de cada provedor.
- Os preços padrão vêm da Artificial Analysis. Confirme no console do provedor antes de citar.
- A referência do paper (US$0,70 por issue, GPT-4o, 4×10 patches) é um valor reportado e não foi recalculado.

### Por que importa

O estudo compara abordagem agêntica e Agentless. Custo por resultado obtido é a dimensão central dessa comparação.

---

## 2. Diferença pareada com intervalo de confiança

**Pergunta:** qual a diferença de taxa de resolução entre duas abordagens nas **mesmas issues**, e qual a incerteza dessa diferença?

### Como é calculada

1. Para cada issue, marca resolvida (1) ou não (0) em cada abordagem.
2. **Diferença** `= (resolvidas_A − resolvidas_B) / n`, em pontos percentuais (p.p.).
3. **IC 95%** por *bootstrap pareado*: sorteia `n` issues com reposição (10.000 vezes, semente fixa), recalcula a diferença a cada vez e usa os percentis 2,5% e 97,5%.
4. Mostra a tabela de discordâncias (só A, só B, ambas, nenhuma) e o p-valor exato de McNemar, que já existia.
5. Conclui em palavras, usando uma margem de equivalência `M` (padrão 10 p.p., parâmetro `--margem`):

   | Situação do IC | Conclusão |
   |---|---|
   | Todo dentro de `[−M, +M]` | equivalente dentro da margem |
   | Todo acima de 0 ou todo abaixo de 0 | diferença significativa |
   | Qualquer outro caso | inconclusivo (amostra pequena) |

### Limites e cuidados

- A margem de 10 p.p. é uma **escolha do estudo**, não uma regra. Justifique no texto.
- Com 47 issues o IC é largo. Um `p = 1,00` no McNemar **não prova equivalência**: indica apenas que não há evidência de diferença. O IC da diferença mostra o que ainda é plausível.

### Por que importa

Corrige a leitura "equivalência estatística" dos slides, que confunde *não rejeitar H₀* com *ser equivalente*.

---

## Resultado atual (Gemini 3.1 Flash-Lite, 47 issues)

| Métrica | Valor |
|---|---|
| Custo total (LLM) | US$ 0,86 |
| Custo por issue | US$ 0,018 |
| Custo por issue resolvida | US$ 0,051 (17 resolvidas) |
| Tokens por issue | ~39,4 mil de entrada, ~5,6 mil de saída |
| Diferença vs. paper (mesmas 47 issues) | −2,1 p.p., IC 95% [−14,9, +10,6] |
| Discordâncias | só nós 5 · só paper 6 · ambos 12 · nenhum 24 |
| Conclusão | inconclusivo |

Custo por etapa:

| Etapa | Tokens entrada | Tokens saída | Custo (US$) |
|---|---:|---:|---:|
| Localização: arquivos (LLM) | 241.853 | 1.447 | 0,063 |
| Localização: arquivos irrelevantes | 244.438 | 7.359 | 0,072 |
| Localização: elementos relacionados | 272.389 | 1.801 | 0,071 |
| Localização: linhas de edição | 452.262 | 3.343 | 0,118 |
| Geração de patches | 390.567 | 132.390 | 0,296 |
| Testes de reprodução | 172.548 | 116.619 | 0,218 |
| Seleção de testes de regressão | 79.571 | 1.748 | 0,023 |
| **Total** | **1.853.628** | **264.707** | **0,860** |

Preços usados: US$ 0,25 de entrada e US$ 1,50 de saída por 1M de tokens (Artificial Analysis).
