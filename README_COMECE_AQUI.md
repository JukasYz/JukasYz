# Cyber Snake Royale — versão para apresentação

Jogo autoritativo em Python/aiohttp, HTML, CSS e JavaScript. Cada celular abre o link de jogador; o apresentador inicia, pausa, retoma e encerra as rodadas. Arena preta e roxa de **3.600 × 2.400**, com aproximadamente **2,8 vezes a área** do mapa original. Limite de entrada: 40 jogadores, com teste automatizado de 30 clientes (consulte RESULTADOS_TESTES.md).

## Windows: iniciar sem depender do comando `py`

1. Instale **Python 3.10+**, marcando **Add Python to PATH**. Feche e reabra o terminal. Confira `python --version`.
2. Extraia **toda** a pasta do ZIP. Não execute o BAT dentro do ZIP.
3. Abra `iniciar_windows.bat`. Ele procura primeiro um ambiente virtual existente, depois `python`, depois `py -3`. Cria `.venv`, instala versões fixas e inicia o servidor. A primeira instalação requer internet.
4. Abra no notebook o endereço do **PAINEL DO APRESENTADOR** que o terminal mostra. A chave é privada; não compartilhe esse endereço nem projete o terminal.
5. Escolha no painel o endereço da rede dos alunos. Compartilhe apenas o QR Code/link de jogador.
6. Os celulares devem estar na mesma rede Wi-Fi para o modo local. Permita Python no Firewall do Windows **somente na rede privada**. Uma rede escolar com isolamento entre clientes pode impedir o acesso; nesse caso, use hospedagem online ou hotspot permitido pela escola.
7. Após os alunos entrarem, clique em **INICIAR RODADA**. Ctrl+C encerra o servidor.

Alternativa no PowerShell, dentro da pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

Se `python` e `py` não existirem, a instalação do Python/PATH precisa ser corrigida; o jogo não inclui o interpretador. Se a pasta `.venv` veio de outro computador, apague **somente `.venv`** e execute o BAT novamente. Porta ocupada: feche o outro servidor ou configure `$env:PORT="3001"` antes de iniciar. Não desative o firewall inteiro.

**O BAT foi reescrito sem blocos parentetizados e sem expansão antecipada de `%errorlevel%`. O usuário confirmou a instalação das dependências e a inicialização no Windows com Python 3.11. Os testes automatizados foram executados em Linux.**

## Linux/macOS

```sh
sh iniciar_linux_mac.sh
```

É necessário Python 3.10+ com suporte a `venv` e `pip`. O ambiente virtual é reutilizado nas execuções seguintes. Nenhuma chave deve ser escrita em arquivos compartilhados.

## Como jogar e regras

- Celular: arraste o joystick à esquerda; segure BOOST à direita para acelerar. Dois dedos são suportados.
- PC: mouse, setas ou WASD; Espaço acelera. A energia recarrega ao soltar.
- Comidas: roxo 2, verde 5, amarelo 10 pontos. A cobra cresce conforme a pontuação.
- Paredes, próprio corpo e corpos dos adversários eliminam. Colisão frontal elimina ambos, sem bônus; colidir no corpo de outro dá 10 pontos ao adversário.
- Há proteção de 3,2s contra cobras no início e após reaparecer; **paredes continuam perigosas**. Reaparecimento em aproximadamente 2,8s. Pontos acumulados permanecem.
- Vence a maior pontuação; desempate por eliminações e depois nome.
- A pausa congela tempo, movimento e temporizadores de proteção/reaparecimento.
- Recarregar a mesma aba ou perder a conexão por até 30s permite retomar com o mesmo jogador e pontuação. A cobra continua simulada durante a ausência. Depois de 30s, o jogador é removido; nova entrada começa zerada. Abas diferentes normalmente são jogadores distintos; evite duplicar uma aba já conectada.
- O apresentador pode remover participantes. Isso não é um banimento: eles podem entrar novamente.

## Skins, líder e power-ups

Na tela de nome e cor, escolha entre **Neon, Conexões, Listras, Pixel e Galáxia**. A prévia usa a cor escolhida e o apelido. Todas as skins têm a mesma velocidade e regras; são apenas visuais. A escolha é lembrada no navegador e preservada na reconexão.

O primeiro colocado com pontuação acima de zero recebe uma **coroa dourada** na arena e no ranking dos jogadores e do apresentador. Eliminar esse líder por colisão no seu corpo vale **15 pontos** (10 normais + 5 de bônus). A coroa segue o ranking; empate usa eliminações e depois nome, como antes. Colisão frontal elimina ambos sem bônus; bater na parede ou em si mesmo também não dá bônus a outro jogador.

Os hexágonos no mapa são coletados ao passar por cima:

| Poder | Duração | Efeito |
| --- | --- | --- |
| 🧲 Ímã | 8 segundos | Coleta comida em um raio maior ao redor da cabeça |
| 🛡 Escudo | 6 segundos | Protege de colisões com cobras; **paredes continuam letais** |
| ⚡ Turbo | 6 segundos | Energia de BOOST fica cheia; segure o botão/tecla normal para acelerar |

