# Resultados — TRELLIS.2-stableprojectorz

Data:2026-10-04. Instalação e pipeline real concluídos na RTX5060 8GB, Windows,16GB RAM. Nenhum AISmith, outro gerador ou treino instalado/executado.

## Testes executados

| Test | Resolution | Time | Peak VRAM | Peak RAM | Vertices | Triangles | Result |
|---|---|---:|---:|---:|---:|---:|---|
| Smoke cadeira | 512 | 8m03.63s | 7.29GiB global | 10.91GiB RSS árvore | 632249 | 980886 | GLB; sem CUDA OOM |
| Prop / teste principal1024 | 1024 | 11m25.65s | 7.25GiB global | 10.67GiB RSS árvore | 210856 | 241263 | GLB; sem CUDA OOM |
| Arma | 1024 | 6m14.79s | 4.34GiB global | 10.45GiB RSS árvore | 168506 | 236991 | GLB; sem CUDA OOM |
| Arquitetura | 1024 | 8m24.10s | 5.29GiB global | 11.04GiB RSS árvore | 209899 | 237989 | GLB; sem CUDA OOM |

Tempos incluem carregamento, pré-processamento, geração, prévia, export e encerramento. A tabela usa pico **observado** de VRAM dedicada global pelo nvidia-smi1s, incluindo outros apps. RSS da árvore soma working sets e pode contar páginas compartilhadas; não equivale à memória privada comprometida. A amostragem pode perder picos breves. Pico exato torch allocated/reserved=null: worker oficial não o expõe. Macroetapas e métricas de sistema estão em report.json/resources.csv.

| Caso1024 | Geração+prévia | Export | Memória privada pico | WDDM dedicada worker | WDDM compartilhada worker | GLB bytes |
|---|---:|---:|---:|---:|---:|---:|
| Prop / teste principal1024 | 438.54s | 88.09s | 38.32GiB | 6.20GiB | 142MiB | 22114384 |
| Arma | 171.31s | 28.47s | 29.57GiB | 3.36GiB | 78MiB | 19963372 |
| Arquitetura | 280.49s | 67.24s | 33.94GiB | 4.09GiB | 78MiB | 19419808 |

WDDM foi medido desde pouco depois da inicialização nos três casos finais; primeiros segundos não cobertos. Valores dedicados/compartilhados são máximos amostrados, não necessariamente simultâneos. A primeira tentativa diagnóstica de1024 teve cobertura somente parcial da inferência. Baseline global de outros aplicativos mudou entre testes; comparar WDDM por processo para reduzir essa interferência.

O offload funcionou, mas utilizou memória virtual intensivamente. Pico privado chegou a38.32GiB; o pagefile **preexistente** em D:/pagefile.sys cresceu automaticamente pelo Windows de31111MiB para37654MiB, com pico de uso observado23922MiB. O agente não mudou a configuração do arquivo de paginação.16GB físicos não são recomendação de margem confortável; o teste dependia de paginação. Leituras em logs/system-memory.json e pagefile-latest.json.

## Reprodutibilidade e parâmetros

Seed0; uma imagem; low_vram=True padrão; SPARSE_DEBUG=0.14steps por estágio. SS:guidance7.5,rescale0.7,T5; Shape:7.5/0.5/T3; Material:1.0/0/T3.1024 usa1024_cascade e res efetiva1024 verificada. Export250000tri,texture2048,remesh do autor; smoke512 usou1Mtri. Todos parâmetros/hashes/input/saídas/tempos em cada report.json. Latentesnpz e PNGs pré-processados preservados.

O exportador oficial limita a casca intermediária de Dual Contouring a512 para conter VRAM; volume/latentes da geração continuam1024, e textura é amostrada do volume completo. Portanto1024 aqui é resolução de geração, não grid1024 no remesh final do GLB.

