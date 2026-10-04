# Memória — avaliação local StableProjectorz

Estado final em 2026-10-04. Pedido: instalar e testar TRELLIS.2-stableprojectorz low-VRAM em pasta nova D:/Projetos/3dGeneratorNew; não instalar AISmith. Anexo original: C:/Users/vinis/.codex/attachments/a82da4c4-4bbe-415c-86c8-cf3df6b8ff65/Texto colado.txt. Projeto antigo apenas lido e Git conferido, sem alterações.

## Instalação

Pacote oficial latest v22, SHA256 62be7caefaf12e396763dfec4b5e688fdd83c9450920090dfdb8082bd43811be. Checkout auditado em runtime/TRELLIS.2-stableprojectorz, commit d5d38f1e033a881e2c00e3137822ef8aa4e193de; fonte inalterada. Runtime executável runtime/official/code, Python portátil 3.11.9 e code/venv. Instalador original exit 0. Torch 2.8.0+cu128, RTX 5060 sm120, driver 610.74, VRAM 8151 MiB e RAM ~16 GB. pip check, CUDA FP16 e EXR passaram.

Correção mínima no venv: opencv-contrib-python 4.10.0.84 em vez de OpenCV5 headless sem OpenEXR, conforme issue12. Flag trellis2_init_done.txt criada após sucesso para evitar reinstalação. Helpers usam SETUPTOOLS_USE_DISTUTILS=stdlib conforme environment.bat do autor e SPARSE_DEBUG=0 padrão. TEMP/TMP, HF, Torch/Triton/CUDA caches direcionados ao D; seedcache virtualenv inicial usou cache preexistente em C sem alterar Python global.

## Resultado final

Quatro GLBs completos, sem CUDA OOM:
- outputs/smoke-chair-512-retry: 512, 483,63 s, 980886 triângulos.
- outputs/prop-bottle-1024-default: 1024, 685,65 s, 241263 triângulos, VRAM global 7429 MiB.
- outputs/weapon-pistol-1024: 1024, 374,79 s, 236991 triângulos.
- outputs/architecture-gate-1024: 1024, 504,10 s, 237989 triângulos.

Seed 0 e defaults oficiais, low_vram=True, export 250k/texture2048 (smoke usou 1M). Geração efetiva 1024; exportador limita grid intermediário Dual Contouring a 512. Pico privado até 38,32 GiB; pagefile preexistente no D cresceu automaticamente, não houve ajuste manual do sistema. Picos nvidia-smi/WDDM são amostrados; allocator Torch exato não disponível.

Todos os três casos 1024 importados e inspecionados no Blender5.2.1. UV e texturas presentes, escala normalizada editável, posições/normais finitas, zero faces degeneradas. Componentes/bordas/non-manifold exigem revisão. Cenas inspection.blend e renders em outputs/<caso>/blender. Garrafa tem interior confirmado por corte diagnóstico; alpha-enabled.blend/png conecta Texture Alpha ao Principled Alpha conforme README e melhora transparência sem mudar GLB/geometria/UV.

Geometria/textura boas em pistola e arquitetura; aceitáveis na garrafa com ajuste de alpha. Veredito **B — parcialmente substitui serviços pagos**. Malhas úteis para Blender cleanup/retopo, não prontas para realtime. Não houve comparação direta com serviços pagos nem teste de espada fina. Godot/cleanup final não executados. Licenças BRIA RMBG2.0/Meta DINOv3/referências requerem revisão comercial.

## Interface e continuidade

Servidor oficial deixado ativo http://127.0.0.1:8080, launcher PID24920, app PID12616 na captura; conferir processos reais antes de agir. HTTP/config/API e upload/preprocess passaram. Navegação visual não verificada: ferramenta de navegador falhou duas vezes, open_in_codex retornou queued. Nenhuma nova geração completa pela UI após worker. Start-StableProjectorz.bat/.ps1 reiniciam quando servidor encerrado; não duplicar porta/worker.

Falhas iniciais preservadas: smoke sem variável distutils e tentativa1024 com SPARSE_DEBUG1 extra; resolvidas nos helpers/padrão, não por edição do fork nem redução de qualidade. Logs/report de cada tentativa mantidos.

