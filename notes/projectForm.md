Pergunta do grupo, a partir da pergunta candidata 1 (ajuste o que quiser)

> Itens marcados com **[PREENCHER]** dependem de informação que só o grupo tem (aparelho, responsáveis) ou de medição real. Nenhum número de medição foi escrito aqui: todos os dados vêm do celular do grupo.

Pergunta, em uma linha, com "quanto": Quanto custa rodar um rastreador de pose pela câmera junto com uma cena 3D no mesmo celular, quando mudo a resolução da câmera do rastreador (desligado, 640×480, 1920×1080), medido em p95 do tempo de quadro (ms)?

Pilar do OSTEP (pode marcar mais de um): Virtualização de CPU

Conceito mais próximo (o que do sistema operacional está sendo cobrado): escalonamento e compartilhamento do processador entre duas cargas que disputam os mesmos núcleos (a renderização da cena e a inferência do rastreador), e a redução de frequência por aquecimento (DVFS / throttling térmico).

O que varia (A variável: a única coisa que vocês mudam de propósito entre uma medição e outra. Nome e valores.): carga do rastreador na câmera — desligado (câmera fechada), câmera 640×480 com rastreador, câmera 1920×1080 com rastreador.

O que mede (métrica, O número que vocês leem ao fim de cada medição, com a unidade.
): p95 do tempo de quadro da cena 3D, em milissegundos (ms).

-----------------------
Cada integrante é dono de uma frente de investigação: uma variação da pergunta do grupo (uma variável a mais, uma condição a mais, um dispositivo a mais). Cada integrante é dono de uma medida: uma métrica, ou a mesma métrica dos colegas numa condição que só você mede (outro dispositivo, outro valor fixo, outra carga). Dois integrantes não podem entregar a mesma métrica na mesma condição.

---
Frente 1: Tempo de quadro — Responsável: **[PREENCHER]**

O que a frente 1 mostra: quanto o rastreador piora a fluidez da cena, olhando os piores quadros (que são os que o usuário percebe como travada e que pioram o enjoo em VR).

Nome da métrica (Só o nome do número que você vai ler, sem a condição.): p95 do tempo de quadro

Unidade (Como o número sai: ms, MB, %, por segundo): ms

O que o número representa (Explique o número para um colega de outra turma. Quanto maior, melhor ou pior?): é o intervalo entre um quadro e o seguinte abaixo do qual ficam 95% dos quadros; só 5% dos quadros demoram mais que ele. Quanto maior, pior: a imagem engasga mais. Numa tela de 60 Hz o ideal é ficar perto de 16,7 ms.

Como se mede( O comando ou a ferramenta e o que aparece como resultado. Confira se funciona no dispositivo de vocês.): página do grupo (pasta docs/, publicada no GitHub Pages). Ela registra o instante de cada quadro com requestAnimationFrame, descarta os 5 s iniciais de aquecimento e mostra média, p50, p95 e p99 ao fim; "Baixar CSV" gera resumo_*.csv (uma linha por execução, coluna frame_p95_ms) e quadros_*.csv (uma linha por quadro, coluna frame_ms). Conferência no Perfetto (opcional): trace com os quadros do Chrome, para comparar com o número da página. **[CONFERIR no aparelho]**

Em que condição (A situação em que você mede: dispositivo, carga e o que fica fixo. Se vale para todas as condições do grupo, escreva "todas".): todas.

O que pode distorcer (O que mudaria o número sem ter relação com a variável, e o que vocês fazem para evitar.): (1) teto da taxa de atualização da tela — o tempo de quadro nunca fica abaixo de 1000/Hz; fixamos a taxa da tela nas configurações e registramos qual é. (2) Aquecimento acumulado de execuções anteriores — esperamos a temperatura da bateria voltar ao valor de repouso antes de cada execução e alternamos a ordem das condições. (3) Notificações e apps em segundo plano — modo avião com só o Wi-Fi ligado, só uma aba aberta. (4) Rastreador sem pessoa na frente da câmera muda o trabalho do modelo — a página registra em quantos quadros a pose foi encontrada; a mesma pessoa fica parada no mesmo lugar em todas as execuções.

---
Frente 2: Uso de CPU por núcleo — Responsável: **[PREENCHER]**

O que a frente 2 mostra: como o sistema distribui a carga extra do rastreador entre os núcleos (se ocupa núcleos livres ou disputa o mesmo núcleo da renderização), que é o mecanismo por trás do custo da frente 1.

Nome da métrica (Só o nome do número que você vai ler, sem a condição.): uso de CPU por núcleo (média na execução)

Unidade (Como o número sai: ms, MB, %, por segundo): % do tempo ocupado

O que o número representa (Explique o número para um colega de outra turma. Quanto maior, melhor ou pior?): fração do tempo em que cada núcleo esteve trabalhando em vez de ocioso. Maior significa núcleo mais carregado; perto de 100% em algum núcleo indica que ele virou gargalo.

