# Decisões — 3dGeneratorNew

## D001 — Fork TRELLIS.2-stableprojectorz como base

Aceita pelo usuário em 2026-10-04. Usar a base instalada e testada para expandir a aplicação local. Reutilizar worker/modelos/low-VRAM; não desenvolver outro gerador. v22 é a referência executável validada. Alterações futuras precisam preservar proveniência e ser verificadas, sem presumir equivalência de um upstream novo.

## D002 — Bake no Blender após retopologia/UV

Aceita pelo usuário em 2026-10-04: “usar bake no blender, problema 1 resolvido”. Adotar transferência high→low da aparência gerada, preservando fonte e malha final com UV. Necessidade de texturizador neural externo encerrada para esta expansão. Decisão de workflow aceita; bake efetivo/automático não implementado ou validado neste trabalho.

Alternativa analisada: pipeline neural texture-only oficial com adaptador para preservar UV. Retirado da prioridade; custo e validação extra de memória/UV desnecessários para o caminho escolhido.

## D003 — Fila de imagens em sequência

Escopo confirmado em 2026-10-04. Uma imagem por job/modelo, trabalhos pesados sequenciais, persistência de parâmetros/resultados. Atender vários pedidos sem carregar várias gerações simultâneas na GPU. Persistência/recuperação e detalhes de UI propostos em EXPANSAO_PROJETO.md; implementação pendente.

## D004 — Acesso por agentes

Escopo confirmado em 2026-10-04. Agentes podem preparar referências, enviar à mesma fila e consultar resultados sem depender de clicar na UI. Geração da referência é operação separada, usando ferramenta disponível. Não introduzir prompt textual/router no backend TRELLIS ou inferência concorrente. API/CLI e MCP opcional são recomendação de integração, ainda não implementada.

## D005 — Histórico abre modelo no visualizador 3D

Requisito confirmado em 2026-10-04. Clicar em item do histórico deve abrir diretamente o GLB daquele resultado no visualizador existente, com download correspondente e sem regenerar. Persistência independe de sessão/cache. A distribuição em três áreas e os rótulos em EXPANSAO_PROJETO.md são proposta de interface, não UI já entregue.

## Estado e precedência

Este pedido substitui a recomendação anterior de integrar texture-only neural. Fila/agentes/histórico estão marcados para expansão; este trabalho entrega análise e registro de escopo, sem implementar funcionalidades. Ver [plano da expansão](EXPANSAO_PROJETO.md).

## D006 — Foco em props estáticos

Confirmado pelo usuário em 2026-10-04. Uso pretendido: props sem animação. Prioridades: preservar forma, reduzir polígonos/triângulos e aproveitar o atlas UV para textura. Topologia para deformação não é critério necessário; integridade, shading e bake continuam relevantes.

Simplificação adaptativa + unwrap/packing + bake automático é recomendação analisada em OTIMIZACAO_AUTOMATICA_PROPS.md, ainda não implementada ou validada. Não assumir orçamento universal de triângulos nem menor malha matematicamente possível.

## D007 — Implementação fora do upstream e histórico de versões

Implementado em 2026-10-04. Reusar o worker v22 e Model3D em UI própria, preservando os fontes do mantenedor. API e UI compartilham SQLite e executor sequencial. Cada remesh deriva da versão selecionada: parent_id e asset_id ligam o LOW ao HIGH, sem sobrescrever. Fonte GLB conferida por hash. Uma imagem por geração segue o fork escolhido neste projeto novo; o contrato multiview do projeto antigo 3dGeneratorLocal não foi alterado.

## D008 — Remesh experimental e resultados rastreáveis

Instant Meshes instalado do mantenedor após leitura da licença; QuadriFlow é integrado ao Blender. Voxel só por opção explícita. Falha não cria modelo concluído. O packing proporcional substitui margem fracionária que colapsou UV; cobertura e limites 0–1 são verificados. Materiais originalmente opacos continuam opacos após bake. Qualidade depende de revisão e não recebe aprovação ou nota geral automática. Atualização operacional das decisões D002–D005: integração implementada; limites de validação no guia Studio.

