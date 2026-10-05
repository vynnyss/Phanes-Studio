# Créditos, proveniência e licenças de terceiros

Phanes Studio é um **fork/derivado da integração Windows de [TRELLIS.2-stableprojectorz, de Igor Aherne](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz)**, baseada no **[TRELLIS.2 da Microsoft](https://github.com/microsoft/TRELLIS.2)**. Este repositório independente contém a camada Phanes; o núcleo upstream é obtido durante a instalação. Não há afiliação ou endosso por Microsoft, Igor Aherne, NVIDIA, Meta ou BRIA.

O modelo de geração, os algoritmos TRELLIS.2 e as otimizações de memória Windows não foram criados pelo Phanes. As adições aqui incluem janela Electron, fila persistente compartilhada, históricos, cliente para agentes, remesh/bake e exportação de LODs.

## Código e pesos

A [licença MIT da raiz](LICENSE) cobre o código Phanes distribuído neste repositório, com o aviso Microsoft conservado e a licença original em [licenses/TRELLIS-MIT.txt](licenses/TRELLIS-MIT.txt). Ela não relicencia bibliotecas, executáveis ou pesos baixados. Estes conservam suas próprias licenças.

| Componente | Autores/origem | Termos e observações |
|---|---|---|
| TRELLIS.2 e TRELLIS.2-4B | [Microsoft e equipe TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | MIT; [modelo](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| Integração Windows v22 e low-VRAM | [Igor Aherne / StableProjectorz](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz) | Aviso MIT herdado do TRELLIS; conservar os avisos do pacote e as exceções de dependências |
| TRELLIS-image-large | [Microsoft / TRELLIS](https://huggingface.co/microsoft/TRELLIS-image-large) | MIT |
| DINOv3 | [Meta AI](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m) | [Licença DINOv3](https://github.com/facebookresearch/dinov3/blob/main/LICENSE), própria da Meta; não é MIT |
| RMBG-2.0 | [BRIA AI](https://huggingface.co/briaai/RMBG-2.0) | CC BY-NC 4.0 para uso não comercial; uso comercial depende de acordo com BRIA |
| nvdiffrast 0.4.0 do pacote v22 | [NVIDIA](https://github.com/NVlabs/nvdiffrast) | [Aviso do wheel usado](licenses/NVDIFFRAST-BUNDLED.txt), NVIDIA Source Code License; verificar as limitações da versão distribuída |
| nvdiffrec_render do pacote v22 | [NVIDIA](https://github.com/NVlabs/nvdiffrec) | [Aviso do wheel usado](licenses/NVDIFFREC_RENDER-BUNDLED.txt), com uso não comercial para pesquisa/avaliação |
| O-Voxel, CuMesh e FlexGEMM | [Equipe TRELLIS.2](https://github.com/microsoft/TRELLIS.2#-related-packages) | Avisos próprios nas fontes/pacote; conservar licenças do runtime e dos wheels |
| Electron | [Electron contributors](https://github.com/electron/electron) | MIT; Chromium e componentes internos têm avisos adicionais no pacote |
| Node.js | [Node.js contributors](https://github.com/nodejs/node) | MIT e avisos de bibliotecas incorporadas |
| Python | [Python Software Foundation](https://www.python.org/) | [Licenças do Python distribuído](licenses/PYTHON.txt) |
| meshoptimizer 1.3.0 | [Arseny Kapoulkine e contributors](https://github.com/zeux/meshoptimizer) | [MIT](licenses/MESHOPTIMIZER-MIT.txt) |
| Instant Meshes, opcional | [Wenzel Jakob, Marco Tarini, Daniele Panozzo e Olga Sorkine-Hornung](https://github.com/wjakob/instant-meshes) | [Licença BSD com texto adicional de contribuições](licenses/INSTANT-MESHES.txt) |
| xatlas / xatlas-python, opcionais | [Jonathan Young](https://github.com/jpcy/xatlas) / [Michael Worchel](https://github.com/mworchel/xatlas-python) | MIT; avisos acompanham a instalação |
| Blender, instalado separadamente | [Blender Foundation e contributors](https://www.blender.org/about/license/) | GPL; Phanes o invoca como processo externo e não inclui o executável |
| UVgami 2.1.0 / OptCuts 1.21.9, opcional | [Daniel Boxer e autores do OptCuts](https://github.com/DanielBoxer/UVgami) | GPL-3.0-or-later, com permissão adicional de combinação com Triangle no motor; executado como processo externo. Textos completos e avisos de Triangle/libigl/TBB/mimalloc/tclap são preservados junto ao binário baixado. Fontes e hashes em `setup/sources.json`; não se aplica a licença MIT do Phanes a esses componentes. |

Outras dependências Python/Node mantêm os avisos de suas distribuições. Esta tabela é uma indicação de proveniência, não substitui os textos completos nem concede direitos adicionais.

**A licença MIT do Phanes não implica que toda a cadeia de geração possa ser usada comercialmente.** Consulte as condições dos pesos e das versões efetivamente utilizadas, especialmente BRIA e os componentes NVIDIA. Modelos/pesos não são redistribuídos neste Git.

## Versões e downloads

[setup/sources.json](setup/sources.json) identifica o pacote v22, os ZIPs DINOv3/RMBG e seus SHA256, além dos snapshots TRELLIS em revisões fixas. A versão v22 foi obtida no release `latest`, com SHA256 `62be7caefaf12e396763dfec4b5e688fdd83c9450920090dfdb8082bd43811be`; uma substituição do asset no mesmo endereço é recusada por hash.

Os textos NVIDIA preservados aqui vêm dos wheels realmente usados no v22. Não se deve assumir que a licença da versão atual de um projeto upstream seja a mesma de um binário antigo. Os arquivos de licença dos pacotes baixados permanecem no runtime local.

## Citação de pesquisa

Para trabalhos acadêmicos que utilizem TRELLIS.2, cite a publicação dos autores originais:

```bibtex
@article{xiang2025trellis2,
  title={Native and Compact Structured Latents for 3D Generation},
  author={Xiang, Jianfeng and Chen, Xiaoxue and Xu, Sicheng and Wang, Ruicheng and Lv, Zelong and Deng, Yu and Zhu, Hongyuan and Dong, Yue and Zhao, Hao and Yuan, Nicholas Jing and Yang, Jiaolong},
  journal={Tech report},
  year={2025}
}
```
