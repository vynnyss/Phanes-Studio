# Otimização automática de props — redução, UV e bake

## Atualização executável — Studio, 2026-10-04

Fila, API local, histórico HIGH/LOW e remesh + UV + bake implementados. Histórico contém quatro HIGH e dois LOW da pistola, vinculados e com originais preservados. Callbacks de seleção/Model3D, download, relações, controle da fila e submissão de duas imagens testados. Instant Meshes gerou 7919 e 22224 triângulos; QuadriFlow recusou a pistola com e sem voxel. Qualidade/UV automáticos continuam experimentais; UI WebGL visual e geração completa pelos novos botões não verificadas. Guia atual: STUDIO_UI_E_HISTORICO.md; API_STUDIO.md; TESTES_REMESH.md. Evidências: local_data/studio/ e outputs/studio/.

As seções anteriores abaixo registram o estado histórico e são substituídas por esta atualização quanto às funcionalidades novas.


Data: 2026-10-04. **Análise/proposta, sem implementação ou teste de redução/bake nesta etapa.**

## Objetivo confirmado

Uso do TRELLIS.2-stableprojectorz para props estáticos. O usuário prioriza preservar forma com poucos polígonos e aproveitar o atlas UV; não precisa de topologia voltada a deformação/animação. Bake no Blender já é o workflow adotado.

Recomendação: simplificação geométrica adaptativa + UV automático + bake high→low no Blender. Quads regulares ou retopologia neural não são requisitos. A malha pode ser triangulada e irregular desde que forma, shading, UV e desempenho sejam adequados.

Não existe promessa de mínimo matemático. O que se pode selecionar é a menor variante testada que passe critérios explícitos, na distância de uso pretendida.

## Fluxo proposto

TRELLIS → fonte original preservada → cópia de trabalho → cleanup conservador → redução adaptativa → UV final → triangulação/normais finais → bake → GLB otimizado + BLEND + mapas + relatório.

Cada etapa deve usar variantes, sem sobrescrever o GLB bruto. O UV novo é criado na cópia otimizada antes do bake; depois de aprovado, fica congelado durante transferência de textura. Não confundir isso com o contrato texture-only, que preserva o UV de um modelo já finalizado.

### Redução de geometria

1. Registrar contagem de triângulos reais, dimensões, componentes, materiais e regiões finas/importantes.
2. Remover geometria degenerada/duplicada somente quando comprovadamente redundante. Não soldar através de costuras/materials ou apagar componentes pequenos indiscriminadamente.
3. Simplificar superfícies quase planas com dissolução/Decimate Planar, preservando bordas importantes.
4. Usar Decimate Collapse para redução geral, com proteção/peso em regiões relevantes quando necessário.
5. Testar candidatos progressivamente mais leves, sempre derivados da mesma fonte para comparação.
6. Selecionar a menor variante que passe todas as verificações; refinar o intervalo próximo ao limite se compensar.

Para caixas, paredes e perfis simples, uma reconstrução com primitivas/perfis ajustados pode superar decimação em eficiência. Automação desse reconhecimento deve ser limitada a formas detectadas com confiança e verificada contra a fonte. Não substituir arco por caixa fechada, por exemplo. Não é a primeira implementação necessária para todos os props.

Não usar voxel remesh/quad remesh como etapa universal: cria outro problema de reconstrução de superfície e pode fechar aberturas ou perder folhas/partes finas. Também não assumir que n-gons reduzem custo: a engine triangula, e a contagem relevante é a exportada.

