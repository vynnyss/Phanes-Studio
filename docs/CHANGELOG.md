# Changelog
2026-10-04: implementados diretório isolado, análise, plano, runtime oficialv22, ambiente Python3.11.9 e instrumentos de teste. Validado: hardware, espaço, leitura das fontes/issues/releases e sintaxe do script. Instalação em andamento; inferência e conclusão de substituição comercial ainda não verificadas.

2026-10-04 — validação intermediária: Torch2.8/cu128 executou matmulFP16 na RTX5060/sm120. OpenCV5 não suportava EXR; ajuste mínimo conforme issue12 para opencv-contrib-python4.10.0.84 passou ao ler forest.exr. Geração ainda não executada.

Smoke512 tentativa1: sampling estrutura/forma/material passou, prévia render falhou em conflito distutils. Nosso lançador omitia SETUPTOOLS_USE_DISTUTILS=stdlib presente em tools/environment.bat oficial; adicionado ao teste e lançador. Sem alteração upstream nem redução de qualidade. Log preservado smoke-chair-512.log.


2026-10-04 — Smoke512 validado até GLB. Tentativa1024 com flag diagnósticaSPARSE_DEBUG1 falhou por validação de tensor temporário de offload, sem OOM. Restaurado padrãoDEBUGFalse, sem alterar fonte ou qualidade; nova tentativa em andamento. Flagdebug adicional não prova falha do modo padrão.

2026-10-04 —1024 padrão validado até GLB,685.65s/241263tri/VRAMglobal7429MiB,semOOM. Blender import/material/UV/render validados; várias componentes/bordas exigem cleanup e transparência não fiel. Flag de instalação oficial criada após exit0 e confirmação funcional; evita reinstalar OpenCV5 ao usar run-gradio.bat. Testes arma/arquitetura e veredito final pendentes.

## 2026-10-04 — encerramento da avaliação

Validado: instalação oficial isolada; smoke512 e três casos1024 até GLB sem CUDA OOM; três importações/inspeções/renders no Blender; ajuste de alpha da garrafa em cena separada; servidor e upload/pré-processamento via API. Pico principal1024 observado7429MiB; pico privado38,32GiB, com paginação. Veredito final B, com bases úteis para Blender e encerramento da necessidade de gerador próprio para este objetivo.

Documentação final substitui os estados intermediários acima. Interface visual automatizada, Godot, cleanup/retopo final e auditoria comercial completa permanecem não verificados. Fonte upstream, malhas e UV originais preservadas. Nenhum AISmith, outro gerador, treino ou alteração no projeto antigo.

## 2026-10-04 — análise de customização

Analisados três pontos solicitados: textura em malha retopologizada/UV do Blender; fila de imagens; uso por agentes. Documento stableprojectorz-customization-analysis.md criado e indexado. Inspecionados worker, API FastAPI, exportador e pipeline de textura oficial atual; configuração/encoder de textura já presentes no cache local. Confirmados limites: v22 sem classe texture-only; pré-processamento oficial descarta UV; API recusa concorrentes e multi usa primeira imagem; saída FastAPI global. Propostas de adaptador, bake high→low e fila/API persistentes, sem implementação, novas inferências ou alteração upstream.

## 2026-10-04 — escopo de expansão e interface

Registradas decisões do usuário: fork como base, bake no Blender encerrando necessidade de texture-only, fila sequencial, uso por agentes e histórico que abre GLB no visualizador existente. Criados EXPANSAO_PROJETO.md e DECISOES.md, índice/status/memória atualizados. Validação executada: leitura do app e componentes Gradio6.0.1 instalados; Model3D aceita GLB e Gallery tem evento select. Identificada necessidade de persistência fora da sessão/cache. Interface e features apenas planejadas, sem implementação/inferência ou alterações upstream.

## 2026-10-04 — análise de otimização para props

Usuário definiu foco em props estáticos e prioridades de forma, triângulos e UV. Criado OTIMIZACAO_AUTOMATICA_PROPS.md, indexado e relacionado à expansão. Proposta de simplificação adaptativa/validação multivista, unwrap/packing e bake no Blender; nenhuma redução, ocupação UV ou bake novo validado. Originais/runtime preservados.

## 2026-10-04 — feedback Decimate e alternativas

