# Status — 2026-10-04

## 2026-10-04 — Cartões e acompanhamento ao iniciar

Implementado: espaço no histórico ao iniciar processamento, referência marcada Processando, seleção exibe carregamento/etapa/passos reais e automaticamente abre o GLB concluído do mesmo ID. Download/remesh indisponíveis enquanto processa. Falhas/interrupções visíveis; pendentes sem modelo. Seleção de outro resultado preservada. jobs.started e GET /api/history adicionados; /api/models mantém somente concluídos. Verificado com subprocessos/controladores em workspace isolado e parser de logs, sem fixtures na galeria real. Referência e GLB do usuário front foram preservados após geração real concluída (249721 triângulos). UI visual/WebGL automatizados permanecem não verificados. Ver STUDIO_UI_E_HISTORICO.md e processing-validation.json.

## 2026-10-04 — Imagens e paginação entregues

Dois históricos paginados de quatro itens, modelos acima e imagens abaixo, navegação independente. Referências de teste e envios anteriores/futuros preservados e deduplicados por SHA256; clique reutiliza como entrada sem gerar automaticamente. Migração reference_images e API GET /api/images, GET /api/images/{id}/file. Modelos, IDs e relações anteriores preservados. Controles, páginas, seleção, download e cópias permanentes validados via cliente/callbacks. Navegação visual automática permanece não verificada por falha da ferramenta. Guia atualizado em STUDIO_UI_E_HISTORICO.md e evidência pagination-validation.json.

Uso por agentes implementado por API HTTP: envio de imagens/remesh, consulta/cancelamento/pausa, idempotência, histórico e downloads. Não há agente próprio que crie a referência e envie automaticamente, nem plugin MCP. Geração completa pelo novo endpoint ainda não repetida. Principais pendências de qualidade: remesh robusto, eficiência UV (26–30% no teste), avaliação bake/mipmaps, outros props e importação no jogo. São limitações conhecidas; não declarar escopo de qualidade encerrado.

## Atualização executável — Studio, 2026-10-04

Fila, API local, histórico HIGH/LOW e remesh + UV + bake implementados. Histórico contém quatro HIGH e dois LOW da pistola, vinculados e com originais preservados. Callbacks de seleção/Model3D, download, relações, controle da fila e submissão de duas imagens testados. Instant Meshes gerou 7919 e 22224 triângulos; QuadriFlow recusou a pistola com e sem voxel. Qualidade/UV automáticos continuam experimentais; UI WebGL visual e geração completa pelos novos botões não verificadas. Guia atual: STUDIO_UI_E_HISTORICO.md; API_STUDIO.md; TESTES_REMESH.md. Evidências: local_data/studio/ e outputs/studio/.

As seções anteriores abaixo registram o estado histórico e são substituídas por esta atualização quanto às funcionalidades novas.


**Instalação e avaliação local concluídas. Veredito B: substituição parcial.**

## Implementado e validado

- Pacote oficial v22, Python portátil 3.11.9 e ambiente isolado no disco D; CUDA FP16, extensões e EXR funcionando.
- Smoke 512 e três casos 1024 (garrafa, pistola, arquitetura), todos com textura e GLB, sem CUDA OOM.
- Seeds, parâmetros, hashes, latentes, renders e métricas por macroetapa preservados.
- Importação e inspeção estrutural dos três GLBs no Blender 5.2.1; cenas e renders salvos. Alpha da garrafa ajustado em uma cena separada, conforme orientação do autor.
- Interface oficial: HTTP 200 e upload/pré-processamento via API. Lançadores na raiz.
- Fonte upstream preservada; apenas dependência OpenCV corrigida para EXR e helpers próprios ajustados ao ambiente oficial.
- Documentação final em results e verdict; nenhum AISmith, treino ou gerador alternativo instalado.

## Limitações e pendências de validação

