"""Existing Gradio interface, constructed only when a desktop client opens it."""
from functools import partial
import html
import json
from pathlib import Path
import subprocess

import gradio as gr

from studio_service import ROOT
from studio_textures import TEXTURE_LABELS, texture_maps
from studio_lod_export import export_lods, triangle_count
from studio_progress import read_progress, stage_label
from studio_pagination import (
    PAGE_BUTTONS, PAGINATION_CSS, page_button_properties, page_button_updates, page_numbers,
)


def build_demo(studio):
    selection_size = 12
    texture_cache = ROOT / "local_data/studio/texture-previews"

    def texture_buttons(maps, mode="3d", completed=True):
        return tuple(
            gr.update(interactive=completed and (channel == "3d" or bool(maps.get(channel))),
                      variant="primary" if channel == mode and completed else "secondary")
            for channel in ("3d", *TEXTURE_LABELS)
        )

    def show_texture(identifier, channel):
        if not identifier or studio.history_entry(identifier)["status"] != "completed":
            return (gr.skip(),) * 6
        maps = texture_maps(studio.variant(identifier)["model"], texture_cache)
        if channel != "3d" and not maps[channel]:
            gr.Info(f"{TEXTURE_LABELS[channel]} não está disponível neste modelo.")
            return (gr.skip(),) * 6
        return (
            gr.update(visible=channel == "3d"),
            gr.update(value=None if channel == "3d" else maps[channel],
                      label="Textura" if channel == "3d" else TEXTURE_LABELS[channel],
                      visible=True if channel != "3d" else "hidden", selected_index=0),
            *texture_buttons(maps, mode=channel),
        )

    def selected_model(identifier):
        if not identifier:
            return (gr.skip(),) * selection_size
        entry = studio.history_entry(identifier)
        if entry["status"] == "completed":
            model = studio.variant(identifier)
            report = {}
            if model["report"] and Path(model["report"]).is_file():
                report = json.loads(Path(model["report"]).read_text(encoding="utf-8-sig"))
            count = report.get("triangles") or report.get("optimized", {}).get("triangles")
            title = f"### {model['name']}\n**{'Original / high-poly' if model['kind'] == 'high' else 'Versão LOW'}**"
            if model["parent_id"]:
                title += f"\nDerivado de **{studio.variant(model['parent_id'])['name']}**"
            if count:
                title += f" · {count:,} triângulos"
            rejected = model.get("quality_status") == "rejected"
            if rejected:
                title += "\n**Rejeitado para uso no jogo:** " + model["quality_reason"]
            elif model.get("quality_status") == "approved":
                title += "\n**Aprovado pelo usuário**"
            details = dict(model, metrics=report)
            maps = texture_maps(model["model"], texture_cache)
            return (
                gr.update(value=model["model"], visible=True),
                gr.update(value=model["model"], visible=True), title, details,
                gr.update(value="", visible=False), (identifier, "completed", model.get("quality_status")),
                gr.update(interactive=not rejected),
                gr.update(value=None, visible="hidden"), *texture_buttons(maps),
            )
        active = entry["status"] == "running"
        progress = read_progress(entry["output"], entry["stage"]) if active else {"stage": entry["status"]}
        label = stage_label(progress["stage"])
        iterations = ""
        if progress.get("total"):
            iterations = f"Passo {progress['iteration']} de {progress['total']} nesta etapa"
        spinner = (
            '<div class="studio-spinner" aria-hidden="true"></div>' if active else ""
        )
        error = entry.get("error") or ""
        panel = (
            '<style>.studio-spinner{width:56px;height:56px;border:5px solid #555;'
            'border-top-color:#ff7a18;border-radius:50%;animation:studio-spin 1s linear infinite;'
            'margin:0 auto 24px}@keyframes studio-spin{to{transform:rotate(360deg)}}</style>'
            '<div role="status" aria-live="polite" style="min-height:560px;display:flex;'
            'flex-direction:column;align-items:center;justify-content:center;text-align:center">'
            f'{spinner}<h3>{html.escape(label)}</h3><p>{html.escape(iterations)}</p>'
            f'<p>{html.escape(error)}</p></div>'
        )
        revision = (identifier, entry["status"], progress["stage"], progress.get("iteration"), error)
        return (
            gr.update(value=None, visible=False), gr.update(value=None, visible=False),
            f"### {html.escape(entry['name'])} · {label}", dict(entry, progress=progress),
            gr.update(value=panel, visible=True), revision, gr.update(interactive=False),
            gr.update(value=None, visible="hidden"), *texture_buttons({}, completed=False),
        )


    def selected_refresh(identifier, previous_revision):
        if not identifier:
            return (gr.skip(),) * selection_size
        entry = studio.history_entry(identifier)
        if entry["status"] == "completed":
            revision = (identifier, "completed", entry.get("quality_status"))
            if revision == previous_revision:
                return (gr.skip(),) * selection_size
        view = selected_model(identifier)
        if view[5] == previous_revision:
            return (gr.skip(),) * selection_size
        return view


    def lod_choices(identifier):
        if not identifier or studio.history_entry(identifier)["status"] != "completed":
            return gr.update(choices=[], value=[])
        selected_variant = studio.variant(identifier)
        choices = []
        for model in studio.variants():
            if model["asset_id"] != selected_variant["asset_id"] or model.get("quality_status") == "rejected":
                continue
            try:
                count = triangle_count(model)
            except (ValueError, OSError):
                continue
            label = f"{model['name']} · {count:,} tris · {model.get('quality_status', 'unreviewed')}"
            choices.append((label, model["id"]))
        return gr.update(choices=choices, value=[identifier])


    def pick_lod_folder(current):
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-STA", "-File",
                 str(ROOT / "scripts/select_export_folder.ps1")],
                capture_output=True, text=True, encoding="utf-8-sig", timeout=180,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            result.check_returncode()
            return json.loads(result.stdout)["directory"] or current
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise gr.Error("Não foi possível abrir o seletor; digite o caminho da pasta") from error


    def export_lods_ui(identifiers, destination):
        try:
            result = export_lods(studio, identifiers, destination)
            return "LODs exportados para: " + result["directory"], result
        except (ValueError, OSError) as error:
            raise gr.Error(str(error)) from error


    MODEL_PAGE_SIZE = 8
    IMAGE_PAGE_SIZE = 4


    def gallery_items(models):
        result = []
        for model in models:
            thumbnail = Path(model["thumbnail"]) if model["thumbnail"] else None
            if thumbnail is None or not thumbnail.is_file():
                reference = Path(model["reference"]) if model["reference"] else None
                thumbnail = reference if reference and reference.is_file() else ROOT / "inputs/chair.png"
            label = "HIGH" if model["kind"] == "high" else "LOW"
            if model.get("quality_status") == "approved":
                label += " · Aprovado"
            if model.get("quality_status") == "rejected":
                label = "Rejeitado"
            if model["status"] != "completed":
                state = "Processando" if model["status"] == "running" else stage_label(model["status"])
                result.append((str(thumbnail), f"{state} · {model['name']}"))
                continue
            count = None
            if model["report"] and Path(model["report"]).is_file():
                metadata = json.loads(Path(model["report"]).read_text(encoding="utf-8-sig"))
                count = metadata.get("triangles") or metadata.get("optimized", {}).get("triangles")
            caption = f"{label} · {model['name']}"
            if count:
                caption += f" · {count:,} tris"
            result.append((str(thumbnail), caption))
        return result, [model["id"] for model in models]


    def job_rows(records):
        translations = {
            "pending": "Aguardando", "running": "Executando", "completed": "Concluído",
            "failed": "Falhou", "cancelled": "Cancelado", "interrupted": "Interrompido",
        }
        return [
            [job["name"], translations.get(job["status"], job["status"]),
             stage_label(job["stage"]), job["error"] or "", job["id"]]
            for job in records
        ]

    def queue_rows():
        return job_rows(studio.queue_jobs()), job_rows(studio.finished_jobs())

    def cancel_pending(identifier):
        try:
            studio.cancel(identifier)
        except ValueError as error:
            raise gr.Error(str(error)) from error
        return queue_rows()


    def paginate(records, page, page_size):
        pages = max(1, (len(records) + page_size - 1) // page_size)
        current = max(1, min(int(page or 1), pages))
        start = (current - 1) * page_size
        return records[start:start + page_size], current, pages


    def model_page_view(page):
        models = studio.history_entries()
        subset, current, pages = paginate(models, page, MODEL_PAGE_SIZE)
        items, identifiers = gallery_items(subset)
        return (
            items, identifiers, current,
            f"Página {current} de {pages} · {len(models)} itens",
            gr.update(interactive=current > 1),
            gr.update(interactive=current < pages),
            *page_button_updates(current, pages),
        )


    def image_page_view(page):
        references = studio.reference_images()
        subset, current, pages = paginate(references, page, IMAGE_PAGE_SIZE)
        running = studio.running_references()
        return (
            [(reference["path"], reference["name"] + (" · Processando" if reference["id"] in running else ""))
             for reference in subset],
            [reference["id"] for reference in subset], current,
            f"Página {current} de {pages} · {len(references)} imagens",
            gr.update(interactive=current > 1),
            gr.update(interactive=current < pages),
            *page_button_updates(current, pages),
        )


    def refresh(previous_ids, page, previous_image_ids, image_page, identifier, viewer_revision, gallery_revision):
        model_view = list(model_page_view(page))
        image_view = list(image_page_view(image_page))
        # Refresh counts/navigation without resetting a gallery selection every tick.
        entries = {entry["id"]: entry for entry in studio.history_entries()}
        running = studio.running_references()
        revision = (
            [(item_id, entries[item_id]["status"], entries[item_id].get("quality_status")) for item_id in model_view[1]],
            [(item_id, running.get(item_id, {}).get("id")) for item_id in image_view[1]],
            len(entries), len(studio.reference_images()), model_view[2], image_view[2],
        )
        unchanged = revision == gallery_revision
        if unchanged:
            # Preserve the navigation buttons when no page or item changed.
            model_view[6:] = [gr.skip()] * PAGE_BUTTONS
            image_view[6:] = [gr.skip()] * PAGE_BUTTONS
        if model_view[1] == previous_ids and unchanged:
            model_view[0] = gr.skip()
            model_view[1] = gr.skip()
        if image_view[1] == previous_image_ids and unchanged:
            image_view[0] = gr.skip()
            image_view[1] = gr.skip()
        status = (
            "Fila pausada: o trabalho ativo termina antes da pausa."
            if studio.paused() else "Fila ativa · um processamento por vez."
        )
        return (*model_view, *image_view, *queue_rows(), status, revision,
                *selected_refresh(identifier, viewer_revision))


    def numbered_model_page(current, slot):
        total = max(1, (len(studio.history_entries()) + MODEL_PAGE_SIZE - 1) // MODEL_PAGE_SIZE)
        current = max(1, min(int(current or 1), total))
        numbers = page_numbers(current, total)
        if slot < 0 or slot >= len(numbers) or not isinstance(numbers[slot], int):
            return (gr.skip(),) * (6 + PAGE_BUTTONS)
        return model_page_view(numbers[slot])


    def numbered_image_page(current, slot):
        total = max(1, (len(studio.reference_images()) + IMAGE_PAGE_SIZE - 1) // IMAGE_PAGE_SIZE)
        current = max(1, min(int(current or 1), total))
        numbers = page_numbers(current, total)
        if slot < 0 or slot >= len(numbers) or not isinstance(numbers[slot], int):
            return (gr.skip(),) * (6 + PAGE_BUTTONS)
        return image_page_view(numbers[slot])


    def previous_models(page):
        return model_page_view(page - 1)


    def next_models(page):
        return model_page_view(page + 1)


    def previous_images(page):
        return image_page_view(page - 1)


    def next_images(page):
        return image_page_view(page + 1)


    def choose_image(identifiers, event: gr.SelectData):
        index = event.index[0] if isinstance(event.index, (tuple, list)) else event.index
        if not event.selected or not 0 <= index < len(identifiers):
            return (gr.skip(),) * (selection_size + 3)
        running = studio.running_references().get(identifiers[index])
        if running:
            return (gr.skip(), "Acompanhando o processamento desta imagem.",
                    running["id"], *selected_model(running["id"]))
        reference = studio.reference_image(identifiers[index])
        notice = (f"Imagem {reference['name']} carregada como entrada. "
                  "Clique em Adicionar imagens à fila quando quiser gerar.")
        return [reference["path"]], notice, *((gr.skip(),) * (selection_size + 1))


    def choose_gallery(identifiers, event: gr.SelectData):
        index = event.index[0] if isinstance(event.index, (tuple, list)) else event.index
        if not event.selected or not 0 <= index < len(identifiers):
            return (gr.skip(),) * (selection_size + 1)
        identifier = identifiers[index]
        return identifier, *selected_model(identifier)


    def enqueue_images(files, resolution, seed, faces, texture):
        if not files:
            raise gr.Error("Adicione uma ou mais imagens.")
        jobs = []
        try:
            for path in files:
                jobs.append(studio.enqueue_generate(
                    path, int(resolution), int(seed), int(faces), int(texture)
                ))
        except (ValueError, OSError) as error:
            raise gr.Error(f"{len(jobs)} pedido(s) já enviado(s). {error}") from error
        notice = f"{len(jobs)} imagem(ns) adicionada(s). A geração inclui exportação GLB automática."
        return notice, *queue_rows()


    def enqueue_remesh(identifier, method, triangles, texture, repair):
        if not identifier:
            raise gr.Error("Clique no modelo que deseja processar no histórico.")
        if studio.history_entry(identifier)["status"] != "completed":
            raise gr.Error("Aguarde a conclusão do modelo antes de enviar para remesh.")
        try:
            job = studio.enqueue_remesh(identifier, method, int(triangles), int(texture), repair)
        except (ValueError, OSError) as error:
            raise gr.Error(str(error)) from error
        return f"Remesh + UV + bake adicionado: {job}. O original será preservado.", *queue_rows()

    def enqueue_uvgami(identifier, texture):
        if not identifier:
            raise gr.Error("Selecione um LOW no histórico.")
        try:
            job = studio.enqueue_unwrap(identifier, int(texture))
        except (ValueError, OSError) as error:
            raise gr.Error(str(error)) from error
        return f"UVgami + bake adicionado: {job}. A geometria do LOW será preservada.", *queue_rows()

    def uvgami_available(identifier):
        if not identifier or studio.history_entry(identifier)["status"] != "completed":
            return gr.update(interactive=False)
        model = studio.variant(identifier)
        compatible = (
            model["kind"] == "low"
            and model.get("quality_status") != "rejected"
            and Path(model["model"]).with_name("optimized.blend").is_file()
        )
        return gr.update(interactive=compatible)


    with gr.Blocks(title="Phanes Studio") as demo:
        gr.Markdown("# Phanes Studio\nGere props, escolha um modelo e compare o original com remesh + bake.")
        selected = gr.State(None)
        viewer_revision = gr.State(None)
        gallery_revision = gr.State(None)
        history_ids = gr.State([])
        model_page = gr.State(1)
        image_ids = gr.State([])
        image_page = gr.State(1)
        with gr.Row():
            with gr.Column(scale=3, min_width=280):
                gr.Markdown("### Imagens e fila")
                images = gr.File(
                    label="Imagens para gerar modelos", file_count="multiple",
                    file_types=["image"], type="filepath",
                )
                with gr.Accordion("Configuração da geração", open=False):
                    resolution = gr.Radio([512, 1024], value=1024, label="Resolução")
                    seed = gr.Number(value=0, precision=0, label="Seed")
                    faces = gr.Number(value=250000, precision=0, label="Limite de triângulos do original")
                    generation_texture = gr.Radio([1024, 2048], value=2048, label="Textura")
                generate = gr.Button("Adicionar imagens à fila", variant="primary")
                gr.Markdown("### Fila de execução atual")
                queue_status = gr.Markdown()
                with gr.Row():
                    pause = gr.Button("Pausar após o atual")
                    resume = gr.Button("Continuar")
                jobs = gr.Dataframe(
                    headers=["Modelo", "Estado", "Etapa", "Erro", "ID"],
                    datatype=["str"] * 5, interactive=False, wrap=False,
                    max_height=220, elem_id="current-job-queue",
                    column_widths=[150, 125, 140, 240, 300],
                )
                with gr.Accordion("Cancelar pendente", open=False):
                    cancel_id = gr.Textbox(label="ID do pedido")
                    cancel = gr.Button("Cancelar pedido pendente")
                gr.Markdown("### Histórico de pedidos finalizados")
                finished_jobs = gr.Dataframe(
                    headers=["Modelo", "Estado", "Etapa", "Erro", "ID"],
                    datatype=["str"] * 5, interactive=False, wrap=False,
                    max_height=260, elem_id="finished-job-history",
                    column_widths=[150, 125, 140, 240, 300],
                )
            with gr.Column(scale=7, min_width=400):
                model_title = gr.Markdown("### Selecione um modelo no histórico")
                with gr.Row(elem_classes=["texture-toolbar"]):
                    model_button = gr.Button("3D", interactive=False, scale=0, min_width=64)
                    texture_button_components = [
                        gr.Button(label, interactive=False, scale=0, min_width=64)
                        for label in TEXTURE_LABELS.values()
                    ]
                viewer = gr.Model3D(
                    label="Modelo 3D", height=560, display_mode="solid",
                    clear_color=(0.15, 0.15, 0.18, 1),
                )
                texture_viewer = gr.Gallery(
                    label="Textura", visible="hidden", height=560, columns=1,
                    object_fit="contain", allow_preview=True, preview=True,
                    interactive=False, buttons=["download", "fullscreen"],
                    elem_id="texture-viewer",
                )
                processing = gr.HTML(visible=False)
                download = gr.DownloadButton("Baixar GLB")
                with gr.Accordion("UVgami · novos UVs e bake do LOW", open=True):
                    gr.Markdown("Mantém a geometria do LOW e cria outra versão com UVs e texturas novos. Pode levar vários minutos. Requer o LOW com sua cena de bake; cada novo resultado precisa de revisão.")
                    uv_texture = gr.Radio([512, 1024, 2048], value=1024, label="Textura UVgami")
                    uv_button = gr.Button("Enviar LOW para UVgami + bake", interactive=False)
                with gr.Accordion("Remesh automático + bake do modelo selecionado", open=True):
                    method = gr.Radio(
                        choices=[("Simplificação (Decimate preparado)", "simplify"),
                                 ("meshoptimizer", "meshopt"),
                                 ("Instant Meshes (experimental)", "instant"), ("QuadriFlow", "quadriflow")],
                        value="simplify", label="Método",
                    )
                    triangles = gr.Number(value=12000, precision=0, label="Triângulos desejados (aproximado)")
                    texture = gr.Radio([512, 1024, 2048], value=2048, label="Atlas de textura")
                    repair = gr.Checkbox(
                        value=False, label="Preparação voxel para QuadriFlow (pode alterar detalhes e aberturas)"
                    )
                    remesh_button = gr.Button("Enviar modelo para remesh + bake", variant="primary")
                    gr.Markdown("Simplificação prepara uma cópia soldada e repara apenas microfissuras; o high é preservado. Resultados precisam de revisão. Instant Meshes pode ser recusado pela validação geométrica.")
                with gr.Accordion("Exportar LODs", open=False):
                    gr.Markdown("Escolha uma versão por nível do mesmo modelo. LOD0 será a mais detalhada. Avalie os candidatos antes de exportar.")
                    lod_ids = gr.Dropdown(choices=[], multiselect=True, label="Versões para os LODs")
                    lod_refresh = gr.Button("Atualizar versões do modelo selecionado")
                    lod_destination = gr.Textbox(label="Pasta de destino", placeholder="D:/MeuJogo/Assets/Props")
                    lod_pick = gr.Button("Escolher pasta…")
                    lod_export = gr.Button("Exportar LODs", variant="primary")
                    lod_notice = gr.Markdown()
                    lod_result = gr.JSON(label="Arquivos exportados")
                notice = gr.Markdown()
                with gr.Accordion("Detalhes e métricas", open=False):
                    details = gr.JSON()
            with gr.Column(scale=3, min_width=240):
                gr.Markdown("### Histórico · high e low-poly")
                history = gr.Gallery(
                    columns=2, rows=4, height=680, allow_preview=False, interactive=False,
                    label="Clique para abrir o GLB", show_label=True,
                )
                initial_model_pages = max(1, (len(studio.history_entries()) + MODEL_PAGE_SIZE - 1) // MODEL_PAGE_SIZE)
                with gr.Row(elem_classes=["history-pagination"]):
                    model_previous = gr.Button("Anterior", interactive=False, elem_classes=["pager-edge"])
                    model_page_buttons = [
                        gr.Button(**properties, scale=0, min_width=22)
                        for properties in page_button_properties(1, initial_model_pages)
                    ]
                    model_next = gr.Button("Próxima", interactive=initial_model_pages > 1, elem_classes=["pager-edge"])
                model_page_label = gr.Markdown()
                gr.Markdown("### Histórico de imagens utilizadas")
                reference_history = gr.Gallery(
                    columns=2, rows=2, height=340, allow_preview=False, interactive=False,
                    label="Imagens enviadas e de teste · clique para reutilizar",
                    show_label=True,
                )
                initial_image_pages = max(1, (len(studio.reference_images()) + IMAGE_PAGE_SIZE - 1) // IMAGE_PAGE_SIZE)
                with gr.Row(elem_classes=["history-pagination"]):
                    image_previous = gr.Button("Anterior", interactive=False, elem_classes=["pager-edge"])
                    image_page_buttons = [
                        gr.Button(**properties, scale=0, min_width=22)
                        for properties in page_button_properties(1, initial_image_pages)
                    ]
                    image_next = gr.Button("Próxima", interactive=initial_image_pages > 1, elem_classes=["pager-edge"])
                image_page_label = gr.Markdown()
        model_outputs = [
            history, history_ids, model_page, model_page_label, model_previous, model_next,
            *model_page_buttons,
        ]
        image_outputs = [
            reference_history, image_ids, image_page, image_page_label,
            image_previous, image_next, *image_page_buttons,
        ]
        selection_outputs = [
            selected, viewer, download, model_title, details, processing, viewer_revision, remesh_button,
            texture_viewer, model_button, *texture_button_components,
        ]
        texture_outputs = [viewer, texture_viewer, model_button, *texture_button_components]
        for channel, button in zip(("3d", *TEXTURE_LABELS), [model_button, *texture_button_components]):
            button.click(
                partial(show_texture, channel=channel), inputs=[selected], outputs=texture_outputs,
                api_name=f"view_{channel}", concurrency_id="model-view", concurrency_limit=1,
            )
        refresh_inputs = [
            history_ids, model_page, image_ids, image_page, selected, viewer_revision, gallery_revision,
        ]
        refresh_outputs = [*model_outputs, *image_outputs, jobs, finished_jobs, queue_status, gallery_revision,
                           *selection_outputs[1:]]
        timer = gr.Timer(3)
        demo.load(refresh, inputs=refresh_inputs, outputs=refresh_outputs, show_progress="hidden",
                  concurrency_id="model-view", concurrency_limit=1)
        timer.tick(refresh, inputs=refresh_inputs, outputs=refresh_outputs, show_progress="hidden",
                   concurrency_id="model-view", concurrency_limit=1)
        model_previous.click(
            previous_models, inputs=[model_page], outputs=model_outputs,
            api_name="models_previous_page",
        )
        model_next.click(
            next_models, inputs=[model_page], outputs=model_outputs,
            api_name="models_next_page",
        )
        image_previous.click(
            previous_images, inputs=[image_page], outputs=image_outputs,
            api_name="images_previous_page",
        )
        image_next.click(
            next_images, inputs=[image_page], outputs=image_outputs,
            api_name="images_next_page",
        )
        for index, button in enumerate(model_page_buttons):
            button.click(
                partial(numbered_model_page, slot=index), inputs=[model_page], outputs=model_outputs,
                api_name=f"models_page_button_{index + 1}",
            )
        for index, button in enumerate(image_page_buttons):
            button.click(
                partial(numbered_image_page, slot=index), inputs=[image_page], outputs=image_outputs,
                api_name=f"images_page_button_{index + 1}",
            )
        reference_history.select(
            choose_image, inputs=[image_ids], outputs=[images, notice, *selection_outputs],
            api_name="use_history_image", concurrency_id="model-view", concurrency_limit=1,
        )
        history.select(
            choose_gallery, inputs=[history_ids],
            outputs=selection_outputs,
            api_name="open_history_model", concurrency_id="model-view", concurrency_limit=1,
        )
        generate.click(
            enqueue_images, inputs=[images, resolution, seed, faces, generation_texture],
            outputs=[notice, jobs, finished_jobs], api_name="enqueue_images",
        )
        remesh_button.click(
            enqueue_remesh, inputs=[selected, method, triangles, texture, repair],
            outputs=[notice, jobs, finished_jobs], api_name="enqueue_remesh",
        )
        selected.change(lod_choices, inputs=[selected], outputs=[lod_ids], api_name=False)
        selected.change(uvgami_available, inputs=[selected], outputs=[uv_button], api_name=False)
        viewer_revision.change(uvgami_available, inputs=[selected], outputs=[uv_button], api_name=False)
        uv_button.click(
            enqueue_uvgami, inputs=[selected, uv_texture],
            outputs=[notice, jobs, finished_jobs], api_name="enqueue_uvgami",
        )
        lod_refresh.click(lod_choices, inputs=[selected], outputs=[lod_ids], api_name="lod_choices")
        lod_pick.click(pick_lod_folder, inputs=[lod_destination], outputs=[lod_destination], api_name=False)
        lod_export.click(export_lods_ui, inputs=[lod_ids, lod_destination],
                         outputs=[lod_notice, lod_result], api_name="export_lods")
        pause.click(lambda: studio.pause(True), api_name=False)
        resume.click(lambda: studio.pause(False), api_name=False)
        cancel.click(
            cancel_pending, inputs=[cancel_id], outputs=[jobs, finished_jobs], api_name=False,
        )
    return demo
