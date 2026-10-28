# Resultados verificados — 28/10/2026

Projeto trabalhado em `/workspace/Cyber_Snake_Royale`, extraído do ZIP original. O repositório de perfil não foi modificado. Testes automatizados em Linux, Python 3.12 e Chromium headless; sem teste em Android ou iPhone físicos. O usuário confirmou por captura a instalação das dependências e a inicialização do servidor no Windows com Python 3.11.

## Skins, liderança e poderes

Implementadas cinco skins cosméticas selecionáveis junto ao nome e à cor, com prévias reais; coroa do líder na arena e em ambos os rankings; bônus de cinco pontos sobre a eliminação normal do líder; ímã (8s), escudo (6s) e turbo (6s) coletáveis. Pausa congela a duração e morrer remove os efeitos. Skins e efeitos persistem na reconexão dentro do prazo normal. Incluída a homenagem simples **“PDP · Homenagem à Rede Cidadã”**, conforme escolha do usuário. Nenhuma informação foi obtida de outro chat.

**25 testes determinísticos passaram** (13 regras anteriores + 12 testes dos novos poderes/liderança). O protocolo verificou as cinco skins, fallback para Neon em valor inválido e preservação da skin ao retomar. O navegador verificou cinco prévias diferentes, escolha da cor, skin sincronizada, homenagem, coleta dos três poderes, indicadores de duração congelados na pausa, coroa nos dois rankings e retenção de skin/efeitos após reload. Zero erros JavaScript. A renderização evita desenhar objetos fora da tela para reduzir o trabalho gráfico; desempenho em 30 celulares físicos permanece pendente.

A última carga, detalhada abaixo, usou os cinco tipos de skin entre os 30 jogadores. Todos os clientes confirmaram as skins, os três tipos de item no mapa e a coerência da marcação do líder com o ranking.

## Mapa ampliado

Arena ampliada de 2.200 × 1.400 para **3.600 × 2.400**, aproximadamente **2,8 vezes a área**, a pedido do usuário. As outras regras e controles foram mantidos. O snapshot foi conferido com as novas dimensões, 30 pontos de nascimento e comidas dentro dos limites. Regras (13 testes), integração e navegador mobile/painel foram reexecutados com sucesso; as capturas e métricas de carga abaixo correspondem à arena ampliada.

## Correções implementadas

- BAT com detecção funcional de `python` antes de `py -3`, reutilização do ambiente virtual, verificação de versão, caminhos entre aspas e fluxo por labels. Removidos blocos que usavam `%errorlevel%` expandido antes do comando e texto com parênteses dentro desses blocos, fontes de erros do iniciador original. Arquivo com finais CRLF. Shell Linux/macOS também reutiliza `.venv`.
- Servidor com filas limitadas por conexão e escritores independentes: enviar para clientes lentos não trava o passo de simulação. Limite de 100 conexões totais e 100 mensagens/s por conexão. Compressão WebSocket disponível e utilizada no teste de carga.
- Agendamento compensado para aproximadamente 30 passos/s e 12 estados/s; suavização visual no navegador.
- Colisões frontais simétricas, detecção do último segmento do corpo, proteção inicial aplicada após a contagem regressiva (antes expirava durante os cinco segundos de contagem). A parede continua letal durante a proteção.
- Retomada por token privado da aba durante 30s, sem zerar pontos; expiração de ausentes. Comandos de boost expiram se não forem renovados.
- Relógio e temporizadores congelados na pausa; indicação visual de pausa; controles deixam de ficar presos ao perder foco. Direção inicial respeita a orientação do spawn, tecla Espaço não é capturada no campo de apelido e WASD aceita maiúsculas.
- Chave do apresentador removida da barra de endereço após autenticação; cabeçalhos de proteção e rejeição de WebSocket com Origin de outro domínio. Mensagens malformadas, ângulos não finitos/grandes e chaves Unicode não derrubam a conexão.
- QR com margem de leitura de quatro módulos; configuração de URL pública por `PUBLIC_URL`; receitas Render e Docker; dependências fixadas nas versões instaladas.

## Verificações concluídas

| Verificação | Resultado |
| --- | --- |
| `python tests/physics.py` | **13 testes passaram**: movimento, giro, boost, comida/crescimento, paredes, corpo, cabeça, próprio corpo, proteção/reaparecimento, pausa, ranking/resultados, ausência, reinício |
| `python tests/features.py` | **12 testes passaram**: coleta/expiração dos efeitos, proteção, parede letal, turbo, pausa dos temporizadores, limite de itens, limpeza na morte/lobby, liderança, bônus e renovação sem empilhamento |
| `python tests/protocol.py` | Passou: JSON malformado, chave Unicode inválida, comando sem autorização, nome sanitizado, skins válidas/inválidas, retomada com pontuação e skin, 40 entradas aceitas, 41ª negada, Origin externo e QR inválido negados |
| `python tests/integration.py` | Passou: HTTP, SVG QR, 3 jogadores, contagem/início, movimento, pausa/retomada, remoção, retorno ao lobby com zeragem |
| `python tests/browser.py` | Passou: painel autenticado, QR **decodificado** e comparado ao link de jogador sem chave, cinco prévias e seleção de skin/cor, homenagem, entrada mobile, coleta dos três poderes e indicadores, coroa nos dois rankings, joystick/boost multitouch nativo, pausa, reload/reconexão, resultados e nova rodada; **zero erros JavaScript** |
| Tamanhos de tela emulados | Controles visíveis e dentro da tela em 360×640, 390×844 e 844×390 |
| `node --check` | Passou para `player.js`, `host.js` e `render.js` |
| `pip check` | Nenhuma dependência quebrada |

