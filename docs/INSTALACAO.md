# Instalação do Phanes Studio após clonar

O repositório contém a camada Phanes e manifestos de instalação. O runtime pesado é obtido do [fork Windows de Igor Aherne](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz), versão v22, e permanece em `runtime/`, fora do Git. Consulte também [créditos/licenças](../THIRD_PARTY_NOTICES.md).

## Pré-requisitos

Windows x64, driver NVIDIA compatível com CUDA 12.8, Node.js >=22.12 e Blender 5.2 instalado separadamente. Git é necessário para clonar; o pacote upstream inclui Git portátil para instalar utils3d. Node e Blender são detectados no computador; o instalador não modifica instalações globais nem configura paginação/driver.

Use uma pasta gravável e estável. Reserve aproximadamente 70 GB para runtime, pesos, ambientes, cache e extração; o total varia e outputs crescem com uso. A rotina exige internet para GitHub, Hugging Face, PyPI e os índices PyTorch/npm. Execução não deve coincidir com trabalhos em andamento ou janela Electron aberta.

## Etapas do instalador

1. Validar Windows x64, Node, driver NVIDIA e caminho Blender.
2. Baixar `trellis2-stableprojectorz_v22.zip`, comparar SHA256 e extrair código/Python/ferramentas em `runtime/official`. Recusar ZIPs com caminhos fora da pasta ou links simbólicos.
3. Criar `runtime/official/code/venv` com o Python 3.11 portátil do pacote.
4. Reutilizar `install.py` upstream para Torch 2.8/CUDA 12.8, wheels Windows e dependências. Os callbacks de download são adaptados somente em memória para usar os hashes/revisões registrados; o arquivo upstream não é alterado.
5. Baixar DINOv3/RMBG com SHA256 verificado e os dois snapshots Microsoft com revisões fixas em `setup/sources.json`. Conservar licenças recebidas com os modelos.
6. Aplicar `requirements-studio.txt`, removendo distribuições conflitantes de OpenCV/Pillow quando necessário. A versão OpenCV 4.10.0.84 preserva suporte EXR necessário ao HDRI.
7. Instalar pacotes Node por lockfile (`npm ci`), copiar meshoptimizer e o Node local usado pelo worker, instalar o binário Electron e empacotar Phanes Studio.
8. Gravar somente o caminho Blender em `local_data/settings.json` e criar atalhos do usuário, salvo `-NoShortcuts`. `ASSET_BLENDER` definido no ambiente tem prioridade sobre esse arquivo.

Com `-OptionalTools`, Instant Meshes é baixado com hash verificado e xatlas 0.0.11 é instalado na pasta de ferramentas. Simplificação, QuadriFlow e meshoptimizer não exigem Instant Meshes. Os experimentos xatlas em `scripts/` usam inputs locais documentados, não são uma função genérica da interface.

## Comandos

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-PhanesStudio.ps1
.\Install-PhanesStudio.ps1 -BlenderPath 'C:\Apps\Blender\blender.exe'
.\Install-PhanesStudio.ps1 -OptionalTools
.\Install-PhanesStudio.ps1 -Plan
.\Install-PhanesStudio.ps1 -CheckOnly
```

`-Plan` não instala nem baixa. `-CheckOnly` verifica o ambiente, imports reais das extensões, CUDA, EXR, existência dos snapshots/pesos e artefatos desktop/meshoptimizer, sem iniciar o serviço ou gerar modelos. `-SkipModels` omite os pesos para preparar dependências; execute novamente sem essa opção antes de gerar. `-NoShortcuts` omite os atalhos.

Se a política PowerShell bloquear a chamada direta, use o comando com `-ExecutionPolicy Bypass` apenas para esse processo; não é necessário mudar a política global.

## Repetir ou retomar

Downloads completos são reutilizados após verificação de hash. Um download incompleto é refeito para um arquivo `.download`; arquivos completos com hash incorreto são recusados, sem apagar o arquivo automaticamente. Modelos que já têm o arquivo necessário são preservados, sem certificação retroativa de hash. O ambiente CUDA é reutilizado quando as distribuições necessárias já estão instaladas; `pip check` e imports reais validam o resultado.

O instalador não sobrescreve ZIP extraído parcialmente. Se `runtime/official` existir sem os arquivos essenciais, preserve/mova essa pasta manualmente e repita a instalação. Não execute scripts de atualização do upstream que removam o venv enquanto estiver usando o Studio.

Não mova uma instalação pronta: os ambientes Python criados contêm caminhos absolutos. Para outra localização/computador, clone e instale novamente. Faça backup de `inputs`, `outputs` e `local_data` separadamente do Git.

## Termos dos downloads

Os pesos são baixados do release usado pelo fork e de Hugging Face; eles não são incluídos no Phanes Git. O download não muda seus termos. Consulte as licenças Meta, BRIA e NVIDIA em [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Tokens privados eventualmente necessários devem ficar no ambiente/cache local; não os adicione ao código ou ao Git.

## Verificação desta entrega

Verificar sintaxe PowerShell/Python, hashes/fontes dos artefatos, lockfiles, plano sem efeitos, proteção da extração/download e checagem do ambiente existente. O download/reinstalação integral de dezenas de GB em um segundo computador não é assumido como validado; registre as limitações reais no changelog/status da entrega.