- UI não foi percorrida visualmente: ferramenta de navegador falhou. Geração completa foi validada pelo worker oficial, sem repetir todo o ciclo pelo navegador.
- Picos são amostrados; allocator Torch exato não exposto. O teste principal usou até 38,32 GiB de memória privada e dependeu de paginação.
- Grid intermediário do remesh oficial limitado a 512, mesmo com geração 1024.
- Cleanup, retopologia, LOD e importação Godot não executados; lâminas finas e precisão de partes ocultas não certificadas.
- Auditoria completa para produção comercial pendente, especialmente RMBG 2.0 e DINOv3.

## Uso e retomada

Servidor deixado ativo em http://127.0.0.1:8080. Se estiver encerrado, abrir Start-StableProjectorz.bat na raiz. Não iniciar outra instância enquanto a porta estiver ocupada. Roteiro manual em [README](README.md).

Priorizar o workflow Blender/Godot quando houver novo pedido; a necessidade de desenvolver gerador próprio está encerrada para o objetivo avaliado. Não iniciar novos benchmarks ou instalar outros geradores sem pedido. Consulte [resultados](stableprojectorz-results.md) e [veredito](stableprojectorz-verdict.md).

## Análise posterior — customização, 2026-10-04

Documento stableprojectorz-customization-analysis.md concluído, somente análise. Fila persistente, API para agentes, bake high→low e integração texture-only são propostas; não implementados/validados. Geração image→3D anterior permanece validada. Sem alteração do runtime ou início de serviços novos.

## Expansão confirmada pelo usuário — 2026-10-04

Fork TRELLIS.2-stableprojectorz adotado como base. Bake no Blender escolhido para textura após retopologia/UV; problema encerrado como escolha de workflow, não como bake já executado. Texture-only neural retirado da prioridade.

Planejado/não implementado: fila sequencial de várias imagens, acesso por agentes e histórico persistente clicável no visualizador 3D existente. Plano/UX e critérios de aceitação em EXPANSAO_PROJETO.md; decisões em DECISOES.md. Somente documentação/análise nesta etapa, sem mudança do serviço/runtime. Esta seção substitui a prioridade de texture-only sugerida anteriormente.

## Análise posterior — otimização automática de props

Foco em props estáticos confirmado; recomendação técnica em OTIMIZACAO_AUTOMATICA_PROPS.md. Redução adaptativa, UV/packing e bake automático continuam propostos, sem redução real ou novas medições. Não confundir os triângulos originais com contagens otimizadas. Variantes Original/Otimizado no histórico são proposta adicional.

## 2026-10-04 — Remesh com rejeição geométrica

Implementado e validado por execução real: simplificação preparada + reparo limitado de microfissuras + UV/bake, padrão simplify; bloqueio antes do bake e antes da exportação por novas bordas abertas/desvio de superfície. Estante testada: 11.993 triângulos, original preservado, candidato no histórico para revisão. Dois LOW Instant anteriores marcados rejeitados sem apagar artefatos. Instant com 35 mil triângulos também insatisfatório. Limites não certificam topologia completa; UV 29,69% e validação no jogo seguem pendentes. Evidência e roteiro manual em TESTES_REMESH.md e STUDIO_UI_E_HISTORICO.md.

Validação final desta correção: serviço atualizado ativo em 8080 (PID27208), fila retomada ao estado ativo anterior; nenhuma tarefa pesada interrompida. API/default/rejeição, callbacks de seleção e página inicial passaram. Evidência local_data/studio/remesh-quality-validation.json. Recarregar a página para renovar os componentes.

2026-10-04: usuário aprovou o remesh em testes. Candidato front · simplificação preparada 12 mil marcado approved; aprovação específica deste resultado, sem aprovação universal do método ou UV. Próximo tema: alternativas de unwrap/packing para melhorar os 29,69% medidos. Nenhum novo backend UV instalado.

2026-10-04: xatlas 0.0.11 testado na estante aprovada, mantendo 11.993 triângulos e geometria exata. Ocupação raster 29,69% ->40,94% /60,57%; bake e reimportação GLB passaram. Ambos no histórico para avaliação, compacto experimental por margens menores/atlas retangular. Método padrão UV não alterado; integração genérica e mipmaps na engine pendentes. Docs TESTE_UV_XATLAS.md; evidências outputs/uv-xatlas/. Fila restaurada ativa.