## D009 — Referências reutilizáveis e dois históricos paginados

Pedido explícito do usuário em 2026-10-04: imagens utilizadas abaixo dos modelos, mantendo exemplos anteriores, e paginação em ambos. Escolhidos quatro itens por página com controles independentes; estado da página é por sessão e não muda a seleção do visualizador. Imagens originais copiadas de forma permanente e deduplicadas por conteúdo, não por nome. Clique carrega entrada e não envia pedido; criação continua explícita. Referências de tentativas canceladas/fracassadas também ficam reutilizáveis. Sem mudanças no remesh ou em pesos para esta implementação.

## D010 — Histórico acompanha o pedido iniciado

Pedido explícito em 2026-10-04. Reservar cartão ao iniciar, usando o ID do job que vira ID do resultado. Unir estado do pedido e GLB concluído na galeria, mantendo a API de modelos concluídos separada. Seleção acompanha somente o item escolhido; fases vêm do worker, sem estimativa geral fictícia. Falha não vira modelo concluído. Reutilização da imagem permanece disponível; imagem em execução seleciona o pedido. Ler logs/recursos próprios em vez de alterar o código upstream. Validar controlador com fixtures isoladas para evitar repetir inferências caras do usuário.

## D011 — Recusar perda geométrica e simplificar cópia preparada

Após rejeição real pelo usuário, Instant deixa de ser padrão. Mais polígonos e variantes de campos não recuperaram a estante. Reusar Blender com solda, reparo limitado e Decimate, mantendo UV/bake e referência high. Avaliar métricas antes de gastar no bake e após triangulação, preservando evidência de falha. Aprovação humana separada de completed; resultados rejeitados permanecem rastreáveis. Não escolher remesh por contagem final ou quads; não prometer malha fechada universal. Método validado neste prop, outros precisam de testes.

## D012 — Comparar por métricas e exportar seleção explícita de LODs

Reusar preparo e bake para comparação justa, ajustar somente backend de simplificação. Seleção automática de modo experimental por alvo/p95, aprovação visual exclusivamente humana. Exportar GLBs separados escolhidos pelo usuário/agente, mesma origem, maior tris como LOD0; não inventar distâncias de troca ou integração específica de engine. Destino absoluto escolhido, pacote novo/atomicidade/hashes para preservar existentes. Reestruturação por primitivas adiada.

## 2026-10-04 — Electron com serviço interno compartilhado

Decisão: preservar Gradio e backend atual, com serviço iniciado/reutilizado automaticamente. Eliminação completa de HTTP foi adiada para evitar reconstrução da interface. O cliente estável para agentes abstrai a URL e permite evolução futura do transporte. Sem autenticação nesta etapa, explicitamente solicitado pelo usuário; manter bind somente 127.0.0.1.

Um único executor atende todos os chats e a janela. Agentes não escrevem no banco e podem operar sem Electron/Gradio. O serviço encerra após 120 s ocioso sem cliente ou trabalho executável; fila pausada e histórico persistem. Fechar a janela não cancela inferência. Distribuição inicial reaproveita o ambiente nesta pasta, sem prometer portabilidade do venv ou do Blender.

## 2026-10-04 — Distribuição por fonte e instalação local

Publicar apenas código/ícones/docs/licenças/manifestos; baixar runtime, pesos e dependências após clonar. Versão v22 e hashes/revisões fixados, sem subir pacotes ZIP, binários, outputs ou dados da fila. Código Phanes sob MIT, com crédito explícito Igor Aherne/Microsoft e termos separados para dependências/pesos. Repositório independente com primeira main autorizada pelo usuário; não pressupor vínculo automático ao grafo de forks do GitHub. Instalação nova exige Node/driver NVIDIA/Blender; Python portátil vem do pacote upstream. Caminhos particulares ficam em local_data/settings.json, fora do Git.