Usuário informou resultado manual insatisfatório com Decimate, sem diagnóstico reproduzido. Atualizada OTIMIZACAO_AUTOMATICA_PROPS.md com QuadriFlow, Instant Meshes, Quad Remesher, meshoptimizer e reconstrução por primitivas. Ferramenta final depende de teste comparativo; nenhum software instalado ou teste de remesh executado.

## 2026-10-04 — Studio e histórico HIGH/LOW

Implementado: fila persistente, imagens múltiplas, API para agentes, histórico selecionável com vínculo de versões e GLB/download, remesh + UV + cinco bakes via Blender isolado. Lançador principal abre Studio; lançador da UI original preservado. Código upstream intacto.

Validado: dois LOW Instant Meshes reais, hashes originais, GLBs com UV/mapas, callbacks de histórico, download, controles da fila, idempotência e submissão múltipla. QuadriFlow falhou com/sem voxel; diagnóstico preservado. Persistência e reinício conferidos no encerramento deste trabalho.

Não verificado: navegação/render WebGL automatizados (ferramenta de navegador falhou), geração completa pelos novos botões, Godot, mipmaps, qualidade para produção e outros props. Atlas de teste ocupa 26–30%; não declarar maximização UV resolvida.

## 2026-10-04 — Imagens e paginação entregues

Dois históricos paginados de quatro itens, modelos acima e imagens abaixo, navegação independente. Referências de teste e envios anteriores/futuros preservados e deduplicados por SHA256; clique reutiliza como entrada sem gerar automaticamente. Migração reference_images e API GET /api/images, GET /api/images/{id}/file. Modelos, IDs e relações anteriores preservados. Controles, páginas, seleção, download e cópias permanentes validados via cliente/callbacks. Navegação visual automática permanece não verificada por falha da ferramenta. Guia atualizado em STUDIO_UI_E_HISTORICO.md e evidência pagination-validation.json.

Uso por agentes implementado por API HTTP: envio de imagens/remesh, consulta/cancelamento/pausa, idempotência, histórico e downloads. Não há agente próprio que crie a referência e envie automaticamente, nem plugin MCP. Geração completa pelo novo endpoint ainda não repetida. Principais pendências de qualidade: remesh robusto, eficiência UV (26–30% no teste), avaliação bake/mipmaps, outros props e importação no jogo. São limitações conhecidas; não declarar escopo de qualidade encerrado.

## 2026-10-04 — Cartões e acompanhamento ao iniciar

Implementado: espaço no histórico ao iniciar processamento, referência marcada Processando, seleção exibe carregamento/etapa/passos reais e automaticamente abre o GLB concluído do mesmo ID. Download/remesh indisponíveis enquanto processa. Falhas/interrupções visíveis; pendentes sem modelo. Seleção de outro resultado preservada. jobs.started e GET /api/history adicionados; /api/models mantém somente concluídos. Verificado com subprocessos/controladores em workspace isolado e parser de logs, sem fixtures na galeria real. Referência e GLB do usuário front foram preservados após geração real concluída (249721 triângulos). UI visual/WebGL automatizados permanecem não verificados. Ver STUDIO_UI_E_HISTORICO.md e processing-validation.json.

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

## 2026-10-04 — Aplicativo Electron e acesso por agentes

- Janela local e executável em desktop/dist/3DStudio/3D Studio.exe, reaproveitando visualizador, históricos e controles.
- Inicialização segura por demanda, núcleo separado da API/interface e montagem tardia de Gradio no mesmo executor.
- Studio-Agent.cmd/.ps1 e cliente JSON para envio, consulta, remesh, espera, downloads e exportação.
- Porta dinâmica apenas em loopback, bloqueio de inicialização concorrente, presença renovável e encerramento ocioso. Fechar janela/chat conserva os trabalhos.
- AGENTS.md, DESKTOP_E_AGENTES.md, README e API atualizados; autenticação fora do escopo por decisão do usuário.
- Integração isolada, renderização Electron e preservação dos dados reais verificadas. Nenhum benchmark/inferência adicional.

## 2026-10-04 — Duas listas para os pedidos

Separados trabalhos ativos/pendentes de concluídos, cancelados, falhos e interrompidos na coluna da fila. Executando primeiro, aguardando por ordem de envio e finalizados recentes primeiro. Cancelamento renova imediatamente ambas as tabelas. IDs completos conservados, linhas compactas e colunas Modelo/Estado antes do ID. Nenhum trabalho de teste inserido na galeria real.

