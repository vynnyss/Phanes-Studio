# Análise TRELLIS.2-stableprojectorz
Data: 2026-10-04. Trabalho isolado em D:/Projetos/3dGeneratorNew. AISmith não instalado nem requerido.

## Fontes auditadas
README completo, install.py, setup.py, setup.sh, wheels, pipeline_worker.py, pipeline imagem-3D, sparse_unet_vae, image_feature_extractor e postprocess do checkout d5d38f1e033a881e2c00e3137822ef8aa4e193de. Releases e issues completas salvas em logs/releases.json e logs/issues.json.
Fonte: https://github.com/IgorAherne/TRELLIS.2-stableprojectorz
Original: https://github.com/microsoft/TRELLIS.2
Release selecionado: latest / trellis2-stableprojectorz_v22.zip (771937588 bytes). A revisão do ZIP será conferida separadamente; não presumir idêntica ao main.

## Arquitetura e diferenças
Imagem única -> remoção de fundo -> DINOv3 -> estrutura esparsa -> latentes de forma e material -> decoders esparsos -> O-Voxel -> mesh/PBR/GLB. UI Gradio e API StableProjectorz usam worker separado. Não é desenvolvimento de novo gerador.
Original anuncia 24 GB, Linux, Python >=3.8 e CUDA12.4/Torch2.6; fork distribui Windows cp311, Torch2.8/cu128 e low_vram=True por padrão. O texto herdado do original no README não descreve o instalador Windows.

## Memória
Modelos movidos CPU/GPU por etapa; decoders carregam blocos, não todo torso simultaneamente. Shape decoding envia tex_slat à CPU; subs e meshes ficam em CPU entre shape e texture; _LazyCudaSubs carrega subdivisões sob demanda; caches esparsos limpos in-place e empty_cache libera pool ocioso.
Sparse UNet usa offload de skip/residual e chunking de MLP/convolução por tamanho em bytes. Construção de output usa chunks de linhas. Export envia atributos/coordenadas à CPU e rasteriza faces em chunks. Worker força EXPLICIT_GEMM e oferece soma ponderada sequencial como fallback Triton. Essas escolhas trocam velocidade por menor pico, sem garantia universal de 8GB.
Decoders e atributos finais FP16; conversão BF16->FP16 disponível. Nenhuma execução FP8 identificada nos caminhos inspecionados. Lote usual: uma imagem/mesh; chunking interno não equivale a benchmark de geração em batch.
Forma/material gerados separadamente. Export/remesh/unwrap/bake pode ter pico independente; monitorar até GLB, não apenas difusão.
Resoluções declaradas 512,1024,1536; 1024 em ~8GB é alegação do autor, ainda não validada localmente. Texture size independente da resolução voxel.

## Dependências e compatibilidade
Python3.11 obrigatório para wheels. Torch2.8.0, torchvision0.23.0, torchaudio2.8.0 CUDA12.8. transformers4.57.3, gradio6.0.1, xformers0.0.32.post2, triton-windows3.4.0.post21. Wheels CuMesh, FlexGEMM, nvdiffrast, nvdiffrec_render, o_voxel, Pillow-SIMD; release pode incluir flash-attn e utils3d. Não instalar setup.py com extras Linux em lugar de install.py.
Driver local610.74, RTX5060 8151MiB, driver anuncia CUDA13.3 (capacidade do driver, não versão runtime Torch). Suporte Blackwell deve ser confirmado com operações CUDA e extensões; teste major>=8 do instalador não prova suporte sm120 em cada wheel.
Issues relevantes: #12/#13 OpenEXR; #8 download GLB; #6 PNG/Pillow; #4 paths com espaços; #2 GPUs antigas; #10 APIs de DINO/FlexGEMM. #11 relata RTX5060 e baixo uso VRAM, sem benchmark confiável. Não identificada comprovação local antecipada.

## Recursos e licenças
Disco: 228.6GB livres inicialmente. Reservar provisoriamente 45-70GB para pacote, ambientes, dois snapshots HF, DINO/RMBG e outputs; estimativa, confirmar após download. Instalador estima ~20GB só modelos HF. RAM16GB total, ~2.9GB livres inicialmente: offload pode depender de paginação e causar lentidão; pico esperado não documentado com segurança (null até medição). VRAM: alvo do autor ~8GB; pico local null antes dos testes.
Código/TRELLIS MIT; dependencies mantêm termos separados. DINOv3 usa licença Meta própria; RMBG2.0 usa termos BRIA separados, não assumir permissão comercial pela redistribuição do ZIP. Auditoria de uso comercial completa pendente; testes pessoais locais não demonstram licença para produto comercial. Não há incorporação ao core antigo nem publicação de pesos/dataset.

## Validações intermediárias e ajuste mínimo
CUDA real: logs/cuda-check.log, Torch2.8.0+cu128, capability12.0/sm120, matmulFP16 finita. Isto não valida extensões.
OpenCV5.0.0 instalado pelo procedimento oficial: OpenEXR:NO, forest.exr retorna None (logs/exr-check.log). Causa coincide com https://github.com/IgorAherne/TRELLIS.2-stableprojectorz/issues/12. Correção no venv: remover opencv-python-headless e instalar opencv-contrib-python==4.10.0.84; código original inalterado. Evidências logs/opencv-fix.log e exr-check-fixed.log.
Wheels auditados em logs/wheel-audit.json: CuMesh/FlexGEMM MIT, FlashAttention BSD, Pillow-SIMD HPND, nvdiffrast/nvdiffrec licenças NVIDIA incluídas. Wheel o_voxel não inclui LICENSE; licença da fonte MIT registrada, equivalência binária não certificada.
Fontes de termos de modelos: https://huggingface.co/briaai/RMBG-2.0 (CC BY-NC4.0/acordo comercial BRIA); https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m (licença Meta própria); https://huggingface.co/microsoft/TRELLIS.2-4B (MIT). Isto é registro de proveniência para teste local, não parecer de uso comercial.

Comparação direta preservada em logs/upstream/*.diff (original main versus pacotev22): confirmou skip/residual CPU, norm/silu chunk200k, concatenação/skip chunk1M, offload de atributos/coordenadas/mesh no export e decoders sequenciais. Fonte original mutable recuperada na data da análise; pacotev22 identificado por SHA256.
OpenEXR corrigido e validado: cv2=4.10.0, forest512x1024x3. Código do fork permanece inalterado. Base CUDA validada; pipeline ainda pendente.

Detalhe de exportação confirmado no código do autor: o_voxel.postprocess.to_glb limita dc_resolution=min(resolution,512) no remeshing de Dual Contouring, para reduzir pico da malha intermediária; textura é amostrada do volume voxel na resolução original. Assim, pipeline/latentes1024 não significam que a casca intermediária do GLB remeshed use grid1024. Esta política vem do fork, não foi reduzida pelo agente; defaultUI250000tri e texture2048 usados nos três casos1024. Pode reduzir fidelidade de detalhes geométricos muito finos. Declaração de1024 deve se referir à resolução efetiva registrada, não ao tamanho da textura nem ao grid do remesh.
