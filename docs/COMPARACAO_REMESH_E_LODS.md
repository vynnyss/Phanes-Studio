# Comparação de redução e exportação de LODs

## Objetivo e estado

Pedido de 2026-10-04: comparar Decimate preparado e meshoptimizer, buscar menor candidato aceitável, disponibilizar review manual e exportar LODs pela UI/API com pasta escolhida. Reconstrução parcial por primitivas adiada explicitamente pelo usuário.

Implementado: worker meshoptimizer, comparação real na estante, sete candidatos com bake no histórico, seleção e exportação de LODs. Escolha definitiva do menor modelo de produção depende do review do usuário. Nada foi aprovado automaticamente. Testes em outros props, comportamento na engine e mipmaps permanecem não verificados.

## Dependência e arquitetura

meshoptimizer v1.3 oficial, tag fixa, licença MIT: https://github.com/zeux/meshoptimizer/tree/v1.3. README e LICENSE do mantenedor consultados, sem pesos/datasets ou instaladores executados. meshopt_simplifier.js incorpora WASM oficial; Node24.19.0 foi copiado da instalação local para runtime/tools/meshoptimizer/node.exe, com licença Node/dependências incluída. Origem e SHA256 em local_data/studio/meshoptimizer-audit.json. O checksum confirma arquivo registrado, não auditoria completa de vulnerabilidades. Upstream TRELLIS permanece separado.

Blender prepara cópia soldada, repara microfissuras limitadas e executa Node/WASM de forma sequencial. Flags LockBorder, limite de erro 0,01. Testados position (mantém posições disponíveis), update (ajusta posições) e normal-update (ajusta posições e considera normais, peso 0,1). Sem Prune/Sloppy: não remover componentes pequenos indiscriminadamente. Default integrado é update; API method=meshopt. CLI aceita --meshopt-mode e --meshopt-error. Geometria, UV e bake continuam com a mesma validação independente; erro interno não substitui comparação externa.

## Experimento controlado

Mesma fonte HIGH front 249.721 triângulos, hash preservado; não reduzir repetidamente o LOW já simplificado para esta comparação. Orçamentos 12000/8000/6000/4000. Doze probes meshoptimizer com três modos; seleção preliminar dos modos que passaram checks, preferência por atingir alvo dentro de 1%, depois menor p95 na pior direção. Sem nota geral. Bake completo somente dos selecionados; Decimate 8k/6k/4k usa a preparação aprovada. Referência Decimate12k existente reutilizada, sem repetir o bake aprovado.

A tabela usa validação da geometria final após triangulação. Todos os candidatos usam Smart UV Blender e bake PBR1024 para manter comparação consistente. Não misturar o teste xatlas como vantagem de um backend. Relatórios, BLENDs e renders em outputs/remesh-comparison/front-20261004/. comparison.json inclui probes, falhas, candidatos e IDs. Nenhum HIGH/LOW anterior substituído.

| Método | Alvo | Tris finais GLB | P95 pior direção / diagonal HIGH | Menor IoU em 4 vistas | ID |
|---|---:|---:|---:|---:|---|
| meshopt | 12000 | 11944 | 0.0424% | 0.9989 | comparison-667ae8c03239520d9ebae43fb9001af4 |
| meshopt | 8000 | 7947 | 0.0680% | 0.9985 | comparison-575bbcd768a056bca0770cf6ab77cae9 |
| simplify | 8000 | 7991 | 0.0841% | 0.9976 | comparison-14ce4b80be015ad894e38ced42d897d4 |
| meshopt | 6000 | 5923 | 0.1176% | 0.9981 | comparison-3d5d35e2f3435d1dbf976bb60ef35611 |
| simplify | 6000 | 5990 | 0.1238% | 0.9968 | comparison-e340f43bf5625aee8be0bc14283014ae |
| simplify | 4000 | 3991 | 0.3120% | 0.9840 | comparison-b88c8d1adfa35988ba45f21ee4fa7575 |
| meshopt | 4000 | 3947 | 0.1861% | 0.9896 | comparison-e8869a5e7ef95a8491cf7e7164ce9485 |

Referência Decimate aprovada: 11.993 triângulos. Resultados são aproximados: triangulação/remoção de faces degeneradas altera a contagem final. update venceu a seleção numérica entre os modos testados em todos os alvos. normal-update4k parou em 5.731 antes do bake por restrição de erro, não foi forçado ao alvo. Nos alvos correspondentes, meshoptimizer teve menor p95 e melhor pior IoU; isso não garante preferência visual por shading, textura ou detalhes ocultos. Os dois candidatos de ~4k são os menores testados que passaram checks, ainda pendentes de aprovação humana; não são o mínimo matemático.

Primeiro meshoptimizer4k falhou no UV (min V=-0,00496); falha preservada no diretório meshopt-update-4000. Corrigido create_uv com enquadramento uniforme de todo o atlas em 0–1 com margem, preservando formas/arranjo das ilhas. Novo resultado em meshopt-update-4000-uvfit, sem alterar posições para corrigir UV. Metadados uv_preparation registram bounds antes e aplicação do ajuste. Overlap raster não é prova exata; conferir report de cada resultado.

