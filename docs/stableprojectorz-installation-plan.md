# Plano de instalação
Data: 2026-10-04. Plano registrado antes de executar instalação.

1. Usar pacote oficial latest v22 em runtime/official, após ler scripts. Manter checkout main somente como referência para auditoria; código original sem alterações por preferência.
2. Usar Python3.11 portátil incluído no pacote; ambiente code/venv isolado. Se ausente, obter Python3.11 portátil oficial. Não alterar Python3.12 ou CUDA global.
3. Executar rotina oficial de instalação com Torch2.8/cu128 e wheels Windows cp311; runtime, cache HF, TEMP/TMP e Gradio dentro desta pasta no D.
4. Modelos: DINOv3, RMBG2.0 das releases extra-models, microsoft/TRELLIS.2-4B e microsoft/TRELLIS-image-large no cache local. Estimativa45-70GB total, dependente do tamanho real dos snapshots.
5. Verificar torch CUDA, capability/arquiteturas, operações FP16 e imports das extensões; checar EXR antes do primeiro carregamento pesado. Se falha, capturar log completo e aplicar apenas solução mínima apoiada nas issues.
6. Inicializar app.py/Gradio ou API oficial. Configuração low_vram=True, uma geração por vez. Smoke test com objeto simples e export GLB; medir VRAM global NVIDIA, RAM da árvore de processos, memória sistema e tempo. WDDM pode tornar VRAM por processo indisponível; separar global/allocated/reserved.
7. Testar 1024 sem reduzir qualidade automaticamente após OOM: verificar offload ativo. Registrar seed0, input/hash, parâmetros exatos, GLB/hash/tamanho/vertices/triangles. Se funcionar, apenas três casos de qualidade: prop, espada, arquitetura, e importar ao menos um no Blender.
8. RTX5060/Blackwell: CUDA12.8 é a escolha oficial; extensão sem sm120, flash-attn, Triton e EXR são riscos a testar, não falhas assumidas.

Saídas: logs/, inputs/, outputs/, docs/stableprojectorz-results.md e stableprojectorz-verdict.md. Estados sem execução permanecem não verificados; nenhum treino ou gerador alternativo.

Instalação concluída com código0; pip check sem dependências quebradas. Cache HF snapshots TRELLIS2 af44b45f2e35a493886929c6d786e563ec68364d e TRELLIS-image-large25e0d31ffbebe4b5a97464dd851910efc3002d96. Pagefile preexistente D:/pagefile.sys31111MiB; não alterado. Correção EXR descrita na análise.