Como se mede( O comando ou a ferramenta e o que aparece como resultado. Confira se funciona no dispositivo de vocês.): `python tools/coletor_adb.py --rotulo <condição>_r<n> --duracao 130` rodando no PC enquanto a página mede. Ele lê /proc/stat do celular via adb a cada 1 s e grava dados/adb/<rótulo>_<data>/amostras.csv (linhas `cpu_uso_pct`, uma por núcleo por segundo) e bruto.txt com a saída crua. **[CONFERIR no aparelho]**

Em que condição (A situação em que você mede: dispositivo, carga e o que fica fixo. Se vale para todas as condições do grupo, escreva "todas".): todas.

O que pode distorcer (O que mudaria o número sem ter relação com a variável, e o que vocês fazem para evitar.): (1) o próprio coletor usa CPU no celular — é o mesmo em todas as condições (1 amostra/s, inclusive na "desligado"), então entra igual na comparação. (2) Núcleos que desligam e ligam sozinhos — o coletor registra quantos estão online a cada amostra. (3) Processos em segundo plano — mesmas precauções da frente 1.

---
Frente 3: Degradação ao longo de 15 minutos — Responsável: **[PREENCHER]**

O que a frente 3 mostra: se o custo cresce com o tempo de uso por causa do aquecimento, ou seja, se o celular reduz a frequência da CPU (throttling) e a cena fica mais lenta numa sessão de jogo normal.

Nome da métrica (Só o nome do número que você vai ler, sem a condição.): aumento do p95 do tempo de quadro entre o 1º e o 15º minuto (acompanhado da temperatura e da frequência da CPU)

Unidade (Como o número sai: ms, MB, %, por segundo): ms (temperatura em °C e frequência em MHz como apoio)

O que o número representa (Explique o número para um colega de outra turma. Quanto maior, melhor ou pior?): quanto o pior caso da fluidez piorou depois de 15 minutos seguidos de uso. Quanto maior, pior: o celular perde desempenho ao esquentar.

Como se mede( O comando ou a ferramenta e o que aparece como resultado. Confira se funciona no dispositivo de vocês.): página com duração de 900 s + coletor `python tools/coletor_adb.py --rotulo 15min_<condição> --duracao 930`. O p95 é calculado por minuto a partir de quadros_*.csv (coluna t_ms); temperatura (`temp_c`) e frequência (`cpu_freq_mhz`) vêm de amostras.csv. **[CONFERIR no aparelho quais sensores de temperatura são legíveis]**

Em que condição (A situação em que você mede: dispositivo, carga e o que fica fixo. Se vale para todas as condições do grupo, escreva "todas".): mesmo aparelho e carga do grupo, mas com execuções longas de 15 min (só esta frente usa essa duração). Repetições por condição: **[DEFINIR — 5 execuções de 15 min por condição dão ~4 h de medição]**.

O que pode distorcer (O que mudaria o número sem ter relação com a variável, e o que vocês fazem para evitar.): (1) temperatura do ambiente — medir no mesmo local, anotar a temperatura do ambiente. (2) Aparelho começar já quente — começar só com a bateria na temperatura de repouso. (3) Capa do celular e superfície onde ele está apoiado mudam a dissipação — sem capa, sempre no mesmo suporte.

---
Frente 4: Consumo de bateria — Responsável: **[PREENCHER]**

O que a frente 4 mostra: quanto de bateria o rastreador custa, que é o que limita uma sessão de VR com o celular dentro do Cardboard.

Nome da métrica (Só o nome do número que você vai ler, sem a condição.): corrente média de descarga

Unidade (Como o número sai: ms, MB, %, por segundo): mA

O que o número representa (Explique o número para um colega de outra turma. Quanto maior, melhor ou pior?): quanto de carga por segundo sai da bateria durante a execução. Quanto maior, pior: a bateria acaba antes.

Como se mede( O comando ou a ferramenta e o que aparece como resultado. Confira se funciona no dispositivo de vocês.): o mesmo coletor (`tools/coletor_adb.py`) lê a cada 1 s a corrente da bateria (`/sys/class/power_supply/battery/current_now`, linha `bateria_corrente_ua`) e o contador de carga do `dumpsys battery` (linha `bateria, charge_counter_uah`). Se a corrente não for legível no aparelho, usar a queda do contador de carga ao longo da execução (mAh). **[CONFERIR no aparelho]**

Em que condição (A situação em que você mede: dispositivo, carga e o que fica fixo. Se vale para todas as condições do grupo, escreva "todas".): todas, com o celular desconectado do cabo (adb por Wi-Fi), para que o carregador não alimente o aparelho durante a medição.

O que pode distorcer (O que mudaria o número sem ter relação com a variável, e o que vocês fazem para evitar.): (1) cabo USB carregando o aparelho — usar adb por Wi-Fi; a página avisa se detectar que o aparelho está carregando. (2) Nível da bateria muito baixo ou muito alto muda a tensão — começar sempre na mesma faixa de nível **[DEFINIR faixa]**. (3) Brilho da tela — fixo e com brilho automático desligado.

