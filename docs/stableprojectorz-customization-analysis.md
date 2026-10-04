# Análise de customização — textura, fila e agentes

> Atualização de escopo em 2026-10-04: o usuário escolheu bake no Blender e encerrou o problema de textura como decisão de workflow. Integração neural texture-only não integra a expansão atual. Fork como base, fila, agentes e histórico estão confirmados; consulte [EXPANSAO_PROJETO.md](EXPANSAO_PROJETO.md) e [DECISOES.md](DECISOES.md). A análise abaixo fica preservada como referência técnica; sua ordem de implementação anterior foi substituída.

Data: 2026-10-04. Estado: **análise concluída; funcionalidades propostas, não implementadas nem testadas**. Escopo: D:/Projetos/3dGeneratorNew. Sem alteração do runtime, pesos, malhas ou projeto anterior.

## Conclusão

Os três objetivos são viáveis sem desenvolver um gerador próprio. Fila e integração com agentes podem envolver o worker existente. Texturização depois de retopologia/UV exige distinguir transferência da aparência já gerada de geração de uma nova aparência para malha externa.

| Objetivo | Situação atual | Customização indicada | Esforço relativo |
|---|---|---|---|
| Blender retopo/UV → textura | v22 instalado não aceita malha externa para textura | Bake high→low primeiro; adaptador do pipeline oficial de textura para nova aparência | Moderado no bake; maior na integração neural/8 GB |
| Várias imagens → vários GLBs | Uma geração por vez; sem fila durável/biblioteca de jobs | Fila persistente e executor único com resultados por job | Baixo para lote simples; moderado para serviço confiável |
| Agente → imagem → modelo | Worker Python/CLI e API Gradio disponíveis; API FastAPI adicional no pacote | Operações estáveis de enviar/consultar/cancelar/listar resultados | Moderado; depende também do provedor de imagens |

Esforço é comparação qualitativa, não prazo ou benchmark. Não foi instalada nenhuma funcionalidade nova.

## 1. Texturizar depois de retopologia e UV unwrap no Blender

### Distinguir os produtos

O que foi instalado é o **fork TRELLIS.2-stableprojectorz v22**: backend que gera forma e material a partir de uma imagem. A interface em 8080 é Gradio desse backend.

**StableProjectorz**, o aplicativo de projeção/texturização, é separado. Seu site descreve importação de modelos, preservação de UV, projeção multivista e integração com Automatic1111/Forge. Isso permite, em princípio, Blender → malha com UV → StableProjectorz → mapas. Esse aplicativo e seu backend 2D não foram instalados/validados neste trabalho. O botão Re-texture da aplicação só funciona nos geradores que o suportam; não significa que este fork tenha endpoint equivalente.

