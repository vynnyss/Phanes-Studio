# Expansão do projeto — fila, agentes e histórico

## Atualização executável — Studio, 2026-10-04

Fila, API local, histórico HIGH/LOW e remesh + UV + bake implementados. Histórico contém quatro HIGH e dois LOW da pistola, vinculados e com originais preservados. Callbacks de seleção/Model3D, download, relações, controle da fila e submissão de duas imagens testados. Instant Meshes gerou 7919 e 22224 triângulos; QuadriFlow recusou a pistola com e sem voxel. Qualidade/UV automáticos continuam experimentais; UI WebGL visual e geração completa pelos novos botões não verificadas. Guia atual: STUDIO_UI_E_HISTORICO.md; API_STUDIO.md; TESTES_REMESH.md. Evidências: local_data/studio/ e outputs/studio/.

As seções anteriores abaixo registram o estado histórico e são substituídas por esta atualização quanto às funcionalidades novas.


Data: 2026-10-04. **Escopo confirmado pelo usuário; implementação pendente.** Este documento registra a expansão e analisa a interface; não é entrega de código funcional.

## Decisões confirmadas

- Usar o fork TRELLIS.2-stableprojectorz como base da geração local, aproveitando a instalação v22 validada em D:/Projetos/3dGeneratorNew.
- Resolver a textura depois de retopologia/UV por **bake high→low no Blender**. O problema está encerrado como escolha de workflow; bake automático e resultado final ainda não foram executados/validados. Integração neural texture-only deixa de ser prioridade desta expansão.
- Expandir com fila de várias imagens, executadas sequencialmente, um modelo por imagem.
- Ajustar o acesso para agentes enviarem pedidos, acompanharem trabalhos e obterem resultados.
- Adicionar histórico persistente: clicar em um modelo gerado abre aquele GLB diretamente no visualizador 3D existente.

Detalhes de UI e arquitetura abaixo são propostas para cumprir esses requisitos. Não desenvolver um novo gerador, treinar modelo ou instalar outro backend nesta expansão.

## Interface simples proposta

Uma tela principal, com três áreas:

| Esquerda: entrada e fila | Centro: modelo 3D | Direita: histórico |
|---|---|---|
| Adicionar uma ou várias imagens | Visualizador existente, em destaque | Miniaturas dos modelos concluídos |
| Gerar / Adicionar à fila | Nome do modelo selecionado | Nome e data |
| Lista curta com ordem e estado | Girar, aproximar e afastar | Clique abre diretamente o GLB |
| Pausar / Continuar | Baixar GLB | Mais recentes primeiro |
| Configurações avançadas recolhidas | Detalhes técnicos recolhidos | Rolagem/paginação |

Os nomes desta tabela são rótulos propostos, não botões já disponíveis. A apresentação deve manter o foco em imagens, modelos e andamento; seeds e parâmetros permanecem acessíveis, mas fora do fluxo principal.

Em tela pequena: entrada/fila acima, visualizador em seguida e histórico abaixo. Os exemplos do mantenedor podem permanecer em uma seção recolhida, liberando o espaço principal para o histórico. Não criar inicialmente páginas separadas, dashboards, filtros elaborados ou editor de prompt dentro do TRELLIS.

### Adicionar imagens

Selecionar/arrastar vários arquivos mostra suas miniaturas e nomes antes do envio. Uma imagem resulta em um job independente. O botão Gerar atende uma imagem; Adicionar à fila atende o lote. Ambos usam o mesmo executor sequencial.

Fila mostra nome e estado: Aguardando, Preparando imagem, Gerando, Exportando GLB, Concluído, Falhou ou Cancelado. Etapa atual é mais honesta que percentual preciso inventado. Pausar inicialmente significa terminar o trabalho ativo e não iniciar o próximo; o texto deve deixar isso claro. Remover um item pendente é simples; cancelamento ativo exige tratar encerramento do worker.

Exportação GLB deve fazer parte da conclusão automática do job. Não exigir Extract GLB para cada item do lote. Isso também facilita uso por agentes.

### Clicar no histórico