## 2026-10-04 — Nome e ícone Phanes Studio

Nome Phanes Studio aplicado à janela, interface, menu, abertura e executável com metadados/ícone Windows. Criado ícone transparente de semente cristalina dourada/violeta e ICO multirresolução. Atalhos Phanes Studio instalados na Área de Trabalho e no Menu Iniciar do usuário. Lançadores anteriores permanecem compatíveis; novo Start-PhanesStudio.bat e script para reinstalar atalhos. Abertura e visualizador GLB verificados na janela real.

## 2026-10-04 — Ícone minimalista

A pedido do usuário, substituído o ícone detalhado por semente geométrica violeta e centelha dourada central, com formas amplas e espaço negativo. Imagem editada com a ferramenta integrada image_gen; arquivos atuais desktop/assets/phanes-studio-minimal.png e .ico. Primeira versão preservada em phanes-studio.png/.ico. Prompt e origem em desktop/assets/ICON.md.

Aplicado à janela, abertura, executável e atalhos da Área de Trabalho/Menu Iniciar. Ícone dos atalhos usa o novo caminho para evitar reutilização do ícone antigo; Windows notificado para atualizar os atalhos. Empacotamento e sintaxe verificados, ICO transparente com sete tamanhos (16–256 px), hash do recurso empacotado igual ao fonte e ícone nativo extraído do executável conferido. Evidência local_data/studio/phanes-minimal-executable-icon.png e atalhos em phanes-shortcuts-validation.json. Nenhum trabalho de geração/remesh enviado à fila.

## 2026-10-04 — Publicação GitHub e instalação após clonar

Usuário criou https://github.com/vynnyss/Phanes-Studio e autorizou explicitamente a primeira publicação diretamente na main, pois o repositório remoto estava vazio. Raiz inicializada em Git, com origin para esse repositório. README público destaca que Phanes é fork/derivado da integração Windows TRELLIS.2-stableprojectorz de Igor Aherne, baseada no TRELLIS.2 da Microsoft. LICENSE MIT com avisos preservados, THIRD_PARTY_NOTICES e textos de licenças reais incluídos; pesos/dependências não são relicenciados e há termos próprios Meta/BRIA/NVIDIA.

Instalador Install-PhanesStudio.ps1/.bat: pacote v22 verificado por SHA256, Python 3.11 portátil/venv, rotina upstream reaproveitada, downloads de pesos com hashes/revisões, correção EXR e requisitos Studio, npm ci/Electron/meshoptimizer, empacotamento e atalhos. Plan/CheckOnly/SkipModels/OptionalTools/NoShortcuts/BlenderPath documentados em docs/INSTALACAO.md. Blender detectado/configurado localmente em local_data/settings.json; ASSET_BLENDER tem prioridade. Não reinstalar durante uso da fila/janela.

Git exclui runtime, pesos, wheels, node_modules/build, outputs/inputs, banco, logs e configurações/segredos locais. scripts/audit_repository.py verifica conteúdo do índice, limites de tamanho e padrões de credenciais. Conteúdo inicial auditado: cerca de 2,7 MB, 97 arquivos, sem artefatos pesados ou credenciais identificadas. Nove testes de download/extração/configuração passaram; bootstrap PowerShell extraiu fixture segura e recusou caminho externo antes de escrever; sintaxe/Plan/npm ci passaram, meshoptimizer baixado idêntico ao já usado. CheckOnly no ambiente existente confirmou CUDA 12.8/RTX5060, extensões, EXR e modelos. Reinstalação integral em máquina nova não executada; não apresentar como validada.


2026-10-04: UVgami/OptCuts aprovado explicitamente pelo usuário para a estante front, ciente da demora. Resultado registrado via cliente/serviço como uvgami-89156ba0948e55128a2935232dc3f1ed, LOW aprovado, pai validated-7ed3e3cf2aea5910a834838457896667. Remesh original preservado. Integração independente de unwrap+bake adicionada à UI, fila, API e CLI, com geometria verificada, motor fixado por hash e instalação opcional. Outros resultados começam unreviewed. Guia atual: UVGAMI.md. Alterações locais e PR #1 na branch codex/texture-viewer; main preservada.
