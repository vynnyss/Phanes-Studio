# API local e cliente para agentes

O acesso recomendado é `Studio-Agent.cmd`, que inicia/reutiliza o serviço e descobre sua URL. Ele retorna JSON e pode ser usado sem abrir Electron. Consulte DESKTOP_E_AGENTES.md e ../AGENTS.md.

O backend usa HTTP somente em `127.0.0.1`, em porta escolhida automaticamente. Não fixe `8080`. A sessão atual está em `local_data/studio/runtime.json`; `Studio-Agent.cmd start` retorna sua identidade e URL. Documentação interativa em `/api/docs`. Não há autenticação nesta versão, conforme pedido do usuário. UI e agentes compartilham a mesma fila sequencial e o histórico.

| Método e caminho | Entrada / resultado |
|---|---|
| GET /api/runtime | Identidade, protocolo, PID, raiz, URL, interface carregada, clientes e contagem de trabalhos |
| POST /api/runtime/ui | Carrega Gradio sob demanda no mesmo serviço, sem outro executor |
| POST /api/runtime/clients | Presença renovável: kind desktop/agent e pid opcional; retorna client_id e TTL 45 s |
| PUT /api/runtime/clients/{id} | Renova presença; janela/cliente wait renovam a cada 10 s |
| DELETE /api/runtime/clients/{id} | Libera presença; não cancela trabalhos |
| POST /api/runtime/stop | Encerra se não houver clientes ou trabalho executável; conflito retorna 409 |
| GET /api/images | Referências preservadas, nome, ID SHA256 e caminho permanente |
| GET /api/images/{id}/file | Imagem original preservada |
| GET /api/history | Modelos concluídos e cartões de pedidos iniciados; model null enquanto não concluído |
| GET /api/models | HIGH/LOW, asset_id, parent_id, paths e avaliação de qualidade |
| GET /api/models/{id}/glb | GLB exato da versão |
| GET /api/jobs | Até 200 pedidos recentes |
| GET /api/jobs/{id} | Estado, etapa, parâmetros, erro e pasta; progress real para trabalhos em execução |
| POST /api/jobs/generate | Multipart image PNG/JPEG/WebP até 32 MB; resolution 512/1024, seed, faces 1000–1000000, texture 512/1024/2048, request_key e name opcionais |
| POST /api/jobs/remesh | JSON variant_id, method simplify/meshopt/instant/quadriflow, triangles 500–200000, texture 512/1024/2048, repair e request_key |
| POST /api/jobs/{id}/cancel | Cancela somente pending |
| POST /api/queue/pause | Pausa o próximo pedido; ativo termina |
| POST /api/queue/resume | Retoma pendentes |
| POST /api/exports/lods | variant_ids (1–8 IDs do mesmo asset) e target_directory absoluto |

Envio retorna job_id e status_url. Consulte o ID até completed, failed, cancelled ou interrupted. Completed indica artefato disponível, não aprovação de qualidade. A mesma request_key com mesmos dados retorna o pedido existente; conteúdo diferente é recusado. Estados running/pending não significam modelo disponível. O backend recebe imagens prontas; a criação das referências continua sendo responsabilidade da ferramenta do agente.

Exemplo Python, usando o cliente local e evitando URL fixa:

```python
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Projetos\3dGeneratorNew\scripts")
from studio_client import StudioClient

client = StudioClient(r"D:\Projetos\3dGeneratorNew")
try:
    client.ensure()
    reference = Path(r"D:\Referencias\mesa.png")
    with reference.open("rb") as image:
        result = client.request(
            "POST", "/api/jobs/generate",
            files={"image": (reference.name, image)},
            data={"resolution": 1024, "seed": 0, "faces": 250000,
                  "texture": 2048, "request_key": "mesa-v1"},
        )
    print(result["job_id"])
finally:
    client.close()
```

Para ferramentas de agentes, prefira o comando `generate`, que também cuida de lotes e retorna os IDs que já foram enviados se ocorrer falha parcial. `wait` mantém presença ativa, libera-a ao terminar e retorna 3 em timeout sem cancelar o pedido. `status` e `stop` não ligam um serviço parado.

Qualidade: versões incluem quality_status (unreviewed, approved ou rejected) e quality_reason. Remesh sobre rejected é recusado. O método padrão é simplify. Falha geométrica permanece no pedido/relatório, sem GLB falsamente concluído. Não aprovar qualidade em nome do usuário.

UVgami: `POST /api/jobs/unwrap` recebe `variant_id`, `texture` (512/1024/2048, padrão 1024) e `request_key` opcional; devolve `job_id`/`status_url`. Usa a mesma fila e conserva geometria. Requer LOW não rejeitado, cena `optimized.blend` e motor instalado. CLI: `unwrap --model ID --texture 1024 --request-key CHAVE`.

`POST /api/models/import-unwrap` recebe `variant_id` do LOW pai e `directory` absoluto do resultado existente, validado dentro de `outputs`; devolve a versão registrada sem alterar artefatos. CLI: `import-unwrap --model ID --directory PASTA`. `POST /api/models/{id}/review` recebe `state` (`approved`, `rejected`, `unreviewed`) e `reason` não vazio, devolvendo a revisão. CLI: `review --model ID --state approved --reason TEXTO`. Usar revisão apenas para registrar decisão explícita do usuário. Ver [UVGAMI.md](UVGAMI.md).

Exportação de LODs cria uma pasta nova, GLBs incorporados, manifesto, relatórios e hashes. Seleções devem ter contagens distintas e não conter versões rejected. Consulte COMPARACAO_REMESH_E_LODS.md. Download pelo cliente também recusa sobrescrita.

Há timeout de duas horas por worker. Cancelamento durante execução não está implementado. Fechar janela/chat não cancela trabalhos enviados. A fila ativa continua até esvaziar; fila pausada pode dormir, com registros preservados. Depois de 120 s ocioso sem clientes ou trabalho executável, o serviço encerra e remove seu manifesto. A próxima chamada de trabalho o inicia novamente.

Validações atuais: desktop-runtime-validation.json, desktop-window-validation.json e desktop-migration-validation.json em local_data/studio/. Testes de runtime usaram área isolada e worker controlado; migração preservou os dados reais e a janela carregou um GLB existente. Não houve nova inferência GPU para esta migração.
