# UVgami no Phanes Studio

O usuário aprovou em 2026-10-04 o resultado UVgami/OptCuts da estante `front`, mesmo com o tempo de processamento. A versão `uvgami-89156ba0948e55128a2935232dc3f1ed` está no histórico local como LOW aprovado, derivada de `validated-7ed3e3cf2aea5910a834838457896667`, com o mesmo asset HIGH. Arquivos originais em `outputs/uv-optcuts/front-20261004/` preservados; a revisão explícita fica no banco, sem reescrever o relatório histórico do teste.

O teste preservou 5.946 vértices e 11.993 triângulos. Ocupação UV raster aproximada passou de 29,69% para 51,23%, e as ilhas de 2.716 para 191; houve aumento da distorção medida. Motor levou 591,56 s e bake/export/renders mais 40,84 s. Aprovação específica desse resultado, sem aprovação automática de outros props ou variantes. Mapas: albedo, normal, roughness, metallic e alpha em 1024; AO não foi gerado.

## Uso

No aplicativo, selecione o LOW e use **UVgami · novos UVs e bake do LOW**. A etapa cria outra versão, sem substituir ou simplificar o LOW escolhido. Compare o GLB, mapas e métricas antes de aprovar resultados novos.

Por agente, usando o Python local com `scripts/studio_cli.py` ou `Studio-Agent.cmd`:

```powershell
& './Studio-Agent.cmd' unwrap --model ID_DO_LOW --texture 1024 --request-key meu-low-uv-v1
& './Studio-Agent.cmd' wait ID_DO_PEDIDO --timeout 7200
```

O mesmo executor serializa geração, remesh e unwrap. Chave estável com parâmetros/modelo idênticos reutiliza o pedido; mudanças com a mesma chave são recusadas. Fechar a janela ou terminar uma espera não cancela o worker. Limite total do worker: duas horas; OptCuts tem limite de 6.600 s. Não se exibe percentual de progresso inventado enquanto o motor trabalha.

Esta primeira integração aceita cenas de bake `optimized.blend` com `Source_high` e um único LOW triangulado sem modificadores. Não aceita HIGH diretamente ou LOW com somente GLB. Essa condição permite reutilizar a correspondência já validada no teste. Se o OptCuts alterar posições/conectividade ou não retornar todas as faces, a etapa falha antes do bake. Em malhas com vértices coincidentes/triângulos ambíguos a transferência pode ser recusada; não há soldagem ou reparo automático nessa etapa.

Pipeline: Blender exporta os triângulos originais → motor OptCuts 1.21.9, prioridade BALANCED (`-u 4.2 -s 100 -t 6`) → correspondência de triângulos e UV por canto → Blender equaliza densidade e empacota em 0–1, margem de 4 pixels → bake HIGH→LOW e export GLB/blend/renders. Os vetores de posições e índices da cena devem permanecer exatamente iguais. Sobreposição UV é verificada por raster diagnóstico de até 512 px, uma aproximação; tolerância inferior a 0,1%. Hashes dos arquivos de entrada são conferidos. Novo relatório registra `geometry_unchanged`, motor, transferência, UVs, contagens e duração; qualidade inicial `unreviewed`.

## Instalação

O addon/motor já estavam instalados nesta máquina em `runtime/tools/uvgami-v2.1.0/`. O Phanes invoca o motor externo, sem registrar o addon nas preferências globais do Blender e sem modificar código upstream. Em outro clone:

```powershell
& './runtime/official/code/venv/Scripts/python.exe' './scripts/install_uvgami.py'
```

`Install-PhanesStudio.ps1 -OptionalTools` também instala o motor junto às ferramentas opcionais. Downloads fixados e hashes de ZIP/binário ficam em `setup/sources.json`; arquivos não acompanham o Git. GPL e licenças de dependências são mantidas junto ao binário. Proveniência em [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Registro de resultados existentes e revisão

`import-unwrap --model ID_DO_LOW --directory PASTA_ABSOLUTA` registra um resultado existente dentro de `outputs`, sem iniciar um worker nem mudar seus arquivos. Requer relatório concluído UVgami, geometria preservada, todas as faces correspondentes, hash do LOW pai e GLB válido. Registro repetido reutiliza a mesma versão e preserva sua aprovação.

`review --model ID --state approved/rejected/unreviewed --reason TEXTO` registra a decisão explícita do usuário via serviço. Agentes não devem aprovar resultados por conta própria. Conclusão, importação, exportação ou aprovação do método não aprovam novos resultados.

## Validação da integração

18 testes automatizados passaram, incluindo correspondência por canto, recusa de geometria alterada, idempotência, relações HIGH/LOW, importação e revisão explícita. A validação de fila e ciclo de vida passou em workspace isolado.

O fluxo completo pela fila, com OptCuts real, transferência, bake de cinco mapas e exportação, passou numa cena pequena isolada: 8 vértices e 12 triângulos preservados, UVs dentro de 0–1 e sem sobreposição raster detectada, resultado novo sem aprovação automática. Uma execução real sobre a cópia do LOW de 11.993 triângulos concluiu o motor em 584,87 s e confirmou todas as faces na transferência; não foi repetido seu bake completo nessa validação. O resultado aprovado da estante é o teste anterior descrito acima. Nenhum trabalho de teste foi adicionado à galeria do usuário.
