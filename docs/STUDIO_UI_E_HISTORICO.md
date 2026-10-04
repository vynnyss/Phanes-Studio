# Studio local: fila, agentes, histórico e remesh

Implementado em 2026-10-04, em D:/Projetos/3dGeneratorNew. Base geradora: runtime oficial v22 instalado do fork TRELLIS.2-stableprojectorz. O código do mantenedor não foi alterado. A nova interface reutiliza Gradio Model3D e o worker do fork; os adaptadores próprios ficam em scripts/.

## Comportamento

O histórico persiste em local_data/studio/studio.db (SQLite WAL). Cada original recebe kind=high e asset_id próprio. Cada remesh concluído recebe kind=low, parent_id apontando à versão selecionada e o mesmo asset_id. HIGH e LOW aparecem juntos, com contagem real de triângulos. Clicar em uma miniatura envia o GLB daquela versão diretamente ao visualizador e ao botão Baixar GLB. Os detalhes identificam a origem do low. Nenhum clique gera ou reprocessa um modelo.

O usuário escolhe a versão a processar. Remesh + UV + bake cria outro item; nunca sobrescreve o high nem um low anterior. É possível selecionar novamente o high para comparar outros orçamentos, ou derivar uma versão de um low. A conclusão de um trabalho atualiza o histórico sem trocar o modelo que o usuário está inspecionando. Resultados inválidos não entram como modelos concluídos; suas tentativas e motivos ficam na fila e nos logs.

Várias imagens são aceitas de uma vez: uma imagem por geração, exportação GLB automática. Uma única fila executa geração ou remesh por vez, em subprocessos separados. A pausa só impede o próximo trabalho; o atual termina. Só pendentes podem ser cancelados. Reiniciar mantém histórico, pendentes e pausa; trabalhos que estavam ativos são marcados interrompidos, sem reiniciar silenciosamente. Um bloqueio de executor impede duas instâncias do Studio compartilhando a mesma fila. Esse bloqueio não coordena testes CLI nem a UI original: não executar esses caminhos enquanto o Studio processa.

## Remesh e bake

Blender 5.2.1 é executado em background com factory-startup; a sessão aberta do usuário não é usada. Fonte GLB preservada e hash conferido. A cópia de preparação solda duplicatas, remove faces exatamente repetidas e recalcula normais. Não apaga componentes nem preenche buracos silenciosamente.

Instant Meshes usa o binário oficial do mantenedor, hash SHA256 f1fe5b5f56d1002ae61dbd76a3fd646229fc1fe15322e7a3744f8ce442c76b2d, com licença em runtime/tools/instant-meshes/LICENSE.txt. O alvo é aproximado; -D evita a subdivisão da saída quad pura. Mesmo com -d, testes deram contagens diferentes; não prometer determinismo exato. Seu winding é preservado: a propagação de normais do Blender travou nessa saída mista durante diagnóstico.

QuadriFlow é o integrado ao Blender, que o usuário já havia testado. Preparação voxel é opcional e explícita; pode alterar furos e detalhes. Não há addon pago instalado. O método pode recusar malhas e a fila apresenta a falha.

A cópia é triangulada e recebe Smart UV Project, média de escala das ilhas e packing no atlas 0–1. Packing com grande margem fracionária colapsou ilhas no teste; foi substituído por margem proporcional. UV fora de 0–1 ou cobertura inferior a 1% impede conclusão. A ocupação é medida por raster a 512; não é certificação exata de ausência de overlap ou maximização matemática. Margem de bake padrão 2 pixels; isolamento de ilhas nos mipmaps ainda requer avaliação.

Bake CPU high→low: base color, roughness, metallic, alpha e normal tangent-space; PNGs, GLB com mapas embutidos e optimized.blend. Fontes opacas permanecem opacas no material final; alpha de uma projeção incompleta não deve criar transparência artificial. Materiais sem Principled são recusados. Vidro e transmissão não estão validados. Relatório contém contagem, bordas, non-manifold, UV, tempos, integridade da fonte e IoU do alpha renderizado em quatro vistas. Essa IoU depende da transparência do material; não equivale a distância geométrica exata.