O teste do navegador confirma eventos de toque reais em Chromium via CDP, mas não sensibilidade de joystick, FPS e compatibilidade Safari em hardware real. Resultados usam antecipação do relógio autoritativo no teste de navegador para exercitar a tela final; o teste de carga abaixo percorre uma rodada de 60 segundos sem antecipação.

## Último teste de carga da versão entregue

Comando: `python tests/carga_30.py --seconds 67`. Servidor em **processo separado**, 30 conexões de jogador estabelecidas concorrentemente, distribuídas entre as cinco skins, mais um apresentador; leitura contínua de estados; cada jogador envia direção e boost a 20 Hz e uma medição de ping por segundo. Contagem de cinco segundos, rodada real de 60 segundos e tela final. Todos os jogadores permaneceram conectados, receberam ranking com 30 participantes e tiveram mudanças de posição. Movimentos automatizados não representam habilidade de jogadores humanos.

| Medida | Resultado |
| --- | --- |
| Jogadores simultâneos | **30**, nenhum desconectado |
| Menor número de estados recebido por jogador | **804 em 67 s**, aproximadamente **12/s** |
| Passos da simulação | **2.012**, aproximadamente **30/s** |
| Maior duração de um passo de regras | **57,663 ms** |
| Intervalo entre estados, p95 / máximo | **110,66 / 166,97 ms** |
| Ping/pong da aplicação, mediana / p95 | **1,42 / 11,71 ms**, exclusivamente rede local de teste |
| Dados JSON recebidos antes de compressão | **528,35 MB** no conjunto dos clientes |
| Bytes TCP efetivamente recebidos pelos 30 clientes | **65,4 MB**, aproximadamente **7,81 Mbps agregados**, compressão ligada |
| Estado final | `RESULTS`, 30 participantes |

Nesta execução houve um pico de 57,663 ms em um passo das regras e o maior intervalo entre estados foi 166,97 ms; não houve desconexão dos jogadores. Esses valores incluem efeitos do ambiente compartilhado e não constituem uma garantia de latência em produção. O teste de navegador também foi executado durante parte desta rodada.

Os bytes TCP foram lidos dos contadores Linux `TCP_INFO` de cada socket de cliente (diferença durante a janela de teste). Incluem frames WebSocket e dados comprimidos; **não** incluem cabeçalhos IP/TCP, retransmissões de infraestrutura ou TLS. Os 63,09 Mbps presentes em `serverOutboundPayloadMbps` do JSON referem-se ao payload **antes de compressão**, não à largura de banda efetiva medida. Há variação entre rodadas aleatórias. O telão, HTTPS e overhead da rede exigem margem adicional. Prefira disponibilidade sustentada superior a 15 Mbps de saída e valide no serviço/rede reais; isso é uma recomendação de margem, não uma garantia.

O teste não mede desempenho com 30 cobras no comprimento máximo, 30 navegadores renderizando, abuso deliberado prolongado, internet móvel instável nem sessão de horas. Limite de 40 entradas não equivale a capacidade garantida para 40 aparelhos.

## Ainda não verificado / pendente

- Suíte automatizada completa no Windows e validação da rede/Firewall do notebook. A instalação e a inicialização pelo BAT já foram confirmadas pelo usuário.
- Teste de campo com 30 celulares, Wi-Fi escolar, Android/iOS e dados móveis.
- Build/execução do Docker: receita incluída, não executada.
- Deploy Render: `render.yaml` preparado para uma instância Starter paga; conferir preço antes de criar. O usuário informou que ainda não possui hospedagem. **Não há link público ativo, HTTPS/WSS de produção testado ou QR definitivo para a turma.**
- O QR mostrado e decodificado durante o teste corresponde ao endereço local configurado para aquele teste. Não deve ser distribuído como endereço público.

Para concluir a publicação, criar o serviço na conta Render a partir de um repositório próprio do jogo, seguir o guia, abrir o domínio real em dois celulares e então compartilhar o QR gerado pelo painel. Sem conta/serviço provisionado não é possível afirmar acesso público.

A partida vive na memória de um único processo. Reiniciar perde o estado; não usar múltiplas instâncias/workers. Não há persistência de resultados nem sistema de contas/banimento permanente.

## Evidências

- `artifacts/load30.json`: métricas do último teste de carga.
- `artifacts/browser.json`: etapas concluídas no navegador e lista vazia de erros.
- `artifacts/customization.png`: tela de entrada com skins e homenagem.
- `artifacts/mobile-playing.png`, `artifacts/mobile-paused.png`, `artifacts/presenter.png`: capturas reais do navegador automatizado, com um participante de teste.
