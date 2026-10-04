# Phanes Studio — Electron, serviço sob demanda e acesso por agentes

Implementação dos cinco pontos acordados em 2026-10-04. Autenticação ficou fora desta etapa por decisão do usuário. O processamento e a interface Gradio existentes foram reaproveitados.

## 1. Aplicativo local

Abra o atalho **Phanes Studio** na Área de Trabalho ou no Menu Iniciar, `Start-PhanesStudio.bat` ou `desktop/dist/3DStudio/Phanes Studio.exe`. `Start-3DStudio.bat` e `Start-StableProjectorz.bat` continuam disponíveis como lançadores compatíveis. A janela Electron inicia o serviço, aguarda sua disponibilidade e carrega o Studio. Não é necessário abrir um terminal ou navegador. Uma segunda abertura traz a janela existente para frente.

O ícone atual em `desktop/assets/phanes-studio-minimal.png` usa uma semente geométrica violeta com uma centelha dourada central; `phanes-studio-minimal.ico` contém tamanhos de 16 a 256 pixels com transparência. A primeira versão detalhada permanece em `phanes-studio.png`/`.ico`. O empacotamento incorpora o ícone atual e os metadados Phanes Studio ao executável. A janela, a tela de abertura e o cabeçalho da interface usam o novo nome. O prompt e a origem da imagem estão em `desktop/assets/ICON.md`.

Para recriar os dois atalhos do usuário atual, execute `desktop/install-shortcuts.ps1` após empacotar. O script usa as pastas conhecidas do Windows, incluindo Área de Trabalho redirecionada, e aponta diretamente para o executável com pasta de trabalho e ícone explícitos. Não é necessário executar como administrador; a execução deve ocorrer no contexto do usuário que receberá os atalhos.

Fila, parâmetros, histórico HIGH/LOW, histórico de referências, paginação, progresso, visualizador GLB, remesh/bake e exportação de LODs continuam na interface existente. Downloads usam o diálogo de salvamento do Electron. O seletor de pasta da exportação permanece o seletor Windows existente.

A coluna de processamento tem duas listas: **Fila de execução atual**, com executando primeiro e aguardando na ordem de envio, e **Histórico de pedidos finalizados**, com concluídos, cancelados, falhos e interrompidos, mais recentes primeiro (até 200). A fila atual inclui todos os pedidos ativos, sem esse limite. Pausa e cancelamento ficam junto da fila atual; cancelar pendente atualiza as duas listas imediatamente, e a atualização periódica transfere trabalhos que terminam. As colunas mostram Modelo, Estado, Etapa, Erro e ID completo, com linhas compactas e rolagem horizontal quando necessária.

O menu permite abrir resultados, abrir registros, recarregar e ajustar zoom. Falhas de inicialização exibem o erro, com opção de tentar novamente ou consultar registros. A janela usa isolamento de contexto, sandbox e não expõe Node à página.

O executável é acompanhado pelos arquivos do Electron e reutiliza o runtime Python e os modelos desta instalação. Não mova somente o `.exe`: sua pasta `desktop/dist/3DStudio` e a estrutura do projeto são necessárias. Os atalhos também dependem desta localização. Esta entrega não transforma o ambiente de IA em um pacote portátil para qualquer computador.

## 2. Núcleo separado da interface

`studio_service.py` conserva a fila e os workers. `studio_api.py` constrói os endpoints, sem importar Gradio. `studio_runtime.py` administra o executor, conexões e encerramento. `studio_ui.py` constrói a interface somente quando o aplicativo solicita sua abertura.

Importar `studio_app.py` ou `studio_api.py` não inicia a fila nem cria o banco. A compatibilidade `studio_app.py` agora apenas encaminha a execução explícita ao runtime gerenciado.

Um agente pode trabalhar sem iniciar Electron ou carregar Gradio. Se a interface for aberta posteriormente, ela se conecta ao mesmo serviço e à mesma fila; não reinicia o processamento. Depois da primeira abertura, os módulos de interface permanecem na memória até o serviço encerrar.

## 3. Cliente estável para agentes

No PowerShell, a partir de qualquer pasta:

```powershell
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' status
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' models
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' generate --image 'D:\Referencias\mesa.png' --request-key 'meu-chat-mesa-v1'
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' job ID_RETORNADO
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' wait ID_RETORNADO --timeout 7200
```

Também há `Studio-Agent.ps1`. Para evitar diferenças na passagem de opções pelo PowerShell, agentes podem chamar diretamente:

```powershell
& 'D:\Projetos\3dGeneratorNew\runtime\official\code\venv\Scripts\python.exe' 'D:\Projetos\3dGeneratorNew\scripts\studio_cli.py' models
```

| Comando | Comportamento |
|---|---|
| `status` | Consulta sessão atual sem ligar o serviço |
| `start` | Inicia/reutiliza somente o backend; `--ui` também prepara a interface, mas não abre uma janela |
| `models`, `history`, `images`, `jobs` | Lista modelos, histórico, referências ou pedidos em JSON |
| `job ID` | Consulta estado, parâmetros, erro e progresso real quando disponível |
| `generate --image ARQUIVO` | Envia imagem; `--image` pode ser repetido para lote sequencial |
| `remesh --model ID` | Cria variante LOW pelo método selecionado |
| `wait ID` | Acompanha até um estado terminal; mantém o cliente ativo durante a espera |
| `pause`, `resume` | Controla a fila inteira; ativo termina antes da pausa |
| `cancel ID` | Cancela somente pendente |
| `download --model ID --destination ARQUIVO` | Salva o GLB exato sem sobrescrever arquivos |
| `export-lods --model ID --directory PASTA` | Exporta pacote; repetir `--model` para selecionar níveis |
| `stop` | Encerra somente se não houver clientes ou trabalho executável; não liga um serviço parado |