## Arquivos e configuração

- scripts/studio_app.py: UI e API local.
- scripts/studio_service.py: persistência, fila e subprocessos.
- scripts/blender_asset_worker.py: remesh, UV, bake, comparação e exportação.
- scripts/run_test.py: adaptador de geração oficial, com seed e resolução de textura configuráveis.
- outputs/studio/<job_id>/: model.glb, report.json, worker.log, job-resources.json e derivados.
- local_data/studio/: histórico e evidências de validação. Preservar junto com outputs para manter os arquivos do histórico disponíveis.
- ASSET_BLENDER permite indicar outro executável Blender; a instalação verificada fica em C:/Program Files/Blender Foundation/Blender 5.2/blender.exe. Runtime Python, pesos, caches e Instant Meshes ficam no projeto no D; o Blender é a instalação existente do usuário.

Métricas indisponíveis ficam null com motivo. A medição do Studio amostra RAM do processo e filhos/sistema; geração conserva seu próprio log GPU. Não confundir memória global WDDM com pico atribuível a um modelo. Pesos, runtime, banco e outputs permanecem fora de Git. Esta pasta ainda não é um repositório Git; o checkout upstream de auditoria permanece limpo.

## Roteiro manual para o usuário

Pré-requisitos: instalação preservada, GPU para geração, Blender indicado acima e Instant Meshes instalado. Não iniciar outro worker simultaneamente. Para navegar/remesh CPU não é preciso carregar os modelos geradores.

1. Abrir Start-StableProjectorz.bat na raiz, se não houver serviço, e acessar http://127.0.0.1:8080. Esperado: 3D Studio, Imagens e fila, Modelo 3D e Histórico. Start-Original-TRELLIS.ps1 conserva a UI original, em uso separado, na mesma porta.
2. Em Histórico, clicar HIGH weapon-pistol-1024. Esperado: GLB original no visualizador, título Original / high-poly, 236.991 triângulos e Baixar GLB correspondente. Girar/aproximar e conferir materiais.
3. Clicar em cada LOW da pistola. Esperado: outro arquivo no mesmo visualizador, título Remesh / low-poly, origem identificada e contagem diferente. Os highs continuam no histórico. Existem versões locais com 7.919 e 22.224 triângulos para comparação.
4. Selecionar novamente HIGH e abrir Remesh automático + bake do modelo selecionado. Escolher Instant Meshes, Triângulos desejados 24000 e Atlas de textura 1024; clicar Enviar modelo para remesh + bake. Esperado: pedido na fila, etapas e outro LOW após conclusão. O modelo atualmente aberto permanece selecionado até novo clique.
5. Em Detalhes e métricas, conferir optimized, uv, source_unchanged e render_alpha_iou_by_view. Abrir outputs/studio/<ID>/optimized.blend, PNGs e imagens original-N/optimized-N para examinar bake, ilhas, perdas e shading. Exportar/importar GLB no Blender por File > Import > glTF 2.0.
6. Para diagnosticar QuadriFlow, selecionar HIGH e trocar Método; testar preparação voxel desligada. Na pistola atual, esperado: Falhou, motivo de malha/normais e nenhum LOW falsamente concluído. Os arquivos originais continuam disponíveis.
7. Em Imagens para gerar modelos, adicionar inputs/prop-bottle.webp e inputs/architecture-gate.webp. Configuração da geração: resolução 1024, seed 0, limite 250000, textura 2048. Adicionar imagens à fila cria dois pedidos sequenciais; geração inclui GLB automático. Custos anteriores de geração foram aproximadamente 6–12 minutos por modelo e uso intenso de paginação em 16 GB RAM.
8. Pausar após o atual impede o próximo pedido. Em Cancelar pendente, informar o ID de um pedido aguardando e Cancelar pedido pendente. Continuar retoma os demais. Reiniciar o serviço sem trabalho ativo deve conservar os mesmos HIGH/LOW e links.