----------------
Método

Dispositivo usado pelo grupo (A máquina real da medição: modelo, sistema operacional, memória e processador.): Samsung Galaxy Note 9 — **[PREENCHER: número do modelo (SM-N960…), versão do Android/One UI, RAM, processador (SoC), resolução da tela configurada]**

O que fica igual (Tudo o que não muda entre as condições: a máquina, a entrada, o que fica aberto, a duração. O que estiver aqui não pode mudar entre as condições nem entre as frentes.): o mesmo celular; a mesma versão da página; a mesma cena 3D (3000 objetos, visão estéreo de Cardboard, escala de pixels 1); o mesmo modelo de pose (lite) processado na GPU, câmera traseira pedida a 30 fps; Chrome com uma única aba; modo avião com só o Wi-Fi ligado (adb por Wi-Fi), sem cabo; brilho fixo e brilho automático desligado; taxa de atualização da tela fixa; celular sem capa, no mesmo suporte, apontado para a mesma pessoa parada no mesmo lugar; duração de 120 s com 5 s de aquecimento descartados; antes de cada execução, esperar a temperatura da bateria voltar ao valor de repouso.

Condições a comparar(2 ou mais)
Cada linha é uma situação completa que vocês vão comparar: um nome curto e o valor da variável nela.
    Condição 1 — "desligado": cena 3D sem câmera e sem rastreador.
    Condição 2 — "480p": cena 3D + câmera em 640×480 + rastreador de pose.
    Condição 3 — "1080p": cena 3D + câmera em 1920×1080 + rastreador de pose.

    Ordem: as condições se alternam (desligado, 480p, 1080p, desligado, 480p, 1080p, …) para que o aquecimento não favoreça nenhuma.

Carga (O trabalho que roda durante a medição, igual em todas as condições: o programa, a entrada, por quanto tempo.): a página "Custo do rastreador" (docs/ no repositório), que desenha uma cena 3D sintética em Three.js — 3000 objetos girando, renderizados duas vezes por quadro (um para cada olho, como no Cardboard) — por 120 s; o conteúdo de cada quadro depende só do relógio, então é igual em toda execução. Nas condições com rastreador, a mesma página abre a câmera e roda o MediaPipe Pose Landmarker em cada quadro novo da câmera.

Repetições por condição (Quantas vezes cada condição roda. Só o número.): 5

Hipótese (O que vocês esperam antes de medir, com direção: esperamos que ... suba (ou caia) quando ...): esperamos que o p95 do tempo de quadro suba quando o rastreador é ligado, e suba mais com a câmera em 1080p do que em 480p; e que, numa sessão de 15 min com o rastreador, o p95 continue subindo enquanto a frequência da CPU cai pelo aquecimento.

Como vão mostrar o custo (O gráfico que responde à pergunta: o que fica no eixo horizontal, o que fica no vertical, uma série por frente.): eixo horizontal: condição (desligado, 480p, 1080p); eixo vertical: aumento em relação a "desligado", em %, da métrica de cada frente (p95 do tempo de quadro, uso de CPU, corrente da bateria, aumento do p95 em 15 min); uma série por frente, cada ponto é a média das 5 repetições com barra do menor ao maior valor. Gráfico de apoio da frente 3: p95 e temperatura por minuto (eixo horizontal de 0 a 15 min).


-----------------------
Primeira medição (individual por integrante)
Até a próxima aula: rodar a métrica no contexto do grupo, com duas condições e três repetições, comando e saída bruta em dados/. Se não der para coletar, registrar o que travou e a métrica substituta.

Onde mediram:
O dispositivo e o cenário desta medição.
dispositivo próprio  ← (planejado: o celular do grupo)
máquina do laboratório
Codespaces
cenário próprio  ← (planejado: a página do grupo)
um dos exemplos do repositório

Medições:
Cada linha é uma condição e cada coluna é uma métrica. As duas vêm do M2 e do M1, e vocês podem editar, tirar e acrescentar. Na célula vai o que o comando devolveu; se não deu para medir, escrevam o que houve.

| Condição | Repetição | p95 do tempo de quadro (ms) | Uso de CPU médio (%) | Corrente média (mA) |
|---|---|---|---|---|
| desligado | 1 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |
| desligado | 2 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |
| desligado | 3 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |
| 1080p | 1 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |
| 1080p | 2 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |
| 1080p | 3 | **[MEDIR]** | **[MEDIR]** | **[MEDIR]** |

Saída e observações:
Colem o comando usado e a saída dele, ou contem o que travou.
**[PREENCHER depois de medir]**

O que surpreendeu:
O que saiu diferente do esperado, ou o que deu trabalho para coletar.
**[PREENCHER depois de medir]**

O que muda no método:
O que vocês trocam depois de ver o número: métrica, condição, repetições, instrumento.
**[PREENCHER depois de medir]**