Fonte: [site do aplicativo](https://stableprojectorz.com/). Os mapas gerados e suas licenças dependem das ferramentas usadas; não tratar nomes semelhantes como a mesma instalação.

### Caminho A — transferir a aparência existente

Para retopologia de uma malha gerada aqui, o caminho mais direto é:

Imagem → TRELLIS com textura → cópia original high-poly → retopologia low-poly + UV no Blender → bake high→low → mapas aplicados à low-poly.

Não é necessário gerar a textura neural novamente para trocar a topologia ou o atlas UV. O bake transfere a aparência da referência high-poly para o UV novo. Podem ser transferidos base color, roughness, metallic e alpha; normal tangent-space requer bake geométrico high→low separado. O TRELLIS atual não produz mapa normal neural independente nesse conjunto de atributos.

Manter as duas versões alinhadas; usar cage/ray distance e separar peças próximas quando necessário. Superfícies finas, interiores e peças próximas podem capturar a superfície errada. Retopologia que muda muito a silhueta reduz fidelidade; bake não inventa os detalhes ausentes.

A transferência pode ser feita pelo Blender sem carregar TRELLIS na GPU. Como alternativa mais elaborada, o volume PBR pode ser amostrado sobre o UV da malha final: nossos latentes estão salvos, mas recuperar o volume exige decode ou persistir esse artefato em gerações futuras. Essa alternativa não é a primeira escolha para uma implementação simples.

### Caminho B — gerar uma nova aparência para a malha final

O TRELLIS.2 oficial disponibiliza Trellis2TexturingPipeline, exemplo próprio e texturing_pipeline.json. Ele recebe malha e imagem, codifica a forma existente e gera atributos de material sem executar nova difusão de geometria.

Na instalação local já existem o config e os pesos do shape encoder (~709 MB) e texture decoder (~948 MB), além dos modelos de fluxo de textura. Tamanhos reais dos links do snapshot conferidos em logs/customization-texturing-files.json. Não é necessário treinar outro modelo.

Mas a classe oficial não está incluída no código v22 instalado. Seu carregador atual aceita só pipeline.json, enquanto o pipeline de textura usa config_file. Copiar apenas um arquivo não resolve automaticamente importação/configuração/compatibilidade com os decoders adaptados do fork.

Há uma sutileza essencial no código oficial consultado:

- postprocess_mesh possui caminho para utilizar UV existente.
- run chama preprocess_mesh antes.
- preprocess_mesh normaliza/rotaciona a geometria e retorna uma nova Trimesh sem copiar visual/UV.
- Portanto, nesse caminho padrão, a UV pode desaparecer antes de chegar ao ramo que a preservaria. Também há conversões de eixo e reconstrução do material.

Não prometer preservação exata de UV, transformações ou IDs de material pelo run padrão. A proposta é usar cópia normalizada só para inferência e realizar o bake nos UV da malha original. Devolver mapas e vinculá-los ao objeto original no Blender, evitando substituir a geometria.

Fontes: [pipeline oficial](https://github.com/microsoft/TRELLIS.2/blob/main/trellis2/pipelines/trellis2_texturing.py), [exemplo](https://github.com/microsoft/TRELLIS.2/blob/main/example_texturing.py), [configuração de pesos](https://huggingface.co/microsoft/TRELLIS.2-4B/blob/main/texturing_pipeline.json). Fontes consultadas na data; main é mutável.

### Contrato recomendado

Entradas: malha final com UV explícita, imagem de referência, seed, resolução de inferência, tamanho de mapas e informação de orientação/transforms. Primeira versão pode limitar explicitamente a um objeto/atlas 0–1; materiais múltiplos, UV sobrepostas, UDIM e várias UV layers precisam de suporte definido ou erro claro.

Saídas: mapas PBR, relatório e cena derivada com os mapas ligados. Preservar posições, índices, UV por canto, IDs de material e transforms do objeto original. Normalização somente numa cópia temporária; nenhuma decimação, remesh ou unwrap automático na malha final.

Mudanças de orientação/escala na edição precisam de correspondência registrada, principalmente no bake high→low. Material metálico/roughness são dados, base color é cor; configurar color spaces corretamente. Transparência deve ser ligada explicitamente e revisada.

### Limite de hardware e validação necessária

Geração image→3D em 1024 passou em 8 GB, mas isso **não é benchmark do shape encoder + texture-only**. O encoder, a voxelização e o bake podem introduzir outros picos. low_vram=True existe no código oficial, mas as adaptações de chunking/offload do fork não estão automaticamente garantidas nesse novo caminho.

Teste proposto, ainda não executado: usar uma malha retopologizada com UV identificável; registrar assinatura antes/depois; começar em 512 e textura 2048; depois medir 1024 sem reduzir qualidade silenciosamente. Conferir mapas, seams, cobertura e invariantes exatas no Blender. Material slots e UV por canto devem ser conferidos, não apenas número de vértices. Um mapa que parece correto não prova preservação da malha.

## 2. Fila de geração de várias imagens

### O que existe e o que falta

PipelineWorker já processa comandos em um subprocesso sequencial. Isso ajuda a reutilizar o backend, mas suas filas de comunicação não são uma fila persistente de trabalhos. Não têm catálogo durável, job IDs nem contrato seguro para vários consumidores: chamadas concorrentes podem consumir respostas umas das outras.

O pacote também traz FastAPI em api_spz/main_api.py, porta padrão 7960. Não está ativo nem foi validado em geração neste trabalho; 8080 é outro serviço. Código inspecionado:

- /generate_no_preview é síncrono: aguarda geração/export.
- Outra chamada durante geração recebe HTTP 503, não é enfileirada.
- /generate_multi_no_preview usa somente a primeira imagem. Não gera vários modelos.
- /status descreve a geração atual/última, sem histórico por job.
- /download/model aponta para arquivo único em temp/current_generation; é necessário preservar o resultado antes de executar o próximo trabalho.
- /interrupt injeta exceção em thread Python. Isso não equivale a cancelamento robusto de kernels CUDA ou recuperação garantida.

### Customização recomendada

Uma camada local separada gerencia a fila e chama o worker do autor, preservando a fonte do backend. SQLite é suficiente para uma primeira fila persistente de um computador; não há necessidade inicial de infraestrutura distribuída.

Cada job guarda identificador, asset_id, imagem original e hash, seed/parâmetros, versões do backend, estados, datas, erros, artefatos e medições. Estados propostos: pending, running, completed, failed e cancelled, com etapa atual separada.

A fila recebe upload múltiplo ou pasta, transforma cada imagem em **um trabalho independente** e mostra ordem, progresso, resultado, pausa e retry. Arquivos precisam estar concluídos antes de entrar: upload encerrado ou rename atômico para pasta de entrada. Não ler imagens parcialmente escritas.

Executar preprocess → geração → salvar latentes/prévias → export GLB → salvar relatório → liberar processo → próximo job. Diretório outputs/<job_id> exclusivo, sem reutilizar model.glb global entre trabalhos. Falha de um job não apaga os outros.

Para começar, subprocesso por job favorece isolamento/liberação de memória; custa recarregamento, aceitável pois tempo não é prioridade. Reutilizar worker aquecido só após teste de várias gerações consecutivas sem crescimento acumulado. Erro CUDA fatal exige reiniciar worker. Retry deve ser limitado e explícito; não usar loop infinito nem reduzir resolução por conta própria.

UI e agentes devem enviar ao mesmo executor. Não iniciar serviço Gradio, FastAPI e CLI independentes carregando modelos ao mesmo tempo na GPU. Limite global de uma tarefa pesada abrange também textura e eventual geração local de imagens. Pausa segura após job/etapa; cancelamento de job ativo precisa tratar encerramento do processo e estado dos artefatos.

Uma rodada de três imagens durou cerca de 26 minutos nos testes anteriores, somando processos completos. É referência observada, não previsão de uma fila quente ou garantia para novas imagens.

### Validação proposta

Três imagens → três job IDs/GLBs → preservação dos resultados. Incluir uma imagem inválida entre duas válidas; erro isolado e fila continua. Reiniciar serviço com pending/running; recuperar pending e marcar interrupted/retry de running sem presumir conclusão. Dois clientes enviando simultaneamente devem manter associação correta de respostas. Confirmar limite global de GPU e ausência de acúmulo entre jobs. Nenhum desses testes de fila foi executado agora.

## 3. Uso por agentes de IA durante o trabalho no jogo

### Viabilidade

Sim. O backend já pode ser chamado sem clicar na interface: PipelineWorker Python, helper CLI e endpoints Gradio. Para uso recorrente por agentes, uma API de jobs acima deles é mais confiável que automação visual ou chamada longa bloqueante.

A geração da imagem é uma etapa separada: o TRELLIS instalado recebe uma imagem; não recebe prompt textual para criar essa referência. O agente usa a ferramenta de imagens disponível, salva o arquivo, depois envia a geração 3D. Isso não requer outro gerador 3D.

Fluxo proposto:

Brief do asset → agente gera imagem → imagem persistida/validada → enqueue → TRELLIS sequencial → GLB + renders + relatório → revisão → Blender → Godot.

Os nomes de operações a seguir são **contrato proposto, não ferramentas implementadas**: submit_job, get_job, list_jobs, cancel_job e get_artifacts. Expor primeiro por API Python/CLI ou HTTP local; um adaptador MCP pode mapear essas operações depois. A fila e seus resultados devem existir independentemente da memória/conversa do agente.

### O que torna isso fácil na prática

- Brief estruturado: nome/categoria, estilo do jogo, descrição visual, tamanho pretendido, orientação e prioridade. A escala física precisa ser aplicada/verificada depois; a imagem não garante metros reais.
- Presets de projeto para seed, resolução, textura, limite de faces e localização dos arquivos. Nenhum agente precisa editar launchers ou conhecer detalhes de modelos.
- Uma referência por asset, com objeto completo, isolado, boa leitura da silhueta e poucos elementos distrativos. Imagem de cena com vários objetos aumenta ambiguidade. Não pressupor frente/lado/costas coerentes de uma referência única.
- Envio retorna job_id rapidamente; agente pode continuar outras tarefas e consultar status quando necessário. Resultados com caminhos/links estáveis e erros claros.
- Deduplicação por chave de pedido/hash/parâmetros evita repetição quando um agente reconecta. Nova variante é job novo, com vínculo ao asset original.
- Limites de quantidade e tentativas configuráveis pelo usuário. Geração em segundo plano precisa de agente/scheduler realmente ativo: a mera existência da API não mantém um agente trabalhando após terminar a conversa.
- Resultado entra como candidato para revisão, sem substituir asset aprovado do jogo nem alegar aprovação artística automática.

Os agentes podem planejar e preparar pedidos simultaneamente; geração pesada na RTX 5060 deve permanecer serial. Se a imagem também for gerada localmente nessa GPU, ela usa o mesmo bloqueio de recursos; se a ferramenta for externa, não ocupa a VRAM local, mas pode ter limites/custos próprios. Trabalhar no jogo continua possível, porém viewport 3D, Blender e Godot podem disputar VRAM/RAM. Oferecer pausa e horários de processamento, em vez de prometer ausência de impacto.

### Exemplo de experiência desejada

Pedido humano: “Preciso de três props de madeira no estilo do jogo: baú, barril e caixa.”

O agente prepara três referências, envia três jobs, recebe IDs e acompanha a conclusão sem manter três gerações concorrentes. A biblioteca mostra referência, seed, vistas, GLB e estado de revisão. Você escolhe quais merecem retopologia. Para uma versão já retopologizada, o job de textura recebe o modelo final e devolve mapas sem recriar a forma.

Esse cenário descreve o produto pretendido. Não foi disparado nenhum agente, gerador de imagens ou lote neste pedido de análise.

## Ordem recomendada

1. **Fila persistente + API/CLI de jobs**, integrada ao mesmo executor usado pela UI.
2. **Presets e contrato para agentes**, aproveitando essa fila; adaptador MCP opcional.
3. **Bake high→low no Blender**, para usar logo as aparências já geradas na topologia final.
4. **Prova pequena de texture-only neural**, com pipeline oficial, UV preservada e benchmark 8 GB. Só então integrar esse modo à fila/UI.

A prova de texture-only pode ser antecipada caso seja prioridade, mas não deve bloquear fila/automação já apoiadas pelo backend testado. Esta ordem é recomendação, não decisão de arquitetura implementada ou autorização nova para instalar serviços.

## Evidências e estado final

Inspeção local: pipeline_worker.py, app.py, api_spz/routes/generation.py, api_spz/core/files_manage.py, models_pydantic.py, state_manage.py, trellis2/pipelines/base.py, trellis2_image_to_3d.py, sparse_unet_vae.py e o-voxel/o_voxel/postprocess.py no pacote v22. O exportador atual simplifica/remeshe e faz unwrap mesmo sem remesh; remesh=False sozinho não preserva UV externa.

Fontes públicas: repositórios oficiais e site do mantenedor, consultados em 2026-10-04. Não depender só do roadmap antigo do README v22: o código de textura separado já existe no upstream. A configuração/pesos de textura já presentes no snapshot local não significam que a classe correspondente esteja instalada.

Sem novas inferências, instalação de modelos/aplicativos, alteração de serviço ou edição upstream. Texturização externa, fila durável, uso simultâneo por agentes e invariantes round-trip ainda precisam de implementação/validação. Os quatro testes de geração anteriores continuam sendo a evidência de image→3D, não desses modos novos.