resources.json dos probes/candidatos mede pico de RSS da árvore de processos por estágio e mínimo de RAM livre. GPU peak=null, motivo: não amostrado, BlenderCPU/WASM. A repetição diagnóstica 4k após UV fit não teve monitor RAM; seu pico é indisponível, não inferir de outro run. Renders frontais 4k dos dois backends examinados e todos os GLBs reimportados com contagem conferida; não certificar todas as faces/engine por esse teste.

## Roteiro manual — review e exportação

1. Pré-requisitos: runtime local existente e arquivos dos candidatos. Se serviço não estiver ativo, executar Start-StableProjectorz.bat. Abrir http://127.0.0.1:8080 e recarregar após atualização.
2. Em Histórico · high e low-poly, navegar com Anterior/Próxima; selecionar front · meshoptimizer · alvo 8000 e front · Decimate · alvo 8000. Repetir pares6000/4000 e comparar com front · simplificação preparada 12 mil aprovado. Clique abre o GLB específico, sem gerar novamente.
3. Girar e aproximar: conferir livros, prateleiras, moldura, costas e silhueta; abrir Detalhes e métricas e verificar geometry_validation, UV e renders. Começar review por meshoptimizer6k e4k, mas escolher pelo uso real no jogo.
4. Para gerar novos candidatos: selecionar HIGH front, abrir Remesh automático + bake do modelo selecionado, Método meshoptimizer ou Simplificação (Decimate preparado), definir Triângulos desejados e Atlas de textura, clicar Enviar modelo para remesh + bake. Mesma fila sequencial/estado Processando. Falha mantém original.
5. Para exportar: selecionar uma versão concluída, abrir Exportar LODs e clicar Atualizar versões do modelo selecionado se necessário. Em Versões para os LODs, escolher uma alternativa por nível do mesmo asset. Exemplo: aprovado11.993 como LOD0, meshoptimizer7.947,5.923,3.947 como LOD1–3. Não selecionar os dois métodos do mesmo orçamento como níveis redundantes.
6. Digitar caminho absoluto em Pasta de destino ou clicar Escolher pasta… para abrir seletor nativo Windows. Clicar Exportar LODs. Resultado mostra diretório novo e Arquivos exportados; nenhum arquivo existente sobrescrito. Cancelar seletor mantém caminho anterior. Se seletor indisponível, digitar caminho funciona.
7. Conferir subpasta lods-<asset>-<id>, LOD0.glb etc, LODn-report.json e manifest.json. GLBs contêm mapas incorporados. Manifesto registra níveis, IDs, tris, SHA256 e quality_status. Importar arquivos na engine e configurar distâncias de troca; não há ligação automática específica Unity/Unreal/Godot nem extensão LOD no GLB.

## API para agentes

POST /api/exports/lods:

```json
{
  "variant_ids": [
    "validated-7ed3e3cf2aea5910a834838457896667",
    "comparison-575bbcd768a056bca0770cf6ab77cae9",
    "comparison-3d5d35e2f3435d1dbf976bb60ef35611",
    "comparison-e8869a5e7ef95a8491cf7e7164ce9485"
  ],
  "target_directory": "D:/MeuJogo/Assets/Props"
}
```

Resposta export_id, directory, manifest, levels. Operação copia variantes existentes, não gera nem simplifica. 1–8 IDs únicos, mesmo asset, relatórios com tris disponíveis, contagens distintas e nenhuma versão rejected. unreviewed pode ser exportado para avaliar na engine e mantém esse estado. LOD0 é maior contagem, independe da ordem enviada. Caminho deve ser absoluto; pasta pode ser criada. Cada pedido cria subpasta única, sem sobrescrever/reutilizar exportação anterior. Não marca approved por exportar.

Exportação monta pasta temporária privada no destino, confere hashes, finaliza com rename; falha limpa só a pasta temporária daquela exportação. switch_distances=null com motivo no manifesto: precisam ser definidas após review na engine. Sem extração de texturas externas porque GLBs deste pipeline incorporam os mapas.

## Validações executadas e limites

- Doze probes de meshoptimizer, sete candidatos com bake completo, hash HIGH preservado, reimportação GLB de todos os concluídos.
- Exportador real, API em serviço ativo com quatro LODs, hashes byte-exatos e todos os buffers/imagens incorporados; arquivos prévios do destino preservados.
- Rejeição de IDs duplicados, destino relativo, malha rejeitada e alternativas com mesma contagem; ausência de resíduos de staging.
- Construção da UI, callbacks/lista de versões, controles presentes na configuração e meshopt API aceita (pedido teste cancelado antes do trabalho pesado).
- Evidências local_data/studio/lod-export-validation.json e lod-live-validation.json; pacote de teste em outputs/lod-export-tests/, não no jogo do usuário.
- Seletor nativo e WebGL não verificados visualmente por automação; roteiro acima permite validação humana. Importação em engine/mipmaps/review final pendentes. Fila restaurada ao estado ativo anterior.