Código principal: pacote oficial latestv22, SHA25662be7caefaf12e396763dfec4b5e688fdd83c9450920090dfdb8082bd43811be. Checkout auditoria d5d38f1e033a881e2c00e3137822ef8aa4e193de; fonte do pacote não presumida igual ao main. SnapshotsHF: TRELLIS2 af44b45f2e35a493886929c6d786e563ec68364d, TRELLIS-image-large25e0d31ffbebe4b5a97464dd851910efc3002d96. Torch2.8.0+cu128,Python3.11.9,driver610.74,sm120; pip freeze em logs/installed-packages.txt, pip check sem dependências quebradas.

## Inputs e qualidade visual

Smoke:chair.png72x96, original do usuário copiado byte a byte; serve para validar fluxo, não qualidade fina. Casos1024 usam exemplos incluídos pelo mantenedor, sem imagens novas geradas ou alteração de pixels: prop-bottle.webp972x972 (índice38),weapon-pistol.webp982x982 (índice41),architecture-gate.webp1104x1104 (índice32). Índice/nome original em logs/examples-index.txt. Não publicar/usar em treino sem auditoria de direitos.

| Caso | Geometria | Textura | Observações |
|---|---|---|---|
| Garrafa decorativa | Aceitável | Aceitável após alpha | Corpo,tampa e interior presentes. Detalhes/reflexos irregulares e cores internas suavizadas. GLB padrão é opaco; ligação de alpha no Blender revelou peixes/decoração. |
| Pistola fantástica | Boa | Boa | Silhueta,volume,metal,couro e acessórios úteis. Alça/cinta pertence à referência e pode ser removida no cleanup. Simetria e precisão mecânica não certificadas. |
| Treliça/segmento de arquitetura | Boa | Boa | Arco,barras,madeira,trepadeira e flores reconhecíveis; proporções convincentes. Folhagem fragmentada/densa requer cleanup. Não é módulo com medidas/grid garantidos. |

Avaliação qualitativa do agente pelos quatro lados/base_color/clay e renders Blender; não é aprovação humana de dataset nem nota geral numérica. Não houve comparação controlada direta com Meshy/Tripo. Espadas/lâminas muito finas não foram testadas: arma escolhida foi pistola incluída no pacote. Os materiais e detalhes ocultos são inferidos de uma vista; não exigir fidelidade comprovada dos lados não observados.

## Blender e inspeção estrutural

Blender5.2.1 importou os três GLBs. Todos:UV1,dois mapas2048x2048 embutidos/ativos,posições e normais finitas,0faces degeneradas. Escala1 e dimensões normalizadas ~1 unidade no maior eixo; transform de escala é normal no Blender, mas unidade/altura física real não recuperadas da imagem. Renders não mostraram inversão generalizada de normais; irregularidades locais permanecem para cleanup.

| Caso | Vértices após solda diagnóstica | Componentes | Bordas abertas | Arestas não manifold |
|---|---:|---:|---:|---:|
| Prop / teste principal1024 | 118467 | 382 | 80 | 924 |
| Arma | 117872 | 3 | 8 | 414 |
| Arquitetura | 116459 | 305 | 207 | 1975 |

Solda1e-6 executada somente em cópia bmesh para contagem; GLB não alterado. Non-manifold inclui bordas. Peças separadas/folhas podem ser intencionais: contagem não é reprovação automática. Bordas não equivalem diretamente a número de buracos; loops/causa não certificados. Geometria interna da garrafa inspecionada por corte temporário sem tampa de corte; essas bordas artificiais não entram na tabela. Interior completo dos outros dois objetos não certificado. Densidade de~237k-241ktri exige redução/retopo para realtime, mas não inviabiliza a base.

Garrafa: README documenta alpha preservado e GLBOPAQUE. Conferido canalalpha[0,255]; atlas contém pixels de fundo, então fração dealpha<255 não mede transparência da superfície. Em alpha-enabled.blend, TextureAlpha foi ligado ao PrincipledAlpha; imagem melhorou e revelou interior. GLB, posições, índices e UV originais permanecem preservados. Refração física perfeita/transmission não validada. Seams sem ruptura ampla visível nos renders; overlap/distorsão UV não medidos numericamente. Textura utilizável nos opacos, com suavização de detalhes e necessidade de ajustes em vidro.