## 2026-10-04 — Comparação real e exportação de LODs

Implementado/validado: meshoptimizer1.3 MIT via Node/WASM local, 12 probes, 7 candidatos com bake no histórico. Pares8k/6k/4k +meshoptimizer12k, referência Decimate12k reutilizada. Meshoptimizer teve menor p95/maior pior IoU; aprovação manual pendente. Candidatos mínimos testados: Decimate3991 e meshoptimizer3947. UI Exportar LODs com seleção/pasta/seletorWindows; POST /api/exports/lods com destino absoluto, pacote único sem overwrite e GLBs incorporados, manifesto/relatórios/hashes. Exportação real4 níveis passou; UI construída/callbacks testados, seletor/WebGL não verificados visualmente. UV fora do atlas no meshopt4k corrigida por fit uniforme, falha preservada. Reconstrução parcial adiada pelo usuário. Guia COMPARACAO_REMESH_E_LODS.md e local_data/studio/lod-live-validation.json; fila restaurada ativa.

2026-10-04: corrigida codificação dos rótulos/legendas e mensagens do Studio. Sequências UTF-8 reinterpretadas como Windows-1252 foram restauradas nos fontes studio_app.py, studio_service.py e blender_asset_worker.py; nomes/IDs/arquivos do histórico preservados. Componentes da UI em /config e callback de seleção validados com acentos corretos; serviço reiniciado sem job ativo e pausa restaurada. Recarregar a página. Ao editar fontes/docs, usar read_text/write_text com encoding="utf-8" explicitamente para evitar nova corrupção no Windows.

## 2026-10-04 — Oito modelos e escolha direta de página

Pedido do usuário implementado: modelos em grade de 2 colunas e 4 linhas, até 8 itens por página; imagens abaixo em 2 colunas e 2 linhas, até 4 por página. Página dos modelos e Página das imagens permitem selecionar diretamente qualquer página disponível. Anterior/Próxima continuam; navegação independente, sem alterar o modelo já selecionado no visualizador. Páginas limitadas ao intervalo válido; histórico vazio mostra página1. Última página contém apenas itens existentes, sem modelos fictícios. Atualização automática renova o número de páginas quando necessário e evita redesenhar seletores sem mudança. IDs/persistência/modelos/referências preservados, nenhuma geração executada.

Roteiro manual: iniciar Start-StableProjectorz.bat somente se serviço não estiver ativo; abrir http://127.0.0.1:8080 e recarregar com Ctrl+F5. Conferir 8 posições no Histórico · high e low-poly e 4 no Histórico de imagens utilizadas. Em Página dos modelos escolher3 diretamente e clicar em modelo: GLB correspondente deve abrir. Escolher Página das imagens2: seleção 3D permanece, clicar imagem reutiliza entrada. Anterior/Próxima devem atualizar também o número do seletor. A última página pode ter menos itens. Conferir arquivos originais em outputs/, sem novas variantes criadas por navegar.

Validação executada: dados reais, tamanhos8/4, IDs visitados uma única vez, limites, vazio, ordem dos callbacks e seletor sem redesenho periódico; evidência local_data/studio/history-page-selection-validation.json. Configuração/callbacks servidos serão conferidos após reinício; navegação visual automatizada permanece não verificada.

Validação final: cliente Gradio inicializado pelo evento de carregamento selecionou diretamente modelos página3 (8 itens) e imagens página2 (2 itens), sem perder IDs/referências. Serviço atualizado ativo; estado da fila restaurado.

## 2026-10-04 — Barras numeradas no estilo da referência

Substituídos os dropdowns de página por barras compactas arredondadas: Anterior, números clicáveis e Próxima. Página atual com variante primary do tema (laranja), demais botões com cores escuras existentes. Sete posições reutilizáveis; para até7 páginas mostra todas, depois mostra início/fim e vizinhas com reticências não clicáveis. Botões de borda e página atual desabilitados quando apropriado. Mantidos8 modelos e4 imagens por página, navegação independente e seleção 3D intacta. CSS somente nas barras history-pagination; funções em studio_pagination.py, sem mudar o tema geral.

