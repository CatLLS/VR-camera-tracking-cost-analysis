# Protocolo de medição

Estrutura do repositório:

- `docs/` — página "Custo do rastreador" (cena 3D + rastreador). Publicada pelo GitHub Pages.
- `tools/coletor_adb.py` — coleta CPU por núcleo, frequência, temperatura e bateria do celular via adb.
- `dados/` — saída bruta de todas as medições (CSV da página e pasta do coletor).
- `notes/` — fichas da disciplina e o formulário do projeto.

## Preparação (uma vez)

1. No PC: instalar o [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) e colocar o `adb` no PATH. Python 3 sem bibliotecas extras.
2. No celular: ativar as Opções do desenvolvedor e a Depuração USB.
3. adb por Wi-Fi (para o cabo não carregar o celular durante a medição):
   ```
   adb tcpip 5555          # com o cabo conectado
   adb connect <ip-do-celular>:5555
   ```
   Depois de conectar, tirar o cabo. Conferir com `adb devices`.
4. Abrir a página no Chrome do celular (endereço do GitHub Pages) e permitir a câmera.

## Antes de cada execução

- Modo avião com só o Wi-Fi ligado, brilho fixo, brilho automático desligado, só uma aba aberta.
- Celular sem capa, no suporte, com a câmera traseira apontada para a mesma pessoa, de pé numa marca no chão a cerca de 2 m, corpo inteiro no quadro, parada durante toda a execução. Nada de espelho: a pessoa de verdade, de frente para a câmera.
- **Recarregar a página** (puxar para baixo ou o botão de recarregar do Chrome). Toda execução começa com a página recém-aberta: é parte do método (nada sobra da execução anterior) e evita o erro `Cannot read properties of null (reading 'precision')` que aparece na segunda execução sem recarregar.
- Temperatura da bateria de volta ao valor de repouso (o coletor mostra em `bateria, temperature_c`).
- Na página, conferir o nome do integrante, a condição e o número da repetição. Não mexer na "Carga fixa".

## Uma execução

1. No PC: `python tools/coletor_adb.py --rotulo <condição>_r<n> --duracao 130`
2. Logo em seguida, no celular: **Iniciar execução**. A página entra em tela cheia, mede por 120 s e volta sozinha.
3. Conferir os avisos que a página mostra ao fim (carregando, câmera em resolução errada, pose encontrada em menos de 90% dos quadros, página saiu da tela). Execução com aviso fica salva, mas deve ser repetida. A taxa de pose importa: quando o rastreador perde a pessoa, ele roda a etapa de detecção, mais pesada, e o custo medido muda.
4. Ordem das condições: alternar `desligado → 480p → 1080p → desligado → …` até 5 repetições de cada.

Ao fim do dia, **Baixar todas (CSV)** e copiar `resumo_*.csv` e `quadros_*.csv` para `dados/`.

## Arquivos gerados

`resumo_*.csv` (página): uma linha por execução, com a configuração completa, o que a câmera de fato entregou, e `frame_mean_ms`, `frame_p50_ms`, `frame_p95_ms`, `frame_p99_ms`, `inference_mean_ms`, `tracker_hz`, `pose_detected_ratio`.

`quadros_*.csv` (página): uma linha por quadro. `frame_ms` é o intervalo desde o quadro anterior, `work_ms` o tempo gasto no quadro pelo JavaScript, `inference_ms` quanto o rastreador levou naquele quadro, `warmup=1` nos quadros descartados do aquecimento. `epoch_ms` serve para alinhar com o coletor.

`dados/adb/<rótulo>_<data>/` (coletor): `amostras.csv` no formato `epoch_ms, metrica, chave, valor` (`cpu_uso_pct`, `cpu_freq_mhz`, `temp_c`, `bateria_corrente_ua`, `bateria`), `bruto.txt` com a saída crua do aparelho e `meta.txt` com os relógios do PC e do celular para corrigir o desvio entre eles.