Fontes: [Decimate](https://docs.blender.org/manual/en/4.3/modeling/modifiers/generate/decimate.html). Procedimentos de primitivas, conservação e bake: skill blender-optimize-game-assets.

### Preservação da forma

Comparar original e candidatos com mesmas câmeras, transforms e enquadramento. Métricas separadas, sem nota geral arbitrária:

- Silhueta por vista: interseção/união e deslocamento do contorno em pixels.
- Distância de superfície bidirecional amostrada, relativa ao tamanho do objeto.
- Profundidade e normais quando disponíveis, para detectar achatamento de relevos/espessura.
- Dimensões e características críticas: aberturas, pontas, anéis, alças, bordas.
- Integridade: faces degeneradas, inversões, componentes perdidos e novos problemas estruturais.

Amostragem não prova preservação exata de toda a superfície. Critérios dependem do uso: uma caixa vista longe tolera redução diferente de uma peça de inventário vista de perto. Normal map recupera aparência de detalhes, mas não corrige silhueta perdida ou abertura fechada.

Não basta comparar uma vista frontal. Incluir laterais, costas, cima/baixo e diagonais; revisão visual permanece necessária para casos ambíguos. Se não houver candidato válido no orçamento, entregar o mais conservador com aviso e encaminhar para revisão, sem declarar sucesso artificial.

### Aplicação aos exemplos existentes

Pistola: 236991 triângulos; arquitetura: 237989; garrafa: 241263. São baselines brutos, não resultados de otimização.

Possíveis orçamentos exploratórios, **não metas validadas/defaults**: 25000, 12000, 6000 e 3000 triângulos, refinando conforme a perda medida. Nenhuma redução a esses valores foi executada nesta análise.

- Pistola: corpo, alça, ponta e acessórios precisam de proteção; relevos menores podem ir para normal map.
- Arquitetura: madeira plana pode reduzir bastante, mas folhagem e vãos precisam de tratamento separado. A fonte tem 305 componentes após solda diagnóstica; isso não significa 305 defeitos.
- Garrafa: preservar casca, espessura relevante, tampa e interior visível por transparência. Remover interiores por estarem ocultos num render opaco seria incorreto.

## UV automático com boa ocupação

Gerar UV depois da redução. Não insistir em preservar o atlas original do high-poly: ele é fonte do bake, enquanto a low-poly recebe novo atlas.

### Unwrap

Para hard-surface, Smart UV Project é um ponto de partida; para partes curvas/orgânicas, seams e unwrap por ângulo/conformal podem produzir ilhas melhores. Testar poucos parâmetros de separação e comparar distorção e fragmentação.

Ângulo baixo tende a produzir muitas ilhas com pouca distorção; alto reduz cortes, mas pode aumentar distorção. O objetivo é encontrar equilíbrio, não simplesmente minimizar número de ilhas. Evitar uma ilha por triângulo como solução padrão para textura.

Fonte: [UV Operators](https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/uv.html).

### Packing

Normalizar densidade de texel conforme área da superfície e empacotar no atlas 0–1, com rotação e consideração da forma exata das ilhas. Pack Islands do Blender já fornece um caminho inicial; não exige plugin pago.

Maximizar área útil **sob restrições**: sem sobreposições indevidas, sem UV fora do atlas, com margem para bake/mipmaps e distorção controlada. Não buscar 100% de ocupação sacrificando todas as margens. Muitas ilhas pequenas consomem espaço com padding; reduzir fragmentação pode ajudar mais que apenas usar outro packer.

Não esticar ilhas apenas para preencher buracos. Não sobrepor faces diferentes para inflar ocupação. Espelhamento/stacking de superfícies realmente equivalentes pode ser opção posterior, se aparência idêntica for desejada; pode destruir assimetrias da textura e não deve ser padrão no bake de uma referência gerada.

Começar com atlas por asset. Atlas compartilhado entre vários props é outra decisão, com densidade/materials/revisão próprios; não presumir que seja necessário para atender o pedido.

Fonte: [Pack Islands](https://docs.blender.org/manual/en/4.2/modeling/meshes/uv/editing.html).

### Medições UV

Relatório proposto: ocupação de texels cobertos pela superfície (sem contar padding como textura útil), sobreposição de interiores, ilhas fora de 0–1, quantidade/tamanho de ilhas, distorção e variação de densidade de texel.

Máscara raster é aproximação dependente da resolução; não prova inexistência de overlaps subpixel. Teste geométrico de interseção UV é uma verificação complementar. Nenhuma ocupação foi medida agora, portanto valores atuais são indisponíveis, não zero.

Margens devem ser definidas em pixels em função da resolução e mipmaps esperados; ajustar ao operador real, pois “margin” pode representar distância entre ilhas ou margem por ilha. Conferir visualmente/numericamente em vez de assumir equivalência entre parâmetros de unwrap, packing e bake.

## Bake e exportação

Transferir base color, roughness, metallic e alpha presentes na fonte. Um bake somente de cor não substitui os outros canais. Base color deve evitar adicionar iluminação; dados de material usam configuração de cor adequada. Normal tangent-space high→low é complemento importante para conservar detalhe visual removido da geometria.

Manter high/low alinhados, limitar raios/cage e isolar peças próximas para evitar transferência cruzada. Furos, folhas, alças e transparência são casos delicados. Não preencher automaticamente pixels pretos sem distinguir aparência original de falha de cobertura.

Triangulação e shading finais devem estar definidos antes do normal bake e ser os mesmos usados na exportação. Salvar raw/optimized como versões distintas. Reimportar GLB e conferir mapas/UV/normais; futura inspeção em Godot também necessária.

Fonte: [Render Baking](https://docs.blender.org/manual/th/4.5/render/cycles/baking.html).

## Integração simples à aplicação

Proposta de opção “Otimizar para jogo”, com dois controles principais:

- Preservação da forma: Conservadora / Equilibrada / Agressiva, traduzida em tolerâncias documentadas após validação.
- Tamanho da textura: resolução do atlas de saída.

Orçamento máximo de triângulos pode ficar em detalhes avançados. Não forçar orçamento que destrói forma sem avisar. Primeiro gerar/preservar o raw; otimização é estágio separado e pode falhar sem perder o modelo bruto.

No histórico, variantes Original e Otimizado do mesmo asset abrem diretamente no visualizador, com download correspondente e resumo antes/depois. Não criar cópias indistinguíveis ou substituir o original silenciosamente.

Fila trata otimização e bake sequencialmente, depois de liberar processo/modelo TRELLIS. Blender pode ser executado isoladamente em background com script; isso evita depender de cliques e atende agentes pela mesma API de jobs. Fase CPU inicial pode ajudar a evitar disputa de VRAM, mas tempo/memória precisam ser medidos; não prometer pico baixo sem teste.

## Prova de conceito recomendada

Somente quando houver pedido de implementação/teste:

1. Preservar hashes das fontes e importar cópias em Blender isolado.
2. Começar pela pistola, depois incluir arquitetura e garrafa como casos delicados.
3. Comparar poucos candidatos de redução; selecionar por critérios individuais de forma.
4. Testar unwrap/packing e registrar métricas UV, não apenas um render bonito.
5. Bake completo, salvar BLEND/PNG/GLB e reimportar.
6. Renderizar original/otimizado com câmeras iguais e verificar perto/longe.
7. Conferir triângulos finais, bytes dos mapas, tempo e recursos por etapa.
8. Só após os resultados definir defaults dos presets e integrar opção à fila/histórico.

Estado: nenhum objeto foi alterado, nenhuma inferência ou bake foi executado, nenhum software adicional instalado. Esta análise propõe automação para o requisito de props; o plano anterior ainda não contém a implementação desse estágio.

Relacionados: [expansão](EXPANSAO_PROJETO.md), [decisões](DECISOES.md), [resultados](stableprojectorz-results.md).

## Atualização — alternativas após teste manual do usuário

2026-10-04. O usuário informou resultado insatisfatório com Decimate. Isso é evidência de avaliação humana, sem arquivo, parâmetros ou tipo de falha identificados nesta conversa. Não marcar nossa proposta de Decimate como validada nem atribuir a causa a UV, normais ou geometria sem inspeção.

A recomendação passa a comparar reconstrução de topologia com simplificação por erro:

- **QuadriFlow no Blender**: candidato gratuito já integrado, com alvo de faces e tentativa de preservar sharp/boundaries. O algoritmo espera malha manifold; os GLBs gerados têm problemas/componentes que podem exigir preparação por peça. Perde data layers, portanto manter fonte e refazer UV/bake na nova malha. Não garante mínimo de triângulos. [Manual](https://docs.blender.org/manual/en/4.0/modeling/meshes/retopology.html), [algoritmo](https://github.com/hjwdzh/QuadriFlow).
- **Instant Meshes**: candidato open source de remeshing orientado por campos, com binário Windows e orientação ajustável interativamente. Avaliar adequação e integração batch antes de incorporar; não é unwrap/bake. [Projeto](https://github.com/wjakob/instant-meshes).
- **Quad Remesher / EXOSIDE**: candidato comercial com plugin Blender, tamanho adaptativo por curvatura, detecção de hard edges e controle de densidade. O autor oferece trial; testar antes de comprar. Alvo de quads é aproximado e não equivale a triângulos; quads triangulados usualmente duplicam essa contagem. Não há prova local de superioridade ou compatibilidade da versão exata com nosso Blender5.2.1. [Produto](https://exoside.com/), [manual](https://www.exoside.com/quadremesherdata/QuadRemesher_1.3_UserDoc.pdf).
- **meshoptimizer**: alternativa de simplificação para automação com erro tolerado, atributos e bloqueio de vértices. Continua sendo simplificador, não reconstrução semântica; pode parar acima do alvo por restrições. Costuras/topologia inconsistente também limitam redução. Erro calculado pelo algoritmo não é garantia de máxima distância real/silhueta; comparar externamente. [API](https://github.com/zeux/meshoptimizer/blob/master/src/meshoptimizer.h), [uso](https://github.com/zeux/meshoptimizer/blob/master/js/README.md).
- **Reconstrução por primitivas/perfis**: para props simples, pode produzir malha bem mais econômica. Exige reconhecer/separar formas; automação genérica em qualquer prop de IA não está resolvida. Usar semiautomação/ajuste humano quando contorno/encaixes forem críticos.

Recomendação atual: teste pequeno de QuadriFlow em cópia preparada de prop sólido; Instant Meshes como comparação gratuita; Quad Remesher em trial se houver interesse em opção paga. Comparar mesma fonte, orçamento de triângulos final e vistas iguais. Para arquitetura simples, incluir reconstrução por perfis. meshoptimizer é candidato especialmente para integração da fila/LOD, sem prometer resolver a falha que ocorreu no Decimate.

Remeshing pode arredondar bordas e perder detalhes finos; separar folhagem e interiores para não impor um método único. Todos os caminhos ainda precisam de UV/packing e bake; quads não maximizam ocupação do atlas por si só. Voxel remesh universal continua inadequado como padrão para aberturas/folhagem/interiores.

Nenhuma alternativa instalada ou executada, nenhum original alterado. Decisão de ferramenta pendente de comparação, e bake no Blender permanece adotado.