Geração aceita `--resolution 512/1024`, `--seed`, `--faces`, `--texture 512/1024/2048`, `--name` para uma imagem e `--request-key`. Remesh aceita `--method simplify/meshopt/instant/quadriflow`, `--triangles`, `--texture`, `--repair` e `--request-key`.

Exemplos adicionais:

```powershell
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' remesh --model ID_DO_HIGH --method simplify --triangles 12000 --texture 2048 --request-key 'mesa-low-v1'
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' download --model ID --destination 'D:\MeuJogo\mesa.glb'
& 'D:\Projetos\3dGeneratorNew\Studio-Agent.cmd' export-lods --model ID_LOD0 --model ID_LOD1 --directory 'D:\MeuJogo\Assets'
```

As respostas vão para stdout em JSON. Códigos: 0 sucesso; 1 erro operacional; 2 argumentos inválidos ou resultado terminal sem sucesso em `wait`; 3 timeout de espera. O timeout não cancela o pedido. Se parte de um lote falhar, a resposta inclui `submitted_jobs`, evitando reenvio cego.

Guarde os IDs retornados. Use chave estável para repetir um envio após falha de comunicação; mesma chave e conteúdo devolvem o mesmo pedido. Em lote, a chave recebe o SHA256 da imagem. Para nova tentativa após um pedido que falhou, crie uma chave nova.

## 4. Serviço sob demanda

O serviço escolhe uma porta livre em `127.0.0.1` e grava identidade, versão de protocolo, PID, instante de criação do processo, raiz e URL em `local_data/studio/runtime.json`. O cliente verifica essa identidade; não confunde uma porta ocupada por outro programa com o Studio.

Um bloqueio de inicialização serializa chamadas simultâneas, e o bloqueio do executor existente garante uma única fila. Os clientes não escrevem diretamente no banco. A janela e todos os chats enviam comandos ao mesmo serviço.

O encerramento automático ocorre depois de 120 segundos sem atividade, quando não houver solicitações em andamento, janela com presença válida, agente em espera ou trabalho ativo/executável. Fila pausada pode dormir com pendentes preservados. Uma fila ativa continua até terminar seus pedidos, mesmo depois de fechar a janela.

Ao fechar durante processamento, a janela informa que os pedidos continuarão. Fechar a janela não encerra o executor. Presenças têm prazo de 45 segundos e são renovadas a cada 10 segundos; quando uma janela/chat desaparece abruptamente, sua presença expira. O estado persistente permite consultar resultados em outro chat depois.

`stop` recusa encerramento com clientes ou trabalho ativo. Não oferece cancelamento forçado. Em queda do Windows/processo, o comportamento existente registra trabalhos que estavam executando como interrompidos na próxima inicialização; não promete retomar inferência do ponto da queda.

Para testes isolados, `STUDIO_ROOT`, `STUDIO_PYTHON` e `STUDIO_IDLE_SECONDS` permitem usar outro workspace, Python e intervalo. Para uso normal, conserve os padrões. Esses parâmetros não tornam o venv atual relocável.

## 5. Continuidade em outros chats

`AGENTS.md` na raiz fornece instruções operacionais para novos chats. Eles podem iniciar, enviar, acompanhar e exportar trabalhos sem abrir a interface. Basta ter acesso aos arquivos locais e permissão para executar o cliente.

Chats sem acesso a este computador precisam de uma integração própria; o executável não torna o projeto acessível automaticamente a chats remotos. Um futuro adaptador MCP pode reutilizar `studio_client.py`; não foi necessário instalar ou configurar MCP nesta entrega.

## Reconstruir a janela

Com Node compatível e internet para obter dependências:

```powershell
Set-Location 'D:\Projetos\3dGeneratorNew\desktop'
$env:ELECTRON_CACHE = 'D:\Projetos\3dGeneratorNew\runtime\cache\electron'
npm install --cache 'D:\Projetos\3dGeneratorNew\runtime\cache\npm' --no-audit --no-fund
node node_modules/electron/install.js
node package.cjs
```

Electron está fixado em 44.5.1 com lockfile. A versão inclui instalação explícita de seus binários. O empacotamento prepara permissão de leitura/execução dos binários para a sandbox do Windows. Feche a janela antes de reconstruir a pasta do aplicativo.

## Verificação

O validador `scripts/validate_desktop_runtime.py` cria um workspace separado e usa um worker controlado, que copia um GLB existente. Ele verifica concorrência, idempotência, persistência, pausa/cancelamento, exportação/download, continuidade, falha, espera e encerramento ocioso sem executar inferência na GPU nem inserir modelos de teste na galeria real.

Evidência de runtime: `local_data/studio/desktop-runtime-validation.json`. A verificação Electron usa a janela real, sem uma porta de depuração adicional; gera relatório e captura em `local_data/studio/desktop-window-validation.json` e `.png`.

Registros: `logs/studio-runtime.log` e `logs/studio-desktop.log`. A migração preservou os fontes anteriores em `logs/desktop-migration-original/`. As evidências não representam novos benchmarks de qualidade de geração/remesh.

Resultado: 15 verificações de integração passaram no workspace isolado. A janela Electron carregou os dois históricos e um GLB com renderização WebGL, confirmada pela captura. A migração conservou 22 modelos, 6 referências e 16 pedidos, com registros idênticos e hashes dos arquivos preservados; backup SQLite em `logs/desktop-migration-original/studio-before-desktop.db`. Nenhuma inferência nova foi executada na galeria real.

As tentativas iniciais de executar Electron dentro da sandbox do agente produziram erro nativo do Windows. A validação final usou a execução normal do usuário, mantendo a sandbox interna do Electron ativada. Não foi necessário desativar a proteção da janela.