Até seis power-ups ficam no mapa: a rodada começa com dois de cada tipo e uma vaga é reposta a cada oito segundos. Uma nova coleta do mesmo tipo renova a duração a partir daquele momento, sem acumular tempo indefinidamente. Efeitos diferentes podem ser combinados. A duração restante aparece na tela e congela durante a pausa; morrer ou iniciar outra rodada remove os efeitos. Nenhum botão adicional é necessário no celular.

A tela de entrada e o painel incluem **“PDP · Homenagem à Rede Cidadã”**, conforme pedido do autor do projeto.

## Hospedagem pública: Render

Esta entrega inclui `render.yaml` para **uma instância paga Starter** (implica custo conforme a plataforma). Não contrate sem conferir o preço atual. Um plano gratuito pode adormecer e interromper a apresentação.

1. Envie esta pasta para **um repositório próprio do jogo**, sem `.venv`, `.env` ou chaves. O repositório de perfil enviado anteriormente não foi alterado.
2. Na sua conta Render, crie um Blueprint a partir desse repositório e confira `render.yaml`, plano e custos antes de implantar.
3. A configuração instala `requirements.txt`, executa `python server.py`, monitora `/health` e gera `HOST_KEY` privadamente. Se criar manualmente: runtime Python 3.12, Build `pip install -r requirements.txt`, Start `python server.py`, uma instância. Defina `HOST_KEY` longo e aleatório nas variáveis seguras.
4. Depois que o deploy estiver saudável, abra o domínio HTTPS **real fornecido pela plataforma** para os jogadores. Abra `/host.html?key=SUA_CHAVE` nesse mesmo domínio para o apresentador. A chave sai da barra de endereço e fica na sessão da aba após carregar.
5. O painel usa automaticamente o domínio público para gerar o QR Code, sem incluir a chave. Para domínio próprio/proxy, defina `PUBLIC_URL` com o endereço HTTPS completo, sem caminho. O proxy deve permitir WebSockets, preservar Host e encaminhar `X-Forwarded-Proto`.
6. Teste com um celular usando dados móveis e outro em Wi-Fi, entre na mesma sala e confirme movimento/ranking antes de divulgar o QR Code.
7. Para baixar o QR Code, abra `/api/qr?url=` seguido do link de jogador codificado como URL (ou salve a imagem do painel). Um QR só é útil quando o domínio real está publicado e acessível.

**Nenhum domínio público foi provisionado nesta entrega.** É necessário acesso à conta/serviço de hospedagem para publicar e verificar HTTPS/WSS e o QR final. Não há credencial de hospedagem conectada neste ambiente. Não use links de exemplo como se fossem o jogo online.

## Docker (alternativa, receita ainda não executada)

```sh
docker build -t cyber-snake .
docker run --rm -p 3000:3000 --env HOST_KEY --env PUBLIC_URL cyber-snake
```

Defina as variáveis no seu shell/gerenciador de segredos antes. O container roda com usuário sem privilégios. O host deve encaminhar HTTPS/WSS por proxy reverso. A receita Docker foi preparada, mas não testada nesta máquina.

## Limitações e apresentação

- Uma única sala, um processo e uma instância. **Não habilite múltiplos workers, autoscaling ou réplicas:** cada processo teria uma partida diferente. Reiniciar/deployar o serviço apaga a partida e as sessões.
- Sem banco de dados, histórico persistente, contas ou proteção robusta contra abuso público. Há validação de entradas, limite de mensagens por conexão, limite de conexões e autenticação do apresentador.
- Cliente lento tem fila limitada e não bloqueia a simulação; atraso extremo de escrita pode desconectá-lo para permitir reconectar.
- O teste de carga usa rede local da máquina e clientes automatizados, não 30 celulares físicos. Latência de internet, upload do notebook, Wi-Fi e desempenho dos aparelhos podem limitar a experiência.
- Teste o Wi-Fi/serviço com aparelhos reais antes da apresentação. Prefira notebook na tomada, conexão estável e uma instância sem suspensão. Não prometa 40 jogadores por causa do limite de entrada.

## Executar verificações

Use o Python do ambiente virtual (`.venv/bin/python` em Linux/macOS ou `.venv\Scripts\python.exe` em Windows):

```sh
python tests/physics.py
python tests/features.py
python tests/protocol.py
python tests/integration.py
python tests/carga_30.py --seconds 67
```

Para o navegador, instale `requirements-dev.txt` e um Chromium compatível (ou `python -m playwright install chromium`). Execute `python tests/browser.py`. O teste procura `chromium` no PATH; opcionalmente defina `BROWSER_EXECUTABLE` com o caminho do navegador. Ele emula tela/touch mobile, não hardware Android/iPhone real. Testes iniciam seus próprios servidores; a carga usa a porta 3107.

Relatórios e capturas estão em `artifacts/`; resultados e limites estão em `RESULTADOS_TESTES.md`.
