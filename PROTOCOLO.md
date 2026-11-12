# Protocolo de medição (versão AR / ARCore)

Estrutura do repositório:

- `docs/` — página "Custo do rastreamento AR" (cena 3D + rastreamento de posição do ARCore via WebXR). Publicada pelo GitHub Pages.
- `tools/coletor_adb.py` — coleta CPU por núcleo, frequência, temperatura e bateria do celular via adb.
- `dados/` — saída bruta de todas as medições (CSV da página e pasta do coletor).
- `notes/` — fichas da disciplina e o formulário do projeto (só local, fora do git).

A versão anterior (rastreador de pose MediaPipe) continua na branch `main`.

## Preparação (uma vez)

1. No PC: instalar o [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) e colocar o `adb` no PATH. Python 3 sem bibliotecas extras.
2. No celular: ativar as Opções do desenvolvedor e a Depuração USB. Deixar o "Google Play Services for AR" instalado e atualizado.
3. adb por Wi-Fi (para o cabo não carregar o celular durante a medição; o Note 9 tem Android 10, sem o menu "Depuração por Wi-Fi"):
   ```
   adb tcpip 5555          # com o cabo conectado
   adb connect <ip-do-celular>:5555
   ```
   Depois de conectar, tirar o cabo. Conferir com `adb devices`. Repetir após reiniciar o celular.
4. Abrir a página no Chrome do celular e tocar em **Testar recursos do AR**. Anotar a tabela que aparece (recursos concedidos, ritmo dos quadros, resolução): ela diz quais condições são possíveis neste aparelho.

## O percurso

O ARCore precisa de movimento para rastrear, então **toda execução, inclusive "sem AR", é feita andando o mesmo percurso**:

- Duas marcas de fita no chão, na mesma sala, com a mesma iluminação. **[DEFINIR distância entre as marcas]**
- Ida e volta entre as marcas no ritmo de um metrônomo. **[DEFINIR batidas por minuto]**
- Celular seguro com as duas mãos, na altura do peito, câmera traseira apontada para a frente.
- A cena 3D fica "presa à câmera" (padrão): o que é desenhado não depende do caminho, só o trabalho do ARCore depende.

## Antes de cada execução

- Modo avião com só o Wi-Fi ligado, brilho fixo, brilho automático desligado, só uma aba aberta.
- **Recarregar a página.** Toda execução começa com a página recém-aberta: é parte do método (nada sobra da execução anterior) e evita o erro `Cannot read properties of null (reading 'precision')` que o Note 9 dá na segunda execução sem recarregar.
- Temperatura da bateria de volta ao valor de repouso (o coletor mostra em `bateria, temperature_c`).
- Na página, conferir o nome do integrante, o modo, os recursos marcados (a linha "Condição" mostra a combinação) e o número da repetição.

## Uma execução

1. No PC: `python tools/coletor_adb.py --rotulo <condição>_r<n> --duracao 130`
2. Logo em seguida, no celular: **Iniciar execução** e começar a andar o percurso. No modo AR o Chrome pede para entrar no AR; a página mede por 120 s e volta sozinha.
3. Conferir os avisos ao fim (carregando, rastreamento completo em menos de 90% dos quadros, execução interrompida). Execução com aviso fica salva, mas deve ser repetida. A taxa de rastreamento importa: quando o ARCore perde a posição, ele roda outro caminho de código (relocalização) e o custo medido muda.
4. Ordem das condições: alternar as condições a cada execução até 5 repetições de cada.

Ao fim do dia, **Baixar todas (CSV)** e copiar `resumo_*.csv` e `quadros_*.csv` para `dados/`.

## Arquivos gerados

`resumo_*.csv` (página): uma linha por execução, com a configuração completa, os recursos que o ARCore de fato concedeu (`features_enabled`), a resolução de desenho (`render_w`, `render_h`) e `frame_mean_ms`, `frame_p50_ms`, `frame_p95_ms`, `frame_p99_ms`, `feature_mean_ms`, `tracking_full_ratio`.

`quadros_*.csv` (página): uma linha por quadro. `frame_ms` é o intervalo desde o quadro anterior, `work_ms` o tempo gasto no quadro pelo JavaScript, `feature_ms` o tempo lendo os recursos extras do ARCore, `tracking` o estado do rastreamento (2 = completo, 1 = só rotação, 0 = perdido), `hits` quantas superfícies o hit-test encontrou, `warmup=1` nos quadros descartados do aquecimento. `epoch_ms` serve para alinhar com o coletor.

`dados/adb/<rótulo>_<data>/` (coletor): `amostras.csv` no formato `epoch_ms, metrica, chave, valor` (`cpu_uso_pct`, `cpu_freq_mhz`, `temp_c`, `bateria_corrente_ua`, `bateria`), `bruto.txt` com a saída crua do aparelho e `meta.txt` com os relógios do PC e do celular para corrigir o desvio entre eles.