1. Cada miniatura se associa ao identificador imutável de um resultado.
2. Clique seleciona esse item e envia o caminho autorizado do GLB salvo ao componente Model3D existente.
3. Nome, download e detalhes passam a corresponder ao mesmo resultado selecionado.
4. Não dispara difusão, reconstrução ou novo export; não precisa recuperar latentes para visualizar o GLB.
5. Seleção permanece ao atualizar a fila/histórico. Uma geração concluída em segundo plano não troca o modelo que o usuário está examinando.
6. Se ainda não houver seleção, o primeiro resultado pode aparecer automaticamente. Um aviso discreto informa novos resultados.
7. Se o arquivo estiver ausente/corrompido, mostrar erro claro nesse item; nunca abrir silenciosamente outro GLB.

A miniatura preferida é um render da geração. Na falta dele, a imagem de referência pode ser usada como fallback identificado, sem apresentá-la como render do modelo. Gerações com erro aparecem na fila; histórico de modelos mostra resultados com GLB disponível.

Visualização utiliza somente os arquivos salvos e o renderizador do navegador. Não deve inicializar/carregar modelos de IA. Isso permite abrir o histórico enquanto o executor gera o próximo job, embora a renderização 3D do navegador também possa consumir recursos gráficos.

### Informações por modelo

À vista: nome e data; download do GLB e referência original. Em Detalhes: resolução, seed, parâmetros, tempo, origem UI/agente, métricas e caminhos de relatório. Sem expor linguagem de runtime no fluxo básico.

GLB bruto permanece preservado. Bake, retopologia e mudanças Blender são versões derivadas; não substituir silenciosamente um resultado histórico. Exclusão definitiva de modelos, tags e comparação lado a lado ficam fora da primeira entrega.

## Evidência técnica da interface existente

Inspecionado runtime/official/code/app.py:

- create_preview_panel usa HTML para prévias renderizadas e **gr.Model3D** para o GLB em uma etapa Extract.
- Model3D instalado (Gradio 6.0.1) aceita caminho de arquivo .glb como valor de saída.
- Gallery instalado possui evento select; pode servir de miniaturas clicáveis sem construir um visualizador 3D novo.
- extract_glb grava dentro de diretório temporário associado à sessão.
- end_session apaga esse diretório; Blocks também usa limpeza de cache.
- O estado de geração atual está em gr.State; não é catálogo persistente.

Portanto, adicionar somente uma galeria não resolve o histórico. É necessário persistir os arquivos fora dos diretórios temporários/cache e indexar os resultados. Clicar em histórico também precisa de estado de seleção próprio; não confundir GLB selecionado com latentes do último trabalho ou botão de extração.

A capacidade dos componentes foi confirmada no código local. Clique no histórico e persistência ainda não implementados ou testados. A navegação visual da aplicação existente continua com a limitação de validação anterior.

## Base da expansão e armazenamento

Reutilizar o worker e as otimizações low-VRAM do fork validado, sem substituir o modelo de geração. Uma camada da aplicação gerencia fila, histórico e interface/API; organizar as mudanças de forma revisável e manter a proveniência da base. Upgrades do upstream exigem revisão/benchmark próprios; não atualizar a instalação funcional só para obter UI.

Proposta: SQLite para jobs/artefatos e diretório permanente por identificador em outputs/. Modelos, imagens, caches e ambiente ficam fora do Git e dentro do projeto no D.

Cada job registra ID, nome, origem, imagens/hashes, seed/parâmetros efetivos, versão do backend, etapa/estado, horários, erro e artefatos. Ao concluir o GLB, persistir o registro e publicar o item no histórico. Arquivos de download resolvidos por ID com contenção ao armazenamento de artefatos; não expor todo o runtime ou aceitar caminhos arbitrários do cliente.

Reabrir navegador/reiniciar servidor deve reconstruir o histórico do armazenamento. Resultados anteriores podem ser cadastrados como legado, preservando GLB e hash. Os quatro outputs concluídos já existentes são candidatos para validar esse cadastro, sem nova inferência.

## Fila e agentes usam o mesmo serviço

Um executor pesado por vez na RTX 5060. Upload/consulta/histórico podem atender múltiplos clientes, mas UI, CLI e agentes não podem criar workers concorrentes sem coordenação.

Operações propostas: enviar job, consultar estado, listar jobs/resultados e cancelar pendentes. Envio retorna ID rapidamente; inferência continua no executor. Contrato deve registrar erros, deduplicar reenvios e fornecer links/caminhos estáveis dos artefatos. API/CLI primeiro; adaptador MCP opcional, não requisito para a UI.