## Validação executada e limites

Executados: subprocessos reais Instant Meshes→UV→cinco bakes→GLB, renders em quatro vistas, leitura dos GLBs finais com UV finita e três imagens embutidas (GLB combina canais), conferência do hash original; callbacks reais de carregamento/seleção e Model3D, download exato de high/low, relações parent_id/asset_id, pausa/cancelamento, chave idempotente e erro de parâmetros. Cliente oficial Gradio enviou duas imagens pela mesma função da UI; ambos os pedidos foram cancelados antes da GPU. Geração completa pela UI nova não foi repetida; as quatro gerações prévias validaram o mesmo worker do fork. Evidências em local_data/studio/validation.json, glb-roundtrip-validation.json e logs/history-api-validation.log.

Navegação visual automatizada não verificada: a ferramenta de navegador encerrou seu processo interno. O teste dos callbacks não certifica o render WebGL no navegador. Importação no jogo, mipmaps, aprovação de qualidade pelo usuário e auditoria comercial completa permanecem pendentes. A integração funciona, mas a qualidade automática do remesh/UV ainda é experimental; não marcar o escopo inicial como aprovado para produção.

Validação final: reinício preservou exatamente os seis registros e seus vínculos; captions mostram triângulos reais. Dois uploads REST simultâneos com a mesma chave criaram apenas um pedido, com nome original chair, cancelado antes da GPU. Serviço deixado ativo em 8080.

## Histórico de imagens e paginação — 2026-10-04

Implementado: Histórico de imagens utilizadas fica imediatamente abaixo do histórico de modelos, na mesma coluna. Ambos têm quatro itens por página, Anterior/Próxima próprios e contador Página N de M. A navegação é independente por sessão. O refresh conserva a página e o modelo aberto; não recoloca a primeira página a cada atualização. Ao chegar ao limite os botões são desativados; páginas fora dos limites são ajustadas. Após recarregar a aplicação, páginas voltam a 1, mas os registros persistem.

Imagens de inputs/ (incluindo os quatro exemplos anteriores), referências dos HIGH e imagens enviadas à fila são cadastradas. Referências enviadas que acabaram canceladas/falharam também permanecem disponíveis para reutilização; não interpretar esse histórico como prova de geração concluída. Cada conteúdo exato tem um ID SHA256 e uma cópia permanente em local_data/studio/images/. Reenvio dos mesmos bytes atualiza o último uso, sem duplicar a miniatura. Formatos PNG/JPEG/WebP são aceitos pela API de geração. Imagens diferentes com nomes iguais continuam distintas. As referências mantêm nome legível ao serem reenviadas do histórico.

Um clique em uma imagem carrega essa referência em Imagens para gerar modelos e mostra uma mensagem. Substitui a seleção de arquivos atual por essa imagem; não dispara geração nem modifica o modelo selecionado. O usuário ainda precisa clicar Adicionar imagens à fila. Modelos continuam selecionáveis para remesh independentemente da imagem de entrada.

Persistência: nova tabela reference_images no mesmo banco, sem alterar IDs, relações ou GLBs existentes. Migração automática ao iniciar a aplicação. API GET /api/images lista os registros; GET /api/images/{id}/file retorna a cópia preservada, com verificação de caminho. Os endpoints anteriores continuam compatíveis. Não introduz dependência nova ou serviço de IA.

Roteiro manual adicional:

1. Recarregar http://127.0.0.1:8080. Conferir dois históricos na coluna direita, modelos acima e imagens abaixo. Esperado: seis modelos distribuídos em duas páginas e os exemplos chair, prop-bottle, weapon-pistol e architecture-gate nas imagens.
2. Em modelos, clicar Próxima e selecionar um HIGH. Esperado: o GLB escolhido no visualizador; a página das imagens não muda. Voltar por Anterior; o modelo aberto permanece até outro clique.
3. Em imagens, clicar numa referência. Esperado: arquivo carregado à esquerda e mensagem de reutilização, sem novo pedido de geração. Adicionar à fila é uma ação posterior explícita.
4. Quando houver mais de quatro referências distintas, clicar Próxima nas imagens. Esperado: outras referências, contador atualizado, sem mudar a página dos modelos. Ao reenviar exatamente a mesma imagem, não deve aparecer um segundo item.
5. Reiniciar sem trabalho ativo e conferir persistência dos dois históricos. Inspecionar local_data/studio/images/ e studio.db, sem editar o banco manualmente.

Validação executada: cliente Gradio real percorreu primeira/segunda/última páginas e retorno nos dois históricos; estados independentes e refresh preservados. Callbacks reais mapearam o índice local da segunda página ao ID e GLB corretos, e a referência ao arquivo de entrada correto. Cópia permanente e download HTTP foram comparados byte a byte; duplicação por SHA foi verificada. Referências temporárias de teste foram removidas ao terminar, sem gerar modelos. Evidências em local_data/studio/pagination-validation.json e logs/pagination-validation.log. A ferramenta de navegador voltou a falhar internamente; não declarar conferência visual/WebGL automatizada.

Persistência final validada após reinício: seis modelos e quatro referências de teste preservados exatamente, com o estado original de pausa restaurado. Fixtures usados para exercitar a segunda página de imagens foram removidos.

## Cartões durante processamento — 2026-10-04

Implementado a pedido do usuário: ao iniciar um trabalho, ele reserva um item no histórico de modelos, usando a referência como miniatura e o rótulo Processando. A referência já permanece no histórico de imagens desde o envio e recebe o mesmo rótulo durante a geração. Clique no cartão do trabalho, ou na referência marcada Processando, acompanha esse pedido no centro. Não inicia outra geração.

O visualizador fica reservado para um painel com indicador animado, etapa atual e passos locais quando disponíveis. Model3D e download ficam ocultos, e remesh desativado, até haver GLB concluído. Ao completar, o mesmo ID e posição lógica de histórico passam a apontar ao GLB; se aquele item estiver selecionado, ele abre automaticamente. Não é preciso clicar de novo. Conclusão de outros jobs não muda a seleção atual nem recarrega o modelo aberto a cada atualização.

Falhas e interrupções de trabalhos iniciados permanecem como cartões de diagnóstico; ao clicar, aparece o motivo sem GLB fictício ou spinner infinito. Pendentes/cancelados antes de iniciar continuam apenas na fila, sem reservar modelo. O contador da galeria usa itens porque inclui trabalhos iniciados e tentativas falhas, enquanto GET /api/models continua listando somente modelos concluídos.

Backend: coluna jobs.started, gravada ao iniciar, e projeção history_entries que une versões concluídas e jobs iniciados sem duplicar IDs. O timestamp do início conserva a posição quando conclui. Migração atribui created como aproximação de início aos registros históricos que já tinham executado; não usar esse valor reconstruído como medição de duração. GET /api/history expõe os itens e estados. Nenhuma malha ou referência anterior é reescrita.

Etapas são lidas de progress.json do remesh e de resources.csv/worker.log da geração. Sampling informa passos reais, por exemplo 7 de 14 apenas na etapa de geometria; não há percentual total ou prazo inventado. Etapas traduzidas incluem preparação, estrutura, geometria, texturas, exportação, remesh, UV, bakes e comparação. studio_progress.py não modifica o fork nem pesos. O polling é de três segundos e não mostra o loading genérico do Gradio sobre modelos concluídos.

Roteiro manual adicional:

1. Recarregar a UI após atualizar o serviço. Selecionar uma imagem e Adicionar imagens à fila. Esperado: na fila enquanto aguarda; ao iniciar, cartão Processando no histórico de modelos e marca na imagem.
2. Clicar nesse cartão. Esperado: nome, indicador animado, etapa atual e passos quando informados. Download e remesh indisponíveis durante processamento.
3. Aguardar a conclusão mantendo a seleção. Esperado: mesmo cartão torna-se HIGH/LOW e o GLB abre automaticamente; download/remesh são liberados. O arquivo está em outputs/studio/<job_id>/model.glb.
4. Durante outro pedido, abrir um modelo já concluído. Esperado: ele permanece aberto, mesmo quando o pedido novo termina. Página dos históricos continua independente.
5. Para um teste de falha reproduzível, enviar o HIGH da pistola para QuadriFlow sem voxel. Esperado: cartão Falhou e motivo, sem download de modelo concluído. O HIGH original permanece intacto.

Validação executada: controle de ciclo real do Studio com subprocessos de fixture em banco/workspace isolados, sem novas gerações ou itens falsos no histórico do usuário. Verificados pendente oculto, item ao iniciar, seleção por imagem e por modelo, spinner/ações desativadas, etapas, mesmo ID→GLB automático, falha visível e preservação da seleção de outro resultado. Parser também verificou passagem de Sampling para exportação, sem manter passos antigos. Evidência processing-validation.json e logs/processing-validation.log. A geração real do usuário front concluiu na fila com 249721 triângulos, seed 0; não foi interrompida para atualizar o serviço. Conferência visual automatizada do navegador/WebGL ainda indisponível; fixtures validam controle, não qualidade de inferência ou render visual.

Validação final: resultados existentes e o novo remesh front do usuário preservados após reinício. Histórico sem IDs duplicados; novo remesh real tem started e terminou com GLB. Estado atual de pausa restaurado. Serviço ativo em 8080, lançador28340. Recarregar a UI após a atualização para renovar seus eventos.

## 2026-10-04 — Correção após rejeição da estante pelo usuário

Os dois LOW Instant Meshes de front (8.342 e 6.953 triângulos) foram rejeitados pelo usuário por deformação e buracos. Finalização operacional anterior não era aprovação de qualidade. Continuam preservados, agora com quality_status=rejected e motivo; visualização/download para diagnóstico permanecem disponíveis, mas derivar outro remesh desses resultados é bloqueado. O HIGH original permanece intacto por conferência SHA256.

A comparação antes do bake confirmou perda geométrica: comprimento de bordas abertas 0,613 no HIGH preparado contra 42,76/43,82 nos LOW. Variantes Instant Meshes com aproximadamente 9,4 mil, 9,9 mil e 35 mil triângulos também falharam; aumentar polígonos não solucionou este caso. Preparação voxel + Instant igualmente insatisfatória.

Novo método padrão: Simplificação (Decimate preparado), código simplify. Solda uma cópia para remover fragmentação por UV/material, preenche somente pequenos loops fechados com até 8 vértices e perímetro <=2,5% da maior dimensão, simplifica, cria UV e faz bake PBR. Nenhuma alteração no original. Não inferir que o teste manual anterior do usuário usou a mesma preparação.

Validação geométrica em blender_geometry_quality.py rejeita o resultado antes do bake e verifica novamente antes da exportação: comprimento de bordas <=1,25 vezes o original +2% da diagonal; distância amostrada bidirecional em 2.000 pontos por direção, p95 <=1% e máximo amostrado <=5% da diagonal. Métricas individuais no report.json, sem nota geral. São limites experimentais: amostragem não certifica toda topologia, detalhes ocultos ou qualidade no jogo. Imperfeições já existentes podem permanecer.