Roteiro manual: iniciar Start-StableProjectorz.bat somente se serviço estiver parado; abrir http://127.0.0.1:8080 e Ctrl+F5. Embaixo dos modelos, clicar número3 diretamente, conferir oito itens e destaque laranja no3. Embaixo das imagens, clicar2; conferir duas imagens atuais na última página, com seleção 3D preservada. Anterior/Próxima atualizam a barra. Com mais de7 páginas, reticências separam as faixas e primeira/última continuam acessíveis.

Validação: sequências de1–100 páginas, limites/destaque e atualização estável; cliques pelos endpoints dos botões em serviço real (modelos3/imagens2), CSS entregue e histórico preservado. Evidência local_data/studio/numbered-pagination-validation.json. Conferência visual automatizada não realizada: ferramenta de navegador falhou com trusted Node process exited unexpectedly. Estado anterior da fila restaurado.

## 2026-10-04 — Correção da paginação após F5

Implementado e validado: números e destaque da página 1 já presentes na configuração inicial, nos dois históricos, antes do load/clique. Botões deixam de ser entradas do próprio evento; navegação usa State da página. Novas sessões, páginas diretas, anterior e refresh passaram no serviço real; 24 itens/6 referências preservados e fila restaurada ativa. Evidência local_data/studio/numbered-pagination-initialization-validation.json. Conferência visual automatizada não verificada; roteiro manual em docs/STUDIO_UI_E_HISTORICO.md.

## 2026-10-04 — Electron e agentes sob demanda

Cinco pontos implementados: executável Electron preservando a UI Gradio; núcleo/API/UI separados sem inicialização ao importar; cliente JSON para agentes; serviço único em loopback com porta dinâmica, presença de clientes e encerramento ocioso em 120 s; AGENTS.md e guia DESKTOP_E_AGENTES.md. Autenticação omitida conforme pedido. Não usar mais 8080 fixa para o Studio novo; lançadores existentes abrem a janela. A interface original separada continua em 8080.

Validação: 15 verificações de integração em workspace isolado passaram, incluindo três clientes simultâneos, idempotência, persistência, pausa/cancelamento, continuidade, LOD/download, falha/timeout, UI sob demanda e encerramento. Electron carregou um GLB com WebGL e captura confirmada. Migração preservou 22 modelos, 6 referências, 16 pedidos, relações/avaliações e hashes de artefatos; backup SQLite preservado. Sem inferência nova na galeria real. Evidências desktop-runtime-validation.json, desktop-window-validation.json e desktop-migration-validation.json. Executável local com runtime externo; portabilidade para outra máquina não está implementada.

## 2026-10-04 — Fila atual separada do histórico de pedidos

Interface com duas tabelas: Fila de execução atual inclui todos os executando/aguardando, em execução primeiro e pendentes na ordem de envio; Histórico de pedidos finalizados inclui os últimos 200 concluídos/cancelados/falhos/interrompidos, recentes primeiro. Controle de pausa e cancelamento junto da fila atual; cancelamento atualiza as duas listas imediatamente. Refresh e envios atualizam ambas. Linhas compactas com Modelo/Estado primeiro e ID completo conservado. API de agentes, banco e trabalhos existentes preservados. Verificação de estados, ordenação, cancelamento e callbacks em cópia isolada: local_data/studio/queue-split-validation.json.

Verificação visual desta separação: Electron abriu a fila atual vazia e o histórico em tabela independente, mantendo visualizador GLB funcional. Evidência local_data/studio/queue-split-window-validation.json e .png. Colunas receberam larguras fixas para manter Modelo/Estado legíveis, com Etapa/Erro/ID acessíveis por rolagem horizontal.

## 2026-10-04 — Phanes Studio e atalhos Windows