Pasta ~32,15 GiB na captura, não inclui pagefile. Raiz nova não é Git; dependência auditada permanece limpa. Nenhum PR/publicação, treino, AISmith ou outro gerador. Documentos finais em docs, dados/métricas em outputs e logs.

Objetivo técnico concluído para categorias testadas. Considerar encerrada necessidade de desenvolver gerador próprio; próximos trabalhos somente quando solicitados, priorizando TRELLIS → Blender → cleanup/retopo → textura → Godot. Não ampliar benchmark nesta avaliação.

## 2026-10-04 — customização analisada

Usuário pediu análise de três pontos, sem pedir implementação: texture-only após retopologia/UV do Blender, fila sequencial e agentes gerando referências/modelos enquanto trabalha no jogo. Ler docs/stableprojectorz-customization-analysis.md ao retomar.

Achados: backend v22 instalado não é aplicativo StableProjectorz de projeção; aplicativo separado anuncia preservação UV e não foi instalado. Upstream Microsoft já possui Trellis2TexturingPipeline, exemplo e config; configuração/shape encoder (~709MB)/tex decoder (~948MB) presentes no snapshot local, mas classe ausente no v22 e base loader sem config_file. Pipeline oficial run→preprocess_mesh recria Trimesh sem UV; preservar malha/UV/IDs requer cópia para inferência + bake nos UV originais, preferencialmente mapas aplicados ao objeto Blender original. Primeiro caminho prático: bake high→low da aparência já existente. Texture-only neural em8GB não validado.

API FastAPI do pacote (default7960) não iniciada/testada: generate síncrono, concorrente503, multi usa só primeira imagem, download/globaltemp substituível. Worker tem filas IPC sem jobIDs e não deve ter consumidores concorrentes. Proposta: fila persistente/SQLite, diretórios porjob, um executor e bloqueio globalGPU, incluindoUI,CLI,textura/imagemlocal. Agentes enviam/consultam porAPI/CLI, MCPopcional; referências geradas por ferramenta separada, resultado candidato para revisão.

Análise documentada/indexada e logs/customization-texturing-files.json registra arquivos reais. Sem implementação, installs, inferência, subagentes ou mudança de runtime. Ordem recomendada: fila/API→agentes→bakeBlender→prova neuralUV/8GB; não é decisão já implementada. Não confundir pesos disponíveis com funcionalidade instalada.

## 2026-10-04 — expansão confirmada e análise de UI

Usuário escolheu bake no Blender para retopologia/UV e declarou problema1 resolvido; tratar como decisão de workflow encerrada, sem afirmar bake executado. Utilizar fork TRELLIS.2-stableprojectorz como base. Marcar para expansão: fila de várias imagens sequenciais, ajustes para agentes e histórico simples de modelos gerados; clique no modelo deve abrir seu GLB no visualizador3D existente.

Criados docs/EXPANSAO_PROJETO.md e docs/DECISOES.md. Esta decisão substitui prioridade anterior de texture-only neural, fora desta expansão. PropostaUI: entradas/fila à esquerda, Model3D no centro, histórico comminiaturas àdireita, detalhes avançados recolhidos. Galleryselect/Model3DGLB confirmados no Gradio6.0.1 local; app usa préviasHTML e GLB em WalkthroughExtract, saída temporária/session removida emend_session. Histórico exige armazenamento permanente e seleção independente de latentes/currentjob. Não regenerar ao clicar nem trocar seleção quando job acaba.

Somente análise/documentação: nenhuma fila, API de jobs ou histórico implementado, nenhum bake/geração/instalação/serviço novo. Próxima implementação deverá usar o mesmoexecutor paraUI/agentes, persistência antesdaUI, diretórios porjob e cadastro dos4GLBs legados sem alteraroriginais. Ordem sugerida/critériose roteiroplanejados no plano. Não iniciar implementação com base apenas neste registro sem instrução para executar a expansão.

## 2026-10-04 — props e otimização automática

Usuário pretende usar este gerador somente para props sem animação; prioridades são manter forma com poucos polígonos e maximizar área útil doUV paratextura. Não exigir quad topology paradeformação. Skill blender-optimize-game-assets lida/aplicada àanálise e references/blender-lessons.md consultado.

