# Phanes Studio

<img src="desktop/assets/phanes-studio-minimal.png" width="96" alt="Ícone Phanes Studio">

Aplicativo local para gerar modelos 3D a partir de imagens, organizar trabalhos em uma fila e preparar versões LOW com remesh, UV, bake e exportação de LODs. A janela Electron abre o ambiente automaticamente; agentes de IA podem usar a mesma fila sem abrir a interface.

**Fork/derivado de [TRELLIS.2-stableprojectorz, por Igor Aherne](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz), baseado no [TRELLIS.2 da Microsoft](https://github.com/microsoft/TRELLIS.2).** Phanes acrescenta o aplicativo, a fila, as ferramentas e a integração com agentes. O modelo e as otimizações de memória do núcleo pertencem aos projetos originais. Consulte [créditos e licenças de terceiros](THIRD_PARTY_NOTICES.md).

## Recursos

- Janela Electron, ícone e atalhos para Área de Trabalho e Menu Iniciar.
- Uma execução por vez, pausa após o atual e cancelamento de pendentes.
- Fila atual separada do histórico de concluídos, cancelados, falhos e interrompidos.
- Histórico HIGH/LOW, referências reutilizáveis, paginação e visualizador GLB.
- Simplificação, QuadriFlow, meshoptimizer e Instant Meshes opcional; UV/bake via Blender.
- Exportação de LODs e cliente JSON para outros chats/agentes.

O serviço interno escuta somente em `127.0.0.1`, escolhe uma porta livre e termina após 120 segundos ocioso. Fechar a janela conserva os trabalhos em andamento. Esta versão não inclui autenticação; não exponha o serviço na rede.

## Instalar após clonar — Windows x64

Pré-requisitos: Windows x64, GPU NVIDIA/driver compatível com CUDA 12.8, [Node.js 22.12 ou superior](https://nodejs.org/), [Git](https://git-scm.com/) para clonar e [Blender 5.2](https://www.blender.org/download/) para remesh/bake. O instalador baixa Python 3.11 portátil e os wheels do fork; não exige um Python/CUDA Toolkit global para esse caminho de instalação.

Planeje cerca de 70 GB livres para runtime, ambientes, pesos, arquivos temporários e cache; os trabalhos gerados precisam de espaço adicional. A geração foi testada localmente em RTX 5060 de 8 GB e 16 GB de RAM, com offload e paginação. O tempo e a memória necessários variam por imagem e resolução; 1024 pode ser muito demorado nesse hardware.

```powershell
git clone https://github.com/vynnyss/Phanes-Studio.git
Set-Location Phanes-Studio
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-PhanesStudio.ps1
```

Também pode abrir `Install-PhanesStudio.bat`. A instalação baixa o pacote upstream v22 com SHA256 verificado, prepara o ambiente Python, baixa os pesos, aplica a correção OpenEXR, instala Electron e meshoptimizer, empacota o executável e cria os dois atalhos. Não abre o Studio automaticamente.

Opções:

```powershell
# Somente mostrar o plano, sem downloads ou instalação.
.\Install-PhanesStudio.ps1 -Plan

# Blender em outro local.
.\Install-PhanesStudio.ps1 -BlenderPath 'C:\Apps\Blender\blender.exe'

# Acrescentar Instant Meshes e xatlas para os experimentos de UV.
.\Install-PhanesStudio.ps1 -OptionalTools

# Preparar dependências sem baixar pesos ainda; geração fica indisponível.
.\Install-PhanesStudio.ps1 -SkipModels -NoShortcuts

# Conferir uma instalação existente, sem instalar nada nem gerar modelos.
.\Install-PhanesStudio.ps1 -CheckOnly
```

Detalhes, retomada e limites de verificação: [guia de instalação](docs/INSTALACAO.md). Leia as [condições dos modelos/dependências](THIRD_PARTY_NOTICES.md) antes de baixar e usar.

## Abrir e usar

Abra **Phanes Studio** no Menu Iniciar/Área de Trabalho ou `Start-PhanesStudio.bat`. O executável fica em `desktop/dist/3DStudio/Phanes Studio.exe`, acompanhado pelos arquivos Electron. Conserve a estrutura da instalação; mover somente o `.exe` não funciona.

Selecione as imagens e envie à fila. Clique em um modelo do histórico para visualizar, criar uma versão LOW ou exportar LODs. Os arquivos existentes são preservados. Remesh e UV continuam sujeitos à avaliação de qualidade do usuário.

## Agentes e outros chats

No PowerShell, a partir da pasta do projeto:

```powershell
.\Studio-Agent.cmd status
.\Studio-Agent.cmd generate --image 'C:\Referencias\cadeira.png' --request-key 'cadeira-v1'
.\Studio-Agent.cmd wait ID_RETORNADO --timeout 7200
.\Studio-Agent.cmd models
```

Respostas em JSON. Os chats locais e a janela compartilham o mesmo executor. `status` não inicia o serviço; comandos de trabalho iniciam/reutilizam o serviço sob demanda. O comando `wait` mantém o serviço presente durante a espera; um timeout não cancela o pedido.

[AGENTS.md](AGENTS.md) orienta futuros chats; [guia desktop/agentes](docs/DESKTOP_E_AGENTES.md) e [API](docs/API_STUDIO.md) descrevem os comandos e o ciclo de vida. Chats remotos precisam de uma integração própria para acessar este computador.

## Repositório leve

O Git contém código, documentação, manifestos/lockfiles de instalação, licenças e ícones. Os pesos, pacotes Python, `node_modules`, Electron empacotado, ferramentas binárias, caches, banco da fila, imagens de entrada e modelos gerados ficam fora do repositório.

| Pasta | Conteúdo | Versionada? |
|---|---|---|
| `scripts/`, `desktop/` | Integração Phanes e fontes da janela | Sim, exceto dependências/build |
| `setup/` | Fontes/hash dos downloads e dependência meshoptimizer | Sim, exceto `node_modules` |
| `docs/`, `licenses/` | Guias, histórico técnico e avisos | Sim |
| `runtime/` | Código upstream, Python, pesos, wheels e cache | Não |
| `inputs/`, `outputs/` | Referências e resultados pessoais | Não |
| `local_data/`, `logs/` | Fila, configurações locais, registros e evidências | Não |

Os documentos antigos em `docs/` registram testes da instalação original e podem mencionar caminhos ou modelos locais que não acompanham o clone. O README e o guia de instalação são o ponto de entrada para novas instalações.

Antes de publicar alterações, prepare o índice e execute `python scripts/audit_repository.py`: ele recusa arquivos locais/pesados, possíveis credenciais e conteúdo acima de 5 MiB por arquivo ou 10 MiB no total. Os limites podem ser revistos conscientemente quando houver necessidade real.

## Licença e créditos

Código Phanes sob [MIT](LICENSE), compatível com a licença do código TRELLIS.2, conservando os avisos originais. Pesos e dependências mantêm termos separados: DINOv3 usa licença Meta própria, RMBG-2.0 tem condições não comerciais/BRIA, e componentes NVIDIA do runtime v22 têm limitações específicas. **A MIT deste repositório não concede autorização comercial para toda a cadeia de geração.**

Agradecimentos a **Igor Aherne**, à **Microsoft/equipe TRELLIS**, aos autores de **Blender, meshoptimizer, Instant Meshes e xatlas**, e aos mantenedores das demais bibliotecas. Créditos, fontes e citação acadêmica: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