O agente gera a referência por sua ferramenta de imagens, depois envia o arquivo. O TRELLIS não recebe prompt textual. Se geração de imagem também usar a GPU local, coordenar recursos no mesmo mecanismo; não rodar simultaneamente com TRELLIS. Nenhum agente foi disparado nesta análise.

Resultados entram como candidatos; aprovação artística e incorporação ao jogo são separadas. O agente pode continuar outras tarefas após receber o job ID, mas precisa estar ativo/agendado para acompanhar ou preparar mais referências.

Na primeira implementação, subprocesso por job é recomendação conservadora por liberação de memória; reutilização aquecida somente após medir sequências. Retry limitado, sem reduzir qualidade silenciosamente. Persistir intermediários permite repetir export quando possível sem regenerar tudo. Reinício precisa detectar job interrompido, não marcá-lo como concluído.

## Ordem de implementação sugerida

1. **Persistência e contratos compartilhados**: jobs, artefatos, diretórios por job e cadastro dos resultados existentes.
2. **Fila sequencial**: entrada múltipla, execução até GLB, pausa e recuperação de falhas.
3. **UI simples e histórico**: galeria, seleção independente, visualizador e download do resultado correto.
4. **Acesso para agentes**: API/CLI usando a mesma fila, deduplicação e consulta não bloqueante.

Histórico pode ser validado com os GLBs já existentes antes de executar um lote novo. UI e agentes dependem da mesma camada; não manter três fluxos de geração concorrentes separados.

## Critérios de aceitação e roteiro futuro

Estado de todos os itens abaixo: **planejado/não executado**.

Pré-requisitos: instalação v22 funcional, GPU disponível e armazenamento do projeto preservado. Nomes de botões abaixo são os propostos neste documento.

1. Abrir a aplicação. Histórico deve listar modelos persistidos, incluindo legado cadastrado. Clicar arquitetura → abrir seu GLB; clicar pistola → trocar visualizador, nome e download para pistola.
2. Conferir o hash do GLB baixado contra o artefato selecionado. Nenhum evento generate/extract deve ocorrer ao selecionar histórico.
3. Fechar navegador e reiniciar serviço. Modelos permanecem listados e selecionáveis, independentemente do diretório temporário anterior.
4. Adicionar três imagens conhecidas e clicar Adicionar à fila. Cada item deve gerar um GLB próprio, um por vez, com seed/parâmetros/relatório preservados.
5. Durante a geração, abrir um modelo antigo. A conclusão do job não troca a seleção; novo item aparece no histórico.
6. Pausar. Job ativo termina e próximo permanece Aguardando. Continuar inicia o próximo, sem duplicar resultados.
7. Incluir uma imagem inválida entre duas válidas. Falha fica identificada; resultados válidos continuam preservados.
8. Enviar por UI e por cliente de agente. IDs distintos, um executor, downloads corretos, reenvio deduplicado conforme contrato.
9. Interromper/reiniciar serviço com job ativo. Estado interrompido recuperável; arquivos parciais não entram como modelo concluído.
10. Conferir desktop e tela pequena, histórico vazio, miniatura ausente e arquivo indisponível. Sem troca silenciosa de modelo ou caminhos fora do armazenamento.

Métricas de desempenho e memória devem acompanhar os jobs. Os testes prévios mostraram até 38,32 GiB de memória privada/paginação; funcionamento em background não garante ausência de impacto sobre Godot/Blender.

## Fora desta expansão

Texture-only neural, novo gerador, treino, retopologia automática, rigging/animação, publicação de pesos e instalação de outros geradores. Bake no Blender é o workflow adotado; automação do bake não foi solicitada nesta etapa.

Documentos relacionados: [decisões](DECISOES.md), [análise anterior](stableprojectorz-customization-analysis.md), [resultados locais](stableprojectorz-results.md) e [status](STATUS.md).

## Proposta adicional — props estáticos

O usuário esclareceu que pretende usar a geração somente para props sem animação, priorizando quantidade de polígonos, preservação da forma e aproveitamento UV. A análise em [OTIMIZACAO_AUTOMATICA_PROPS.md](OTIMIZACAO_AUTOMATICA_PROPS.md) propõe simplificação adaptativa, unwrap/packing e bake high→low em Blender isolado, com variantes Original/Otimizado no histórico. Nenhum estágio de otimização foi implementado ou validado. A exclusão anterior de retopologia automática descreve o plano anterior; essa nova possibilidade foi analisada, ainda sem execução.