Teste real completo: outputs/remesh-diagnosis/front/simplify-baked/model.glb, 11.993 triângulos após exportação, bake e quatro vistas, reimportação GLB confirmada e hash do original preservado. Candidato inserido no histórico como front · simplificação preparada 12 mil, ainda unreviewed. Silhuetas renderizadas IoU 0,9990–0,9994; UV ocupa 29,69%, portanto packing eficiente continua pendente. Teste negativo real outputs/remesh-diagnosis/front/instant-quality-guard/report.json terminou failed e não exportou GLB.

Roteiro manual: se necessário iniciar Start-StableProjectorz.bat, abrir http://127.0.0.1:8080 e recarregar a página após atualização. No Histórico · high e low-poly, selecionar front HIGH (249.721 triângulos). Abrir Remesh automático + bake do modelo selecionado, escolher Simplificação (Decimate preparado), Triângulos desejados 12000 e Atlas de textura 1024. Clicar Enviar modelo para remesh + bake. Selecionar cartão Processando para acompanhar; sucesso cria um LOW vinculado, sem substituir HIGH. Falha mostra motivo e não cria GLB concluído. Para avaliar o teste já realizado, selecionar front · simplificação preparada 12 mil, girar no visualizador e comparar com HIGH; conferir Detalhes e métricas e o report.json acima. Os dois LOW antigos aparecem como Rejeitado. Importação no jogo e aprovação visual do usuário continuam pendentes; WebGL automatizado não verificado por indisponibilidade da ferramenta de navegador.

[Comparação Decimate/meshoptimizer e exportação de LODs](COMPARACAO_REMESH_E_LODS.md): candidatos reais e roteiro de review/exportação pela UI/API.

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

## 2026-10-04 — Números visíveis no carregamento inicial

Correção implementada e validada em serviço ativo: os botões numerados recebem valor, visibilidade, disponibilidade e variante da página 1 na construção da UI, antes do evento de carregamento. Antes, eram criados vazios e preenchidos somente pelos callbacks, permitindo o estado relatado pelo usuário após F5. O clique agora usa o estado da página e a posição do botão, sem usar o próprio botão como entrada; evita dependência de seu rótulo durante a inicialização. A mesma função de propriedades atende a construção e as atualizações. Mantidos tema escuro/laranja, 8 modelos e 4 imagens por página, históricos independentes e reticências.

Validação executada: configuração inicial HTTP antes de qualquer load/clique contém modelos 1/2/3 e imagens 1/2, com 1 primary em ambas; duas novas sessões começam na página 1. Cliente Gradio real abriu modelos página 3 e imagens página 2 diretamente, retornou por Anterior e botão 1 e executou refresh. Atualização sem mudança preserva os botões. Verificados limites e reticências com até 100 páginas. IDs dos 24 itens de modelos e 6 referências preservados, sem geração ou remesh. Serviço reiniciado sem job ativo; estado anterior da fila restaurado ativo. Evidência: local_data/studio/numbered-pagination-initialization-validation.json. Conferência visual automatizada permanece não verificada por indisponibilidade da ferramenta de navegador.

Roteiro manual:

1. Pré-requisito: Studio atualizado; executar Start-StableProjectorz.bat somente se o serviço estiver parado. Abrir http://127.0.0.1:8080.
2. Pressionar F5. Antes de clicar em Anterior/Próxima, conferir os números abaixo de Histórico · high e low-poly e Histórico de imagens utilizadas. Página 1 deve aparecer laranja nas duas barras, com Anterior desativado.
3. Clicar 3 nos modelos: esperado Página 3 de 3 e número 3 destacado. Clicar 2 nas imagens: esperado Página 2 de 2, mantendo a página dos modelos. Valores refletem os dados atuais e podem aumentar com novas gerações.
4. Aguardar uma atualização automática; números permanecem. Pressionar F5 novamente: ambas retornam à página 1 com números visíveis imediatamente.
5. Conferir evidência em local_data/studio/numbered-pagination-initialization-validation.json; navegar não cria arquivos de modelos em outputs/ nem modifica as referências existentes.