Nome escolhido pelo usuário aplicado ao executável `desktop/dist/3DStudio/Phanes Studio.exe`, metadados Windows, janela, menu, abertura e cabeçalho da interface. Ícone gerado com image_gen em `desktop/assets/phanes-studio.png`, transparente; ICO com sete tamanhos (16–256 px), incorporado ao executável e usado nos atalhos. Prompt/origem em `desktop/assets/ICON.md`. Lançador `Start-PhanesStudio.bat`; lançadores anteriores atualizados. Atalhos do usuário criados na Área de Trabalho e no Menu Iniciar; reinstalação por `desktop/install-shortcuts.ps1`.

Validação: dois atalhos apontam diretamente para o executável, com pasta de trabalho e ícone corretos; metadados ProductName/FileDescription/OriginalFilename conferidos. Electron abriu a interface Phanes Studio e renderizou um GLB existente com WebGL, encerrando com código 0. Evidências `local_data/studio/phanes-shortcuts-validation.json` e `phanes-window-validation.json`/`.png`. Nenhuma geração/remesh de teste enviada à fila real.

## 2026-10-04 — Ícone minimalista

A pedido do usuário, substituído o ícone detalhado por semente geométrica violeta e centelha dourada central, com formas amplas e espaço negativo. Imagem editada com a ferramenta integrada image_gen; arquivos atuais desktop/assets/phanes-studio-minimal.png e .ico. Primeira versão preservada em phanes-studio.png/.ico. Prompt e origem em desktop/assets/ICON.md.

Aplicado à janela, abertura, executável e atalhos da Área de Trabalho/Menu Iniciar. Ícone dos atalhos usa o novo caminho para evitar reutilização do ícone antigo; Windows notificado para atualizar os atalhos. Empacotamento e sintaxe verificados, ICO transparente com sete tamanhos (16–256 px), hash do recurso empacotado igual ao fonte e ícone nativo extraído do executável conferido. Evidência local_data/studio/phanes-minimal-executable-icon.png e atalhos em phanes-shortcuts-validation.json. Nenhum trabalho de geração/remesh enviado à fila.

## 2026-10-04 — Publicação GitHub e instalação após clonar

Usuário criou https://github.com/vynnyss/Phanes-Studio e autorizou explicitamente a primeira publicação diretamente na main, pois o repositório remoto estava vazio. Raiz inicializada em Git, com origin para esse repositório. README público destaca que Phanes é fork/derivado da integração Windows TRELLIS.2-stableprojectorz de Igor Aherne, baseada no TRELLIS.2 da Microsoft. LICENSE MIT com avisos preservados, THIRD_PARTY_NOTICES e textos de licenças reais incluídos; pesos/dependências não são relicenciados e há termos próprios Meta/BRIA/NVIDIA.

Instalador Install-PhanesStudio.ps1/.bat: pacote v22 verificado por SHA256, Python 3.11 portátil/venv, rotina upstream reaproveitada, downloads de pesos com hashes/revisões, correção EXR e requisitos Studio, npm ci/Electron/meshoptimizer, empacotamento e atalhos. Plan/CheckOnly/SkipModels/OptionalTools/NoShortcuts/BlenderPath documentados em docs/INSTALACAO.md. Blender detectado/configurado localmente em local_data/settings.json; ASSET_BLENDER tem prioridade. Não reinstalar durante uso da fila/janela.

Git exclui runtime, pesos, wheels, node_modules/build, outputs/inputs, banco, logs e configurações/segredos locais. scripts/audit_repository.py verifica conteúdo do índice, limites de tamanho e padrões de credenciais. Conteúdo inicial auditado: cerca de 2,7 MB, 97 arquivos, sem artefatos pesados ou credenciais identificadas. Nove testes de download/extração/configuração passaram; bootstrap PowerShell extraiu fixture segura e recusou caminho externo antes de escrever; sintaxe/Plan/npm ci passaram, meshoptimizer baixado idêntico ao já usado. CheckOnly no ambiente existente confirmou CUDA 12.8/RTX5060, extensões, EXR e modelos. Reinstalação integral em máquina nova não executada; não apresentar como validada.
