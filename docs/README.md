# Documentação — Phanes Studio

Para clonar e preparar uma instalação nova, comece pelo [README da raiz](../README.md) e pelo [guia de instalação](INSTALACAO.md). Origem do fork e licenças estão em [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Os documentos de testes abaixo registram a instalação original e referenciam resultados locais que não são enviados ao Git.

Base TRELLIS.2-stableprojectorz v22, em D:/Projetos/3dGeneratorNew. A interface local agora inclui fila de imagens, API para agentes e histórico persistente de originais HIGH e versões LOW, com clique abrindo o GLB no visualizador. Abaixo ficam as imagens utilizadas e de teste, reutilizáveis por clique. Os históricos têm paginação independente: oito modelos e quatro imagens por página, com barras numeradas para seleção direta, página ativa em destaque e reticências para históricos grandes. Trabalhos iniciados aparecem como cartões Processando; seleção mostra etapa/carregamento e abre o GLB automaticamente ao concluir. Remesh + UV + bake está integrado, ainda experimental quanto à qualidade.

## Abrir e usar

Abrir **Phanes Studio** pelo atalho na Área de Trabalho ou no Menu Iniciar, ou executar `Start-PhanesStudio.bat`. `Start-3DStudio.bat` e `Start-StableProjectorz.bat` também abrem o aplicativo. A janela Electron inicia/reutiliza o serviço automaticamente, sem terminal ou navegador. Agentes usam Studio-Agent.cmd; o serviço escolhe uma porta local e encerra após 120 segundos ocioso, conservando a fila e o histórico. Clicar num item de Histórico para visualizar; selecionar a versão desejada antes de Enviar modelo para remesh + bake. O resultado cria outro LOW e conserva o HIGH.

O processamento aparece em duas listas separadas: Fila de execução atual (executando e aguardando) e Histórico de pedidos finalizados (concluídos, cancelados, falhos e interrompidos).

- [Aplicativo Electron e acesso por agentes](DESKTOP_E_AGENTES.md): os cinco pontos implementados, comandos JSON, ciclo de vida e reconstrução do executável. Instruções para novos chats em ../AGENTS.md.

- [Studio, histórico e roteiro manual](STUDIO_UI_E_HISTORICO.md): funcionamento, arquivos, etapas de teste e limites reais de validação.
- [API para agentes](API_STUDIO.md): envio, consulta, idempotência, modelos e downloads.
- [Testes QuadriFlow e Instant Meshes](TESTES_REMESH.md): resultados e evidências, sem aprovação automática de qualidade.
- [Status](STATUS.md), [decisões](DECISOES.md) e [changelog](CHANGELOG.md).
- [Plano inicial de expansão](EXPANSAO_PROJETO.md) e [análise inicial de otimização](OTIMIZACAO_AUTOMATICA_PROPS.md): documentos históricos; o estado implementado atual está no guia do Studio.
- [Análise inicial de customização](stableprojectorz-customization-analysis.md).
- [Análise do fork](stableprojectorz-analysis.md), [instalação](stableprojectorz-installation-plan.md), [resultados da geração](stableprojectorz-results.md) e [veredito](stableprojectorz-verdict.md).

## Repetir geração pela CLI

Encerrar ou deixar a fila do Studio sem execução pesada antes de iniciar testes externos. Usar um nome de saída novo:

```powershell
& .\runtime\official\code\venv\Scripts\python.exe .\scripts\run_test.py --input .\inputs\architecture-gate.webp --resolution 1024 --name architecture-repeat --seed 0 --texture 2048
```

Saídas em outputs/architecture-repeat. Defaults: 14 steps, low_vram do fork, exportação 250000 triângulos. A redução oficial é aproximada. A geração 1024 anterior usou muita paginação com 16 GB de RAM; não prometer execução confortável só pela VRAM.

Start-Original-TRELLIS.ps1 conserva a UI original para uso separado, na porta 8080. Não executar processamento nessa interface em paralelo à fila compartilhada do Studio. Os nomes Image Prompt, Generate e Extract GLB pertencem a essa interface antiga, não ao Studio novo.

Atualização de qualidade: método padrão Simplificação (Decimate preparado), teste real da estante e rejeição de saídas com perda geométrica documentados em [Testes de remesh](TESTES_REMESH.md). O candidato no histórico requer avaliação do usuário; UV eficiente permanece pendente.

- [Teste UV xatlas](TESTE_UV_XATLAS.md): dois candidatos com bake real sobre o LOW aprovado, comparativo e limites de margens/mipmaps.

[Comparação Decimate/meshoptimizer e exportação de LODs](COMPARACAO_REMESH_E_LODS.md): candidatos reais e roteiro de review/exportação pela UI/API.