## Artefatos visuais

### Prop / teste principal1024

![Prop / teste principal1024](../outputs/prop-bottle-1024-default/blender/alpha-enabled.png)

[GLB](../outputs/prop-bottle-1024-default/model.glb) · [Cena Blender](../outputs/prop-bottle-1024-default/blender/inspection.blend) · [Relatório](../outputs/prop-bottle-1024-default/report.json)

### Arma

![Arma](../outputs/weapon-pistol-1024/blender/blender-render.png)

[GLB](../outputs/weapon-pistol-1024/model.glb) · [Cena Blender](../outputs/weapon-pistol-1024/blender/inspection.blend) · [Relatório](../outputs/weapon-pistol-1024/report.json)

### Arquitetura

![Arquitetura](../outputs/architecture-gate-1024/blender/blender-render.png)

[GLB](../outputs/architecture-gate-1024/model.glb) · [Cena Blender](../outputs/architecture-gate-1024/blender/inspection.blend) · [Relatório](../outputs/architecture-gate-1024/report.json)

Garrafa adicional: [original opaco](../outputs/prop-bottle-1024-default/blender/blender-render.png), [vista de corte](../outputs/prop-bottle-1024-default/blender/cutaway.png), [cena com alpha](../outputs/prop-bottle-1024-default/blender/alpha-enabled.blend).

## Falhas preservadas e correções

1. OpenCV5.0 instalado pelo procedimento oficial não tinha OpenEXR; corrigido no venv para opencv-contrib-python4.10.0.84 conforme issue12. Leitura forest.exr512x1024x3 passou. Código do fork inalterado.
2. Primeiro smoke512 gerou/decodificou, mas falhou na prévia: lançador do agente omitia SETUPTOOLS_USE_DISTUTILS=stdlib presente em environment.bat oficial. Corrigido apenas nos helpers; nova tentativa passou.270.45s,RSS10.11GiB,VRAMglobal7490MiB,semOOM; nenhumGLB naquela tentativa.
3. Primeiro1024 foi executado com SPARSE_DEBUG1 adicional para medir logs. Falhou602.20s no assert do tensor vazio temporário durante offload; não foiOOM nem teste do padrão. RestauradoDEBUGFalse do autor,sem edição do core/qualidade;1024 padrão passou. Logs e relatórios das tentativas mantidos em outputs/smoke-chair-512 e outputs/prop-bottle-1024.
4. Helper de API precisou stdoutUTF8 e parser deconfig capaz de chaveJSON vazia; ajustes só nos helpers, sem mudança na interface.

## Interface e limites de validação

Servidor oficial em http://127.0.0.1:8080. HTTP200,configGradio6.0.1 e endpoints confirmados; upload/preprocess via clienteGradio passou (logs/ui-preprocess-report.json). App/worker oficial utilizados. Botões reais:Generate,ExtractGLB,DownloadGLB. Não repetida geração inteira viaUI após os quatro testes do worker.

Automação visual do navegador falhou com trusted Node process exited unexpectedly em duas tentativas. open_in_codex respondeuqueued; abertura/navegação visual não confirmadas. Roteiro manual em README. Este limite não é falha observada do servidor; interface responde e processa uploads pelaAPI.

Pasta ocupa~32.15GiB (34524743177bytes,54467arquivos na captura; inclui pacoteZIP/checkout/modelos/ambiente/outputs). Pagefile adicional do sistema não entra no tamanho da pasta. Runtime e dados ficam no D, fora doGit; projeto antigo continua sem alterações. CachesTorch/Triton/CUDA foram direcionados aoD para usos seguintes; seedcachevirtualenv inicial usou cache preexistente emC, sem instalação/alteração do Python global.

Código/TRELLISMIT não cobre todos os termos de modelos/deps. RMBG2.0 requer termos BRIA não comerciais/acordo comercial; DINOv3 tem licença Meta própria. Auditoria comercial completa continua pendente. Não houve publicação de pesos/referências ou incorporação ao core antigo.
