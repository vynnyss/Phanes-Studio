"""HTTP adapter for the Studio core; importing this module starts no executor or UI."""
from pathlib import Path
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from studio_service import DATA
from studio_lod_export import export_lods
from studio_progress import read_progress


def protected(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def create_api(studio, lifespan=None):
    api = FastAPI(title="Local 3D Studio", docs_url="/api/docs", lifespan=lifespan)

    @api.get("/api/models")
    def models():
        return studio.variants()


    @api.get("/api/history")
    def history_entries():
        return studio.history_entries()


    @api.get("/api/images")
    def reference_images():
        return studio.reference_images()


    @api.get("/api/images/{identifier}/file")
    def download_image(identifier: str):
        reference = protected(studio.reference_image, identifier)
        return FileResponse(reference["path"], filename=Path(reference["path"]).name)


    @api.get("/api/jobs")
    def list_jobs():
        return studio.jobs()


    @api.get("/api/jobs/{identifier}")
    def get_job(identifier: str):
        job = protected(studio.job, identifier)
        if job["status"] == "running":
            job["progress"] = read_progress(job["output"], job["stage"])
        return job


    @api.post("/api/jobs/generate")
    async def generate_job(
        image: UploadFile = File(...), resolution: int = Form(1024),
        seed: int = Form(0), faces: int = Form(250000), texture: int = Form(2048),
        request_key: str | None = Form(None), name: str | None = Form(None),
    ):
        suffix = Path(image.filename or "image.png").suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
            raise HTTPException(status_code=400, detail="Use PNG, JPEG or WebP")
        content = await image.read(32 * 1024 * 1024 + 1)
        if len(content) > 32 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image exceeds 32 MB")
        with tempfile.NamedTemporaryFile(dir=DATA, suffix=suffix, delete=False) as stream:
            path = Path(stream.name)
            stream.write(content)
        try:
            identifier = protected(
                studio.enqueue_generate, path, resolution, seed, faces, texture,
                origin="agent", request_key=request_key, name=name or Path(image.filename or "image").stem,
            )
        finally:
            path.unlink(missing_ok=True)
        return {"job_id": identifier, "status_url": f"/api/jobs/{identifier}"}


    class RemeshRequest(BaseModel):
        variant_id: str
        method: str = "simplify"
        triangles: int = Field(default=12000, ge=100, le=1000000)
        texture: int = 2048
        repair: bool = False
        request_key: str | None = None


    @api.post("/api/jobs/remesh")
    def remesh_job(request: RemeshRequest):
        data = request.model_dump()
        identifier = protected(
            studio.enqueue_remesh, data.get("variant_id"), data.get("method"),
            int(data.get("triangles", 12000)), int(data.get("texture", 2048)),
            bool(data.get("repair", False)), origin="agent", request_key=data.get("request_key"),
        )
        return {"job_id": identifier, "status_url": f"/api/jobs/{identifier}"}


    class LodExportRequest(BaseModel):
        variant_ids: list[str] = Field(min_length=1, max_length=8)
        target_directory: str


    @api.post("/api/exports/lods")
    def export_lod_package(request: LodExportRequest):
        return protected(export_lods, studio, request.variant_ids, request.target_directory)


    @api.post("/api/jobs/{identifier}/cancel")
    def cancel_job(identifier: str):
        protected(studio.cancel, identifier)
        return {"status": "cancelled"}


    @api.post("/api/queue/pause")
    def pause_queue():
        studio.pause(True)
        return {"paused": True, "active_job_finishes": True}


    @api.post("/api/queue/resume")
    def resume_queue():
        studio.pause(False)
        return {"paused": False}


    @api.get("/api/models/{identifier}/glb")
    def download_model(identifier: str):
        model = protected(studio.variant, identifier)
        return FileResponse(model["model"], media_type="model/gltf-binary",
                            filename=Path(model["model"]).name)
    return api
