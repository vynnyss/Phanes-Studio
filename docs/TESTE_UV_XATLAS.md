# Teste UV xatlas na estante aprovada

2026-10-04. Pedido: testar xatlas mantendo o remesh aprovado. Teste isolado, sem alterar o método UV padrão da UI/API. Dois candidatos foram registrados no histórico, vinculados ao LOW aprovado, ambos unreviewed. HIGH e LOW originais preservados.

## Dependência e licença

Binding xatlas-python 0.0.11 cp311 Windows instalado com pip --only-binary=:all: --no-deps --target runtime/tools/xatlas-python. Binding e xatlas têm licença MIT; fontes oficiais consultadas: https://github.com/mworchel/xatlas-python e https://github.com/jpcy/xatlas. Nenhum peso ou dataset incorporado. Dependência nativa isolada do ambiente principal; NumPy existente reutilizado. Licença instalada em runtime/tools/xatlas-python/xatlas-0.0.11.dist-info/licenses. Compatibilidade testada neste runtime Windows/Python, sem garantia em outras máquinas.

## Procedimento e resultados

Extrair posições e índices exatos do optimized.blend aprovado (11.993 triângulos). xatlas gera charts e packing fora do Blender; transferir UV por canto após verificar vmapping[indices] == faces. Não substituir posições ou índices e não aplicar remesh novamente. Bake PBR 1024, margem de bake 2 px, cage 0,015 e ray 0,04, iguais à referência. Renderizar quatro vistas e exportar GLB/BLEND/PNG.

| Configuração | Ocupação de superfície raster 512 | Tempo xatlas | Packing |
|---|---:|---:|---|
| Blender aprovado | 29,69% | não medido neste teste | Smart UV + packing existente |
| xatlas | 40,94% | 0,55 s | padding nativo 4, packing aleatório |
| xatlas compacto experimental | 60,57% | 1,54 s | padding nativo 2, brute force |

Ambos: sem UV degenerada ou fora de 0-1, zero sobreposição detectada no raster 512, bake completo, 11.993 triângulos reimportados do GLB. Arrays de posições/índices Blender iguais antes/depois; hash HIGH preservado. Render frontal examinado sem perda de forma; quatro renders produzidos, certificação visual de cada detalhe e engine permanecem pendentes.

## Ajuste numérico e limitações

Primeira parametrização em unidades originais retornou dois triângulos minúsculos com UV zero; área física combinada ~4,75e-9 da superfície. Rejeitada antes do bake, artefatos initial-* preservados. Multiplicar apenas a entrada numérica de parametrização por 1000 resolveu; UVs transferidas de volta sem modificar a malha aprovada.

resolution=1024 no xatlas é alvo, não tamanho exato: atlas nativo resultou em 1420x1422 e 944x1436; UV normalizada aplicada à textura quadrada 1024. Margens nativas não equivalem diretamente a pixels finais. No compacto, padding convertido corresponde aproximadamente a 2,17 px em U e 1,43 px em V; densidade por direção também muda ao converter atlas retangular em quadrado. Portanto a versão compacta requer atenção a filtragem, distorção/densidade e mipmaps. Ainda não selecionada como padrão.

Utilização nativa xatlas de 83,38%/94,29% considera ocupação de packing e não equivale à área de superfície medida; comparar pelo mesmo raster usado no baseline. Sobreposição raster é aproximação, não prova geométrica. Número de charts ainda alto: 1.890; fragmentação e margens limitam eficiência. Sem promessa de 100% de ocupação ou qualidade universal.

## Como avaliar na UI

Se necessário iniciar Start-StableProjectorz.bat, abrir http://127.0.0.1:8080 e selecionar no Histórico · high e low-poly os itens front · UV xatlas e front · UV xatlas compacto experimental. Comparar com front · simplificação preparada 12 mil; girar e aproximar o modelo, verificar costuras e detalhes, baixar GLB e importar no jogo para testar perto/longe com mipmaps. Renders e métricas em outputs/uv-xatlas/front/ e outputs/uv-xatlas/front-compact/; comparação em outputs/uv-xatlas/comparison.json. A fila foi retomada ao estado ativo anterior, sem interromper processamento pesado.

## Repetir o experimento

Usar fila sem tarefas pesadas e cópias de saída novas; não executar em paralelo com geração. Scripts scripts/test_front_xatlas_blender.py (extract/bake) e scripts/generate_front_xatlas.py (--output, --padding, --brute-force). Entrada da estante fixada no script por ser experimento, não funcionalidade genérica integrada. extract exporta approved-geometry.npz; generate cria atlas.npz; bake aplica UV e produz exportações. Não substituir arquivos de resultados já avaliados ao repetir.
