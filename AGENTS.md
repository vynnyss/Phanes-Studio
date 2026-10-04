# Phanes Studio — instruções para outros chats

Este projeto utiliza TRELLIS.2-stableprojectorz, uma fila SQLite compartilhada e uma janela Electron. O guia atual é `docs/DESKTOP_E_AGENTES.md`; a API está em `docs/API_STUDIO.md`.

Nome público: **Phanes Studio**. Executável: `desktop/dist/3DStudio/Phanes Studio.exe`; lançador: `Start-PhanesStudio.bat`. Ícones em `desktop/assets/`; atalhos do usuário são instalados por `desktop/install-shortcuts.ps1`. Preserve os caminhos de dados e o cliente `Studio-Agent.cmd` ao ajustar a identidade visual.

Após clonar, use `Install-PhanesStudio.ps1`; opções e requisitos em `README.md` e `docs/INSTALACAO.md`. `runtime/`, pesos, ambientes, banco, entradas e resultados não acompanham o Git. Use a raiz real do clone em vez do caminho da instalação original abaixo. O caminho Blender pode ser definido em `local_data/settings.json` (gravado pelo instalador) ou `ASSET_BLENDER`, com prioridade para a variável. Fontes/hash dos downloads em `setup/sources.json`; preserve créditos e avisos de licença em `THIRD_PARTY_NOTICES.md`.

## Acesso por agentes

- Use `D:\Projetos\3dGeneratorNew\Studio-Agent.cmd` ou o Python local com `scripts/studio_cli.py`.
- Os comandos retornam JSON. `status` consulta sem iniciar; os comandos de trabalho iniciam ou reutilizam automaticamente o serviço, sem abrir Electron.
- Exemplo PowerShell: `& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' models`.
- Envio: `generate --image CAMINHO_ABSOLUTO --request-key CHAVE_ESTAVEL`. Guarde os `job_id`; use `job ID` ou `wait ID` para acompanhar.
- Reenvie a mesma chave apenas com a mesma imagem e parâmetros. Uma chave com conteúdo diferente é recusada. Em lote, o cliente acrescenta o hash de cada imagem à chave.
- Comandos disponíveis: `start`, `status`, `models`, `history`, `images`, `jobs`, `job`, `generate`, `remesh`, `wait`, `pause`, `resume`, `cancel`, `download`, `export-lods`, `stop`.
- Códigos de saída: 0 sucesso; 1 erro operacional; 2 argumentos inválidos ou pedido terminado sem sucesso em `wait`; 3 timeout de espera. Timeout não cancela o trabalho.

## Fila e arquivos

- Todos os chats e a janela usam o mesmo executor. Não inicie `run_test.py`, a interface original ou outro executor em paralelo à fila.
- Não escreva diretamente em `studio.db` nem crie processos `Studio.start()` em ferramentas de agentes. Use o cliente.
- `pause` afeta a fila inteira; use somente quando solicitado ou necessário para manutenção autorizada. `cancel` aceita somente pedidos pendentes.
- O serviço escolhe uma porta em `127.0.0.1`. Não fixe 8080; deixe o cliente descobrir a sessão em `local_data/studio/runtime.json`.
- O serviço termina após 120 segundos ocioso, sem janela, clientes ou trabalho ativo. Fila pausada pode dormir e será preservada. Abra o aplicativo ou execute um comando para retomar o serviço.
- Fechar a janela ou terminar um chat não cancela pedidos enviados. Um processo de `wait` mantém uma presença renovável; quando termina, essa presença é liberada.
- Preserve `outputs/`, `inputs/`, `local_data/studio/studio.db` e `local_data/studio/images/`. IDs, relações HIGH/LOW e aprovações existentes devem ser conservados.
- `completed` significa artefato disponível, não aprovação de qualidade. Não aprove resultados em nome do usuário.

## Desenvolvimento

- Leia a documentação atual antes de alterar funcionalidades. Atualize-a após mudanças de comportamento.
- Repositório: `https://github.com/vynnyss/Phanes-Studio`. A primeira publicação na `main` foi autorizada explicitamente pelo usuário. Para mudanças posteriores, siga o fluxo Git aplicável à sessão. Dependências podem conter seus próprios repositórios; não modifique o código upstream sem necessidade e autorização correspondente.
- Núcleo: `scripts/studio_service.py`; API: `studio_api.py`; interface: `studio_ui.py`; ciclo de vida: `studio_runtime.py`; cliente: `studio_client.py` e `studio_cli.py`; janela: `desktop/main.cjs`.
- Importar módulos não deve iniciar serviços ou trabalhos. A interface Gradio deve continuar sendo carregada sob demanda.
- Use UTF-8 explicitamente ao ler/escrever código, documentos e JSON no Windows.
- Execute validações de fila e ciclo de vida em workspace isolado: `scripts/validate_desktop_runtime.py`. Não crie trabalhos de teste na galeria do usuário.
- Não há autenticação nesta versão, conforme decisão do usuário. Mantenha o serviço restrito a loopback.
