# Veredito — TRELLIS.2-stableprojectorz

Avaliação local concluída em 2026-10-04, Windows, RTX 5060 de 8 GB e 16 GB de RAM. Instalado o pacote oficial v22 em D:/Projetos/3dGeneratorNew. Evidências, parâmetros, limitações e artefatos: [resultados](stableprojectorz-results.md).

## 1. Funciona na RTX 5060 8 GB?

**Sim.** Um smoke test em 512 e três casos em 1024 completaram geração, textura, prévia e exportação GLB sem CUDA OOM. Torch 2.8.0+cu128 executou operações CUDA na arquitetura Blackwell sm120. O modo low_vram padrão do autor foi mantido; nenhum código do fork foi modificado.

A execução depende bastante de RAM e paginação. No caso mais exigente, a memória privada da árvore de processos atingiu 38,32 GiB, embora o computador tenha 16 GB físicos. O Windows expandiu seu pagefile preexistente automaticamente. Não interpretar o resultado como garantia para qualquer imagem, driver ou máquina de 8 GB.

## 2. 1024³ funciona dentro de 8 GB?

**Sim, nos três casos testados.** A resolução efetiva de geração foi 1024, usando 1024_cascade. No teste principal da garrafa, o pico global observado foi **7429 MiB (7,25 GiB)**; duração total 11 min 25,65 s. Arma: 4445 MiB; arquitetura: 5413 MiB. Nenhum CUDA OOM.

Esses picos são amostrados a cada segundo pelo nvidia-smi e incluem outros aplicativos. Picos dedicados WDDM do worker foram 6,20 / 3,36 / 4,09 GiB; a cobertura não inclui os primeiros segundos. Pico exato do allocator Torch é null, pois o worker oficial não o expõe. Amostragem não exclui picos breves entre leituras.

Há uma concessão de qualidade do próprio exportador: a casca intermediária de Dual Contouring é limitada a grid 512. A geração e o volume de textura continuam em 1024; não afirmar que o remesh final usa grid 1024. Texturas exportadas: 2048 × 2048.

## 3. Qualidade da geometria

**Boa para a pistola e a arquitetura; aceitável para a garrafa.** Silhuetas, volumes, acessórios e madeira/folhagem oferecem uma base útil para tratamento. A garrafa tem casca e decoração interna confirmadas por corte diagnóstico, mas detalhes são irregulares.

Blender importou os três casos: posições e normais finitas, nenhuma face degenerada e escala editável normalmente. Existem componentes separados, bordas abertas e arestas não manifold. Parte corresponde a folhas e peças intencionais; parte requer cleanup. As malhas de aproximadamente 237–241 mil triângulos precisam de redução ou retopologia para uso em tempo real. Não foram certificadas precisão mecânica, dimensões modulares ou geometria oculta completa. A arma testada foi uma pistola; espadas e lâminas finas continuam não verificadas.

## 4. Qualidade da textura

**Boa nos dois objetos opacos; aceitável na garrafa após ajuste de alpha.** Cores e materiais reconhecíveis, UV e dois mapas 2048 presentes e utilizáveis no Blender. Não houve ruptura ampla visível de seams nos renders; distorção e overlap de UV não foram medidos numericamente.

O GLB original usa material opaco, conforme o README do autor. Ligar Texture Alpha ao Principled Alpha no Blender revelou peixes e decoração interna e melhorou bastante a garrafa. A cena ajustada foi salva separadamente; GLB, geometria e UV originais foram preservados. Refração física e transparência perfeita não estão validadas. Há suavização de detalhes e reflexos incorporados à aparência.

## 5. Utilidade para game assets

**Sim, como base para TRELLIS → Blender → cleanup/retopo → UV/textura → Godot.** Os objetos opacos justificam tratamento posterior. A arquitetura é uma boa referência de cenário, mas precisa de dimensões e encaixes definidos no Blender; folhagem merece simplificação. A garrafa exige material ajustado e revisão do interior.

A importação em Blender e os materiais foram validados. Cleanup final, retopologia, LOD e importação em Godot ainda não foram executados; não declarar assets prontos para jogo. Os arquivos brutos, cenas de inspeção e renders estão preservados para esse trabalho.

## 6. Vale substituir geração comercial?

**B — Parcialmente.** A qualidade e a estabilidade observadas justificam usar a geração local primeiro para props opacos e pequenos segmentos de arquitetura. Manter serviços existentes para categorias difíceis ou resultados que não compensarem o cleanup, principalmente transparência complexa, formas muito finas e fidelidade de partes ocultas.

Não houve comparação direta com Meshy ou Tripo usando as mesmas imagens, nem medição de economia financeira. A conclusão é sobre utilidade dos exemplos locais, não superioridade comprovada sobre esses serviços.

A substituição para produção comercial também depende das licenças: RMBG 2.0 tem termos BRIA não comerciais/acordo comercial, DINOv3 tem licença Meta própria e referências têm direitos separados. A auditoria de incorporação comercial completa permanece pendente; licença MIT do TRELLIS não resolve toda a cadeia.

## Decisão de continuidade

O objetivo técnico principal foi atingido para as categorias testadas: geração local estável em 8 GB e malhas úteis no Blender. Considero encerrada a necessidade de desenvolver um gerador próprio para esse objetivo. Trabalho futuro deve priorizar o workflow TRELLIS → Blender → cleanup/retopo → textura → Godot.

Nenhum AISmith, outro gerador ou treino foi instalado/executado. O projeto 3dGeneratorLocal não foi alterado. A interface oficial responde em http://127.0.0.1:8080; upload e pré-processamento via API passaram. Navegação visual automatizada não pôde ser confirmada porque a ferramenta de navegador falhou, e a geração completa não foi repetida pela UI após os testes do worker.
