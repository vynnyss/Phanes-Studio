# Testes reais de remesh — 2026-10-04

Fonte: outputs/weapon-pistol-1024/model.glb, 236991 triângulos, SHA256 cd58ee20f65cf98486c86e5ddbc033d43b79cc6eeec3377d6c79e9b6f4204070. O teste anterior do usuário era QuadriFlow integrado, confirmado; não instalar Quad Remesher pago.

| Método / alvo | Resultado real | Evidência |
|---|---|---|
| QuadriFlow / 12000 | CANCELLED: exige manifold/normais consistentes; preparação soldada ainda tinha 414 arestas non-manifold | outputs/studio/95eac74170994eabb9dd0e53c9672e39 |
| QuadriFlow + voxel / 12000 | Também CANCELLED; voxel intermediário tinha zero bordas/non-manifold medidos, mas o método ainda recusou normais/superfície | outputs/studio/6aaa5dc707ed4b86ba60c0d85c179762 |
| Instant Meshes / 12000 | 7919 triângulos, bake e GLB concluídos; UV 26,34%, 2557 arestas non-manifold, perdas visíveis | outputs/studio/100d54245ce04d57944a62c403a48adb |
| Instant Meshes / 24000 | 22224 triângulos, bake e GLB concluídos; UV 29,60%, 704 arestas non-manifold; aparência melhor | outputs/studio/0ecd01b8b0454c3399ae77904310036e |

Na versão 24000, redução de 90,62% e IoU do alpha renderizado 0,933/0,935/0,942/0,931 nas quatro vistas. São medidas individuais; IoU não certifica forma oculta ou qualidade do bake. As versões são comparáveis no histórico, derivadas do mesmo HIGH. A 12000 foi criada antes do ajuste que conserva materiais opacos; aparenta perdas adicionais por alpha projetado. A 24000 inclui esse ajuste. Não atribuir toda diferença exclusivamente ao orçamento.

As duas versões LOW foram reimportadas com trimesh: contagem confere com o relatório, UV finita, três imagens PBR embutidas. GLB reúne canais; os cinco PNGs originais do bake também ficam na pasta. report.json confirma source_unchanged. Nenhuma delas foi aprovada para o jogo pelo agente.

Diagnósticos anteriores em outputs/remesh-tests preservados. Saída quad pura Instant Meshes excedeu 39000 triângulos; modo -D passou a ser usado. Recalcular normais pelo Blender travou nas faces mistas, identificado pelo faulthandler; a orientação do Instant é preservada. Primeiro packing com grande margem fracionária colapsou UV e gerou bakes vazios; esse relatório foi marcado failed e retirado da lista de modelos concluídos, sem apagar arquivos. O worker agora valida cobertura/limites antes do bake.

Conclusão prática: integração e preservação do histórico funcionam. Instant Meshes é uma alternativa testável, mas não resolveu automaticamente o objetivo de poucas faces e alto aproveitamento UV. QuadriFlow não forneceu LOW neste modelo. Próxima validação é humana no visualizador/Blender e no jogo; outros tipos de prop e packing mais eficiente permanecem pendentes. Não prometer resultado universal nem encerrar o milestone de qualidade.

## 2026-10-04 — Correção após rejeição da estante pelo usuário

Os dois LOW Instant Meshes de front (8.342 e 6.953 triângulos) foram rejeitados pelo usuário por deformação e buracos. Finalização operacional anterior não era aprovação de qualidade. Continuam preservados, agora com quality_status=rejected e motivo; visualização/download para diagnóstico permanecem disponíveis, mas derivar outro remesh desses resultados é bloqueado. O HIGH original permanece intacto por conferência SHA256.

A comparação antes do bake confirmou perda geométrica: comprimento de bordas abertas 0,613 no HIGH preparado contra 42,76/43,82 nos LOW. Variantes Instant Meshes com aproximadamente 9,4 mil, 9,9 mil e 35 mil triângulos também falharam; aumentar polígonos não solucionou este caso. Preparação voxel + Instant igualmente insatisfatória.

Novo método padrão: Simplificação (Decimate preparado), código simplify. Solda uma cópia para remover fragmentação por UV/material, preenche somente pequenos loops fechados com até 8 vértices e perímetro <=2,5% da maior dimensão, simplifica, cria UV e faz bake PBR. Nenhuma alteração no original. Não inferir que o teste manual anterior do usuário usou a mesma preparação.

Validação geométrica em blender_geometry_quality.py rejeita o resultado antes do bake e verifica novamente antes da exportação: comprimento de bordas <=1,25 vezes o original +2% da diagonal; distância amostrada bidirecional em 2.000 pontos por direção, p95 <=1% e máximo amostrado <=5% da diagonal. Métricas individuais no report.json, sem nota geral. São limites experimentais: amostragem não certifica toda topologia, detalhes ocultos ou qualidade no jogo. Imperfeições já existentes podem permanecer.

Teste real completo: outputs/remesh-diagnosis/front/simplify-baked/model.glb, 11.993 triângulos após exportação, bake e quatro vistas, reimportação GLB confirmada e hash do original preservado. Candidato inserido no histórico como front · simplificação preparada 12 mil, ainda unreviewed. Silhuetas renderizadas IoU 0,9990–0,9994; UV ocupa 29,69%, portanto packing eficiente continua pendente. Teste negativo real outputs/remesh-diagnosis/front/instant-quality-guard/report.json terminou failed e não exportou GLB.

Roteiro manual: se necessário iniciar Start-StableProjectorz.bat, abrir http://127.0.0.1:8080 e recarregar a página após atualização. No Histórico · high e low-poly, selecionar front HIGH (249.721 triângulos). Abrir Remesh automático + bake do modelo selecionado, escolher Simplificação (Decimate preparado), Triângulos desejados 12000 e Atlas de textura 1024. Clicar Enviar modelo para remesh + bake. Selecionar cartão Processando para acompanhar; sucesso cria um LOW vinculado, sem substituir HIGH. Falha mostra motivo e não cria GLB concluído. Para avaliar o teste já realizado, selecionar front · simplificação preparada 12 mil, girar no visualizador e comparar com HIGH; conferir Detalhes e métricas e o report.json acima. Os dois LOW antigos aparecem como Rejeitado. Importação no jogo e aprovação visual do usuário continuam pendentes; WebGL automatizado não verificado por indisponibilidade da ferramenta de navegador.

2026-10-04: xatlas 0.0.11 testado na estante aprovada, mantendo 11.993 triângulos e geometria exata. Ocupação raster 29,69% ->40,94% /60,57%; bake e reimportação GLB passaram. Ambos no histórico para avaliação, compacto experimental por margens menores/atlas retangular. Método padrão UV não alterado; integração genérica e mipmaps na engine pendentes. Docs TESTE_UV_XATLAS.md; evidências outputs/uv-xatlas/. Fila restaurada ativa.

[Comparação Decimate/meshoptimizer e exportação de LODs](COMPARACAO_REMESH_E_LODS.md): candidatos reais e roteiro de review/exportação pela UI/API.
