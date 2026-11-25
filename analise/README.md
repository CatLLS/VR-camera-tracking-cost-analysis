# Análise — gráficos e tabelas

Tudo aqui é gerado por `gerar_graficos.py` a partir dos dados medidos em `dados/`
(Galaxy Note 9, medições da Cat em 21/11 e 24/11/2026). O script não altera nada em `dados/`.

Para gerar de novo (por exemplo, depois que entrarem as execuções de 15 min):

```
pip install matplotlib numpy
python analise/gerar_graficos.py
```

## Gráficos por frente

| Frente | Arquivo | O que mostra |
|---|---|---|
| 1 — p95 do tempo de quadro | `F1_1_p95_por_threads.png` | p95 de cada execução, sem AR e com AR, para 0/2/4/6 threads |
| | `F1_2_custo_ar_p95.png` | **Custo do ARCore** = p95(AR) − p95(sem AR), por nº de threads (a pergunta do projeto) |
| | `F1_3_distribuicao_tempo_quadro.png` | Distribuição (CDF) de todos os quadros de cada condição |
| | `F1_4_fps_medio.png` | fps médio |
| 2 — CPU por núcleo | `F2_1_cpu_por_nucleo.png` | Uso médio de cada um dos 8 núcleos em cada condição |
| | `F2_2_cpu_silver_gold.png` | Núcleos Silver (0-3) e Gold (4-7) separados |
| | `F2_3_custo_ar_cpu.png` | CPU(AR) − CPU(sem AR), em pontos percentuais |
| | `F2_4_vazao_threads_do_jogo.png` | Quanto trabalho cada thread extra do jogo conseguiu fazer |
| | `F2_5_frequencia_cpu.png` | Frequência média dos núcleos |
| 3 — degradação em 15 min | `F3_*.png` | **Ainda não gerado**: depende das 4 execuções de 15 min |
| 4 — bateria | `F4_1_corrente_bateria.png` | Corrente média de descarga (mA) |
| | `F4_2_custo_ar_bateria.png` | Corrente(AR) − corrente(sem AR) |
| | `F4_3_potencia.png` | Potência média = corrente × tensão da bateria (mW) |

Nos gráficos, cada ponto claro é uma execução e o ponto grande com barra é a média ± desvio padrão
das 5 repetições. Nos gráficos de custo, a diferença é calculada **dentro de cada repetição** (o
par sem AR / com AR foi medido um logo depois do outro) e depois tirada a média.

## Tabelas (`tabelas/`)

- `execucoes.csv`: uma linha por execução usada (40), com os números da página e do coletor.
- `resumo_por_condicao.csv`: média, desvio padrão e n de cada métrica, para as 8 condições.
- `custo_do_ar.csv`: média, desvio padrão e n do custo do AR em cada métrica, por nº de threads.

## Como as execuções foram escolhidas

- Só entram execuções de 120 s não interrompidas, da versão 2.1.1 da página. As versões anteriores
  estão em `dados/descartado/` (o motivo está em `dados/descartado/LEIAME.txt`).
- Quando uma condição foi medida mais de uma vez na mesma repetição, vale a **última** (o guia
  manda refazer a execução com aviso no fim da rodada). Isso aconteceu em `sem-ar_t2_r2` (2 vezes).
- `correcoes.csv` corrige rótulos digitados errado, sem mexer nos arquivos originais:
  - a segunda `ar_t6` marcada como repetição 3 é a da repetição 4 (pela ordem da rodada 4 ela vem
    logo antes de `sem-ar_t6_r4`, e a rodada 4 não tinha outra `ar_t6`);
  - a pasta do coletor `ar_t0_2026-11-21T13-01-53` é a `ar_t0_r1` (faltou o `_r1`).
- Os quadros dos primeiros 5 s (aquecimento) ficam de fora, como na página.

## Como os dados do coletor (CPU, frequência, bateria) foram recortados

O coletor roda no PC e a página no celular. O guia manda iniciar o coletor e tocar em
*Iniciar execução* até 10 s depois.

- **21/11:** o horário gravado pela página bate com o do coletor, então usa-se exatamente a janela
  medida pela página.
- **24/11:** o horário gravado pela página ficou atrasado (de ~54 min a ~2 h). A página usa
  `performance.timeOrigin`, e no Android esse relógio para enquanto o celular dorme com a tela
  apagada (no resfriamento entre execuções). Os tempos *dentro* de cada execução estão certos;
  só a hora do dia está errada. Por isso, nesses dias usa-se uma janela fixa de **15 s a 120 s
  depois do início do coletor** (105 s). Ela fica dentro da medição sempre que a página foi
  iniciada até 10 s depois do coletor, como manda o guia.

O relógio do PC e o do celular (pelo adb) diferem em menos de 2 s em todas as coletas.

## Avisos para a análise

- `ar_t0_r1`: o coletor começou ~23 s atrasado, então CPU e bateria dessa execução cobrem só
  80% da janela. Os dados de quadros estão completos.
- `sem-ar_t6_r4`: o coletor cobre 90% da janela.
- Par `t6_r1` (21/11): `sem-ar_t6_r1` começou com a bateria a 34,7 °C (resfriamento curto) e
  `ar_t6_r1` foi refeita 1 h depois, com a bateria a 29,3 °C. As duas estão nos dados.
- Nenhuma execução usada estava carregando ou com a página escondida, e todas as execuções com AR
  tiveram rastreamento completo em ≥ 98,5% dos quadros.
- No modo sem AR a página limita a cena a 30 fps (o fps que o AR consegue), para os tempos de
  quadro serem comparáveis. Por isso o p95 sem AR fica sempre em ~33,5 ms.
- `descarga_ma` vem de `current_now` (no Samsung, em mA; o sinal foi invertido para descarga
  ficar positiva).