Doc docs/OTIMIZACAO_AUTOMATICA_PROPS.md: recomendação simplificação adaptativa (planar/collapse e primitivas apenas ondeadequado), menores candidatos quepassem métricas individuais, UV apósredução compacking/margens/baixa distorção, bakePBR+normal e variantesraw/optimized. Orçamentos25k/12k/6k/3k sãoexploratórios,não resultados nemdefaults. Normalmapnão preservasilhueta. Nãoapagartinycomponentes/folhagem/interiordagarrafa indiscriminadamente. Não garantir minimomatemático/100%UV.

Somente análise/proposta; nenhumteste emBlender/objeto ativo, bake,redução,instalaçãoouinferência. Requisitodepropsconfirmado; customizaçãoautomaticapendente. FontesoficiaisBlender consultadas,índice/plano/changelog atualizados.

## 2026-10-04 — alternativas ao Decimate

Usuário relatou Decimate manual insatisfatório. Sem modelo/parâmetros/falha específicos; não presumir causa. Análise anterior atualizada em docs/OTIMIZACAO_AUTOMATICA_PROPS.md: comparar QuadriFlow/InstantMeshes gratuitos, QuadRemesher comercial comtrial, meshoptimizer para simplificação porerro e primitivas/perfis empropssimples. Quads nãoimplicammenos tris nemUVmelhor automaticamente. Remeshrequer UV/bake novo; preservarraw. Nenhumteste/install/mutaçãomesh. Não manterDecimatecomo opçãojávalidada nemselecionarbackend semevidência. Bakecontinua decisãoaceita.

## Atualização executável — Studio, 2026-10-04

Fila, API local, histórico HIGH/LOW e remesh + UV + bake implementados. Histórico contém quatro HIGH e dois LOW da pistola, vinculados e com originais preservados. Callbacks de seleção/Model3D, download, relações, controle da fila e submissão de duas imagens testados. Instant Meshes gerou 7919 e 22224 triângulos; QuadriFlow recusou a pistola com e sem voxel. Qualidade/UV automáticos continuam experimentais; UI WebGL visual e geração completa pelos novos botões não verificadas. Guia atual: STUDIO_UI_E_HISTORICO.md; API_STUDIO.md; TESTES_REMESH.md. Evidências: local_data/studio/ e outputs/studio/.

As seções anteriores abaixo registram o estado histórico e são substituídas por esta atualização quanto às funcionalidades novas.

Serviço novo Studio em 8080, iniciado pelo lançador principal. UI original preservada em Start-Original-TRELLIS.ps1; não executar juntas. Sessão Blender do usuário PID27852/Vale_Rig_Animations não foi tocada. Não confundir resultado completed com aprovado para uso no jogo. Continuar pelo guia do Studio, não pelos controles históricos Generate/Extract GLB.

Validação final: 4 HIGH + 2 LOW preservados após reinício; Studio processo21540, lançador5140. Nenhum job pesado ativo ao encerrar. REST upload idempotente concorrente passou; geração desses pedidos de teste cancelada antes da GPU. Tool de browser falhou, não declarar WebGL certificado.

## 2026-10-04 — Imagens e paginação entregues

Dois históricos paginados de quatro itens, modelos acima e imagens abaixo, navegação independente. Referências de teste e envios anteriores/futuros preservados e deduplicados por SHA256; clique reutiliza como entrada sem gerar automaticamente. Migração reference_images e API GET /api/images, GET /api/images/{id}/file. Modelos, IDs e relações anteriores preservados. Controles, páginas, seleção, download e cópias permanentes validados via cliente/callbacks. Navegação visual automática permanece não verificada por falha da ferramenta. Guia atualizado em STUDIO_UI_E_HISTORICO.md e evidência pagination-validation.json.

Uso por agentes implementado por API HTTP: envio de imagens/remesh, consulta/cancelamento/pausa, idempotência, histórico e downloads. Não há agente próprio que crie a referência e envie automaticamente, nem plugin MCP. Geração completa pelo novo endpoint ainda não repetida. Principais pendências de qualidade: remesh robusto, eficiência UV (26–30% no teste), avaliação bake/mipmaps, outros props e importação no jogo. São limitações conhecidas; não declarar escopo de qualidade encerrado.

