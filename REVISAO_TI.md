# Informações para revisão do pacote pelo suporte de TI

## Alerta relatado

O navegador do computador institucional bloqueou o download de `Cyber_Snake_Royale_FINAL.zip` com **“Vírus detectado”**. A captura não informa o identificador da ameaça nem o item interno detectado. O usuário informou que a proteção é a do Windows e não conseguiu consultar o histórico.

Ainda não há diagnóstico da causa. **Não foi confirmado falso positivo, nem foi feita varredura pelo Microsoft Defender neste ambiente Linux.** Os testes funcionais não substituem uma análise de segurança. Não foi solicitado desativar a proteção, restaurar quarentena ou executar o pacote à força.

## Identificação do pacote

- SHA-256 do ZIP distribuído: `0006a7b7d728e0cd5eccebe6ada871ee38085eb146ef07721a772892c6479285`
- Manifesto de arquivos internos e respectivos hashes: `PACOTE_SHA256.json`.
- Os arquivos-fonte desta branch foram extraídos do mesmo ZIP, com identidade byte a byte.
- O ZIP não contém `.exe`, `.dll`, `.msi` nem os recuperadores antigos em texto/PowerShell. Isso é apenas uma descrição do conteúdo, não uma comprovação de segurança.

## Comportamento previsto para análise

- `iniciar_windows.bat`: procura Python 3.10+, cria um ambiente virtual local, instala as dependências fixadas de `requirements.txt` pelo pip e inicia `server.py`.
- `server.py`: abre um servidor HTTP/WebSocket no endereço `0.0.0.0`, porta padrão 3000, com arquivos estáticos e simulação em memória. Gera uma chave de apresentador se `HOST_KEY` não estiver configurada.
- `public/`: HTML, CSS, JavaScript e favicon do jogo.
- `tests/`: suítes locais de regras, protocolo, navegador e carga; não são executadas pelo BAT.
- `render.yaml` e `Dockerfile`: receitas opcionais de hospedagem, não executadas pelo BAT.

## Informação necessária para concluir o diagnóstico

O administrador pode consultar os registros da proteção utilizada e informar o **nome/ID da ameaça, item afetado, horário e ação aplicada**. Só então é possível avaliar o arquivo apontado ou encaminhar um possível falso positivo ao fornecedor. Qualquer liberação no computador institucional depende da avaliação e das regras da equipe de TI.