Validação final da paginação: reinício preservou exatamente os seis modelos e quatro imagens; exemplos originais presentes, nenhum fixture temporário ficou na galeria, estado de pausa restaurado. Studio ativo em 8080, lançador9884. Evidência pagination-validation.json.

## 2026-10-04 — Cartões e acompanhamento ao iniciar

Implementado: espaço no histórico ao iniciar processamento, referência marcada Processando, seleção exibe carregamento/etapa/passos reais e automaticamente abre o GLB concluído do mesmo ID. Download/remesh indisponíveis enquanto processa. Falhas/interrupções visíveis; pendentes sem modelo. Seleção de outro resultado preservada. jobs.started e GET /api/history adicionados; /api/models mantém somente concluídos. Verificado com subprocessos/controladores em workspace isolado e parser de logs, sem fixtures na galeria real. Referência e GLB do usuário front foram preservados após geração real concluída (249721 triângulos). UI visual/WebGL automatizados permanecem não verificados. Ver STUDIO_UI_E_HISTORICO.md e processing-validation.json.

Validação final: resultados existentes e o novo remesh front do usuário preservados após reinício. Histórico sem IDs duplicados; novo remesh real tem started e terminou com GLB. Estado atual de pausa restaurado. Serviço ativo em 8080, lançador28340. Recarregar a UI após a atualização para renovar seus eventos.

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

## 2026-10-04 — Electron e serviço sob demanda entregues

Usuário autorizou executar os cinco pontos recomendados, sem autenticação. Implementados: janela/executável Electron 44.5.1 em desktop/dist/3DStudio/3D Studio.exe; separação studio_service/studio_api/studio_ui/studio_runtime; Studio-Agent.cmd/.ps1 e studio_cli/studio_client; serviço único em porta dinâmica loopback, inicialização coordenada, presença de clientes e saída após 120 s ocioso; AGENTS.md e DESKTOP_E_AGENTES.md. Lançadores antigos agora abrem a janela. Não assumir mais http://127.0.0.1:8080 para o Studio novo.

15 verificações de runtime passaram com worker controlado em workspace isolado. Electron abriu os dois históricos e renderizou GLB real existente; captura/relatório preservados. Migração da instância antiga sem job ativo conservou 22 modelos, 6 referências e 16 pedidos, tabelas idênticas e hashes de modelos/imagens iguais; backup SQLite em logs/desktop-migration-original/studio-before-desktop.db. Preservada configuração da pausa. Nenhuma inferência real adicional. Evidências desktop-runtime-validation.json, desktop-window-validation.json e desktop-migration-validation.json em local_data/studio.

Testes iniciais lançados dentro da sandbox do agente produziram erro de acesso nativo do Electron e popup Windows. Validação final passou ao executar no contexto normal do usuário, mantendo sandbox/contextIsolation do Electron. Permissão RX para ALL APPLICATION PACKAGES preparada somente nos binários da janela. Novo executável deve ser lançado normalmente no Windows. Acesso por agentes confirmado; MCP não instalado, transporte HTTP interno conservado, portabilidade para outras máquinas fora desta entrega.

## 2026-10-04 — Fila e pedidos finalizados separados na UI

Pedido do usuário implementado em studio_ui.py: Fila de execução atual (running/pending), controle de pausa/cancelamento e Histórico de pedidos finalizados (completed/cancelled/failed/interrupted). studio_service.queue_jobs consulta todos os ativos, sem limite; finished_jobs lista últimos 200 por finalização. Running primeiro, pendentes por ordem de envio. Refresh/enqueue/cancel renovam as duas tabelas; linhas sem quebra por caractere, Modelo/Estado primeiro, ID completo ao final. API externa jobs permanece compatível. Verificação em cópia isolada do banco, sem execução GPU nem alteração dos registros reais; evidência queue-split-validation.json.

Verificação visual desta separação: Electron abriu a fila atual vazia e o histórico em tabela independente, mantendo visualizador GLB funcional. Evidência local_data/studio/queue-split-window-validation.json e .png. Colunas receberam larguras fixas para manter Modelo/Estado legíveis, com Etapa/Erro/ID acessíveis por rolagem horizontal.

## 2026-10-04 — Identidade Phanes Studio entregue

Usuário escolheu Phanes Studio e já havia autorizado gerar ícone e criar atalhos após a escolha. Executável atual: `desktop/dist/3DStudio/Phanes Studio.exe`; lançador novo `Start-PhanesStudio.bat`, anteriores encaminham ao novo nome. AppUserModelID `local.phanes.studio`, mesmo userData `local_data/desktop`. Ícone image_gen em `desktop/assets/phanes-studio.png`, transparência preservada; ICO com sete tamanhos (16–256), incorporado via rcedit 5.0.2 (dependência só de empacotamento). Prompt/origem em ICON.md. Atalhos `C:/Users/vinis/Desktop/Phanes Studio.lnk` e `C:/Users/vinis/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Phanes Studio.lnk`, com alvo direto e ícone explícito. Reinstalação por `desktop/install-shortcuts.ps1` no contexto normal do usuário.

Validação: metadados do executável, formato/tamanhos/transparência dos ícones, sintaxe e abertura real Electron passaram. UI mostra Phanes Studio e GLB existente renderizou com WebGL; processo saiu 0. Evidências phanes-shortcuts-validation.json e phanes-window-validation.json/.png em local_data/studio. Identidade do protocolo e caminhos de dados/cliente para agentes conservados, sem trabalhos artificiais na fila real. Não executar Electron dentro da sandbox externa do agente; usar contexto normal do Windows.

## 2026-10-04 — Ícone minimalista

A pedido do usuário, substituído o ícone detalhado por semente geométrica violeta e centelha dourada central, com formas amplas e espaço negativo. Imagem editada com a ferramenta integrada image_gen; arquivos atuais desktop/assets/phanes-studio-minimal.png e .ico. Primeira versão preservada em phanes-studio.png/.ico. Prompt e origem em desktop/assets/ICON.md.

Aplicado à janela, abertura, executável e atalhos da Área de Trabalho/Menu Iniciar. Ícone dos atalhos usa o novo caminho para evitar reutilização do ícone antigo; Windows notificado para atualizar os atalhos. Empacotamento e sintaxe verificados, ICO transparente com sete tamanhos (16–256 px), hash do recurso empacotado igual ao fonte e ícone nativo extraído do executável conferido. Evidência local_data/studio/phanes-minimal-executable-icon.png e atalhos em phanes-shortcuts-validation.json. Nenhum trabalho de geração/remesh enviado à fila.

## 2026-10-04 — Publicação GitHub e instalação após clonar

Usuário criou https://github.com/vynnyss/Phanes-Studio e autorizou explicitamente a primeira publicação diretamente na main, pois o repositório remoto estava vazio. Raiz inicializada em Git, com origin para esse repositório. README público destaca que Phanes é fork/derivado da integração Windows TRELLIS.2-stableprojectorz de Igor Aherne, baseada no TRELLIS.2 da Microsoft. LICENSE MIT com avisos preservados, THIRD_PARTY_NOTICES e textos de licenças reais incluídos; pesos/dependências não são relicenciados e há termos próprios Meta/BRIA/NVIDIA.

Instalador Install-PhanesStudio.ps1/.bat: pacote v22 verificado por SHA256, Python 3.11 portátil/venv, rotina upstream reaproveitada, downloads de pesos com hashes/revisões, correção EXR e requisitos Studio, npm ci/Electron/meshoptimizer, empacotamento e atalhos. Plan/CheckOnly/SkipModels/OptionalTools/NoShortcuts/BlenderPath documentados em docs/INSTALACAO.md. Blender detectado/configurado localmente em local_data/settings.json; ASSET_BLENDER tem prioridade. Não reinstalar durante uso da fila/janela.

Git exclui runtime, pesos, wheels, node_modules/build, outputs/inputs, banco, logs e configurações/segredos locais. scripts/audit_repository.py verifica conteúdo do índice, limites de tamanho e padrões de credenciais. Conteúdo inicial auditado: cerca de 2,7 MB, 97 arquivos, sem artefatos pesados ou credenciais identificadas. Nove testes de download/extração/configuração passaram; bootstrap PowerShell extraiu fixture segura e recusou caminho externo antes de escrever; sintaxe/Plan/npm ci passaram, meshoptimizer baixado idêntico ao já usado. CheckOnly no ambiente existente confirmou CUDA 12.8/RTX5060, extensões, EXR e modelos. Reinstalação integral em máquina nova não executada; não apresentar como validada.
