"""Local TraceLoft web application. External input; Python owns recording and shared practice state."""
import argparse
import asyncio
import contextlib
import json
import socket
import sqlite3
import webbrowser
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from analysis import build_report, report_csv
from putting import PuttingSession
from putting_distance import DEFAULT_MODEL_ID
from web_service import ROOT, DRILLS, GolfService


class PracticeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drill: str
    target: float = Field(default=4, gt=0, allow_inf_nan=False)
    speed_tolerance: float = Field(default=.3, ge=0, allow_inf_nan=False)
    angle_tolerance: float = Field(default=1, ge=0, allow_inf_nan=False)
    repetitions: int = Field(default=10, ge=1, le=1000)
    random_pace: bool = False
    minimum: float = Field(default=3, allow_inf_nan=False)
    maximum: float = Field(default=6, allow_inf_nan=False)
    stimp: float = Field(default=10, ge=3, le=20, allow_inf_nan=False)
    target_mode: str = 'speed'
    target_distance: float = Field(default=10, ge=.5, le=300, allow_inf_nan=False)
    distance_tolerance: float = Field(default=2, ge=0, le=100, allow_inf_nan=False)
    ladder_start: float = Field(default=5, ge=.5, le=300, allow_inf_nan=False)
    ladder_end: float = Field(default=25, ge=.5, le=300, allow_inf_nan=False)
    ladder_step: float = Field(default=5, ge=.5, le=300, allow_inf_nan=False)
    ladder_rounds: int = Field(default=2, ge=1, le=100)
    ladder_direction: str = 'ascending'
    distance_model: str = DEFAULT_MODEL_ID
    range_start: float = Field(default=30, ge=1, le=600, allow_inf_nan=False)
    range_end: float = Field(default=100, ge=1, le=600, allow_inf_nan=False)
    range_step: float = Field(default=10, ge=1, le=600, allow_inf_nan=False)
    range_shots: int = Field(default=1, ge=1, le=100)
    range_rounds: int = Field(default=2, ge=1, le=100)
    range_tolerance: float = Field(default=5, ge=0, le=100, allow_inf_nan=False)
    range_order: str = 'ascending'
    range_metric: str = 'carry'
    range_category: str = 'wedges'
    range_club: str = Field(default='', max_length=80)
    range_bag_id: str = Field(default='', max_length=32)
    range_club_id: str = Field(default='', max_length=32)
    range_target: float = Field(default=150, ge=0, le=450, allow_inf_nan=False)
    range_width: float = Field(default=30, ge=1, le=200, allow_inf_nan=False)
    range_depth: float = Field(default=20, ge=1, le=200, allow_inf_nan=False)
    handedness: str = 'right_handed'
    demo: bool = False
    swing_labels: list[str] = Field(default_factory=lambda:['Half','Three-quarter','Full'], max_length=8)
    collection_clubs: list[str] = Field(default_factory=list, max_length=50)
    collection_samples: int = Field(default=5, ge=2, le=100)
    game_rough: float = Field(default=7,ge=0,le=60,allow_inf_nan=False)
    game_sand: float = Field(default=20,ge=0,le=80,allow_inf_nan=False)
    game_variation: float = Field(default=0,ge=0,le=10,allow_inf_nan=False)
    game_gimme: float = Field(default=3,ge=0,le=10,allow_inf_nan=False)
    game_course_id: str = Field(default='meadow-one-v2',max_length=80)
    game_geometry: str = 'downrange'
    game_acknowledged: bool = False


class GameAimParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x: float = Field(ge=-5000,le=5000,allow_inf_nan=False)
    y: float = Field(ge=-5000,le=5000,allow_inf_nan=False)
    turn: int = Field(ge=0)


class GameDemoParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    distance_yd: float = Field(gt=0,le=600,allow_inf_nan=False)
    offline_yd: float = Field(default=0,ge=-200,le=200,allow_inf_nan=False)
    turn: int = Field(ge=0)


class CollectionCellParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    club_id: str = Field(max_length=32)
    swing_label: str = Field(min_length=1,max_length=40)


class RangeCleanupParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str
    keys: list[str] = Field(default_factory=list, max_length=1000)
    revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=240)
    bag_id: str = Field(default='', max_length=32)
    club_id: str = Field(default='', max_length=32)
    batch_id: str | None = None


class RangeTargetParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target: float = Field(ge=0, le=450, allow_inf_nan=False)
    width: float = Field(ge=1, le=200, allow_inf_nan=False)
    depth: float = Field(ge=1, le=200, allow_inf_nan=False)


class DemoParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    count: int = Field(default=1, ge=1, le=10)


class EquipmentParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bag_id: str = Field(default='', max_length=32)
    club_id: str = Field(default='', max_length=32)


class ClubParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(default='', max_length=32)
    label: str = Field(min_length=1, max_length=80)


class BagParams(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=80)
    clubs: list[ClubParams] | None = None


class ExcludeParams(BaseModel):
    key: str


class CourseSourceParams(BaseModel):
    data: dict


class CourseImportParams(CourseSourceParams):
    hole_id: str = Field(max_length=100)
    name: str = Field(min_length=1,max_length=100)
    par: int = Field(ge=3,le=6)
    scorecard_yards: float | None = Field(default=None,ge=30,le=1000,allow_inf_nan=False)
    tee_label: str = Field(default='Mapped tee',max_length=80)
    source_url: str = Field(default='',max_length=500)
    reviewed: bool = False
    edits: dict | None = None


class CourseDraftParams(BaseModel):
    params: CourseImportParams
    id: str | None = None
    revision: int = Field(default=0,ge=0)


class CourseOSMParams(BaseModel):
    way_id: int = Field(ge=1,le=10**12)


def create_app(service=None):
    service = service or GolfService()

    @asynccontextmanager
    async def lifespan(app):
        task=None
        try:
            await service.input.start()
            saved = service.store.connection.execute("SELECT value FROM metadata WHERE key='relay_settings.v1'").fetchone() if service.store else None
            if saved:await service.input.relay.configure(json.loads(saved[0]),service.input.port)
            task = asyncio.create_task(service.run())
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):await task
            await service.shutdown()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service

    def same_origin(origin, host):
        return not origin or urlsplit(origin).netloc == host

    def local_host(host):
        hostname = urlsplit("http://" + (host or "")).hostname
        allowed = {"localhost", "127.0.0.1", "::1"}
        if service.access["lan"]:
            allowed.update(urlsplit(address).hostname for address in service.access["addresses"])
            allowed.update((socket.gethostname().lower(), socket.gethostname().lower() + ".local"))
        return hostname in allowed

    @app.middleware("http")
    async def protect(request, call_next):
        if not local_host(request.headers.get("host")):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Use the local TraceLoft address."}, status_code=400)
        if request.url.path.startswith("/api/"):
            if not same_origin(request.headers.get("origin"), request.headers.get("host")):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Use the TraceLoft page on this server."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(OSError)
    @app.exception_handler(sqlite3.Error)
    async def io_failed(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": f"Could not save or load data: {exc}"}, status_code=500)

    @app.get("/api/health")
    async def health():
        return {"app": "TraceLoft", "status": "ready", "storage": "sqlite" if service.store else "legacy", "architecture": "relay-v1", "input_port": service.input.port}

    @app.get("/api/state")
    async def state():
        return service.snapshot()

    @app.get('/api/analysis')
    async def analysis(request: Request):
        sessions=service.store.list_sessions() if service.store else [service.load_session(s['id']).data for s in service.sessions()]
        report=await asyncio.to_thread(build_report,sessions,dict(request.query_params))
        if request.query_params.get('format')=='csv':
            return Response(report_csv(report),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="traceloft-analysis.csv"'})
        return report

    @app.get('/api/input/context')
    async def input_context():
        return service.input.context()

    @app.post('/api/input/forwarding')
    async def forwarding(request: Request):
        settings = await request.json()
        await service.input.relay.configure(settings, service.input.port)
        if service.store:
            with service.store.transaction():
                service.store.connection.execute("INSERT OR REPLACE INTO metadata VALUES('relay_settings.v1',?)",(json.dumps(settings),))
        service.settings = {k:service.input.relay.state[k] for k in ('host','port','enabled')}
        return service.snapshot()

    @app.get("/api/drills")
    async def drills():
        return DRILLS

    @app.get('/api/range-notices')
    async def range_notices():
        return Response((ROOT/'third_party/opengolfcoach/NOTICE.txt').read_text('utf-8')+'\n\n'+
                        (ROOT/'third_party/opengolfcoach/LICENSE').read_text('utf-8'),media_type='text/plain')

    @app.post("/api/practice")
    async def launch(params: PracticeParams):
        service.create_practice(params.model_dump())
        return service.snapshot()

    @app.post('/api/demo/analytics-pack')
    async def analytics_pack():
        from analytics_demo import install
        result = install(service)
        return dict(result=result,state=service.snapshot())

    @app.post('/api/demo/tour-pack')
    async def tour_pack():
        from tour_demo import install
        result = install(service)
        return dict(result=result,state=service.snapshot())

    @app.get('/api/courses')
    async def courses():
        from course_import import catalog
        return catalog(service.store)

    @app.get('/api/course-drafts')
    async def course_drafts():
        from course_workbench import list_drafts
        return list_drafts(service.store)

    @app.get('/api/course-drafts/{identity}')
    async def get_course_draft(identity: str):
        from course_workbench import load_draft
        return load_draft(service.store,identity)

    @app.post('/api/course-drafts')
    async def put_course_draft(body: CourseDraftParams):
        from course_workbench import save_draft
        return await asyncio.to_thread(save_draft,service.store,body.params.model_dump(exclude={'reviewed'}),body.id,body.revision)

    @app.get('/api/courses/example')
    async def course_example():
        from course_import import inspect
        data=json.loads((ROOT/'courses/examples/jackson-park-osm-2026-10-02.json').read_text('utf-8'))
        return dict(data=data,**inspect(data))

    @app.post('/api/courses/osm')
    async def osm_course(params: CourseOSMParams):
        from course_import import fetch_osm,inspect
        data=await asyncio.to_thread(fetch_osm,params.way_id)
        return dict(data=data,**inspect(data))

    @app.post('/api/courses/inspect')
    async def inspect_course(params: CourseSourceParams):
        from course_import import inspect
        return inspect(params.data)

    @app.post('/api/courses/preview')
    async def preview_course(params: CourseImportParams):
        from course_import import preview
        return await asyncio.to_thread(preview,**params.model_dump(exclude={'reviewed'}),allow_incomplete=True)

    @app.post('/api/courses/save')
    async def save_course(params: CourseImportParams):
        from course_import import save
        return save(service.store,params.model_dump(exclude={'reviewed'}),params.reviewed)

    @app.post("/api/practice/{session_id}/finish")
    async def finish(session_id: str):
        service.change_practice(session_id, "finish")
        return service.snapshot()

    @app.post('/api/practice/{session_id}/equipment')
    async def equipment_selection(session_id: str, params: EquipmentParams):
        service.select_equipment(session_id, params.bag_id, params.club_id)
        return service.snapshot()

    @app.post('/api/collection/{session_id}/cell')
    async def collection_cell(session_id: str, params: CollectionCellParams):
        service.select_collection_cell(session_id,params.club_id,params.swing_label)
        return service.snapshot()

    @app.post('/api/game/{session_id}/aim')
    async def game_aim(session_id: str, params: GameAimParams):
        service.game_action(session_id,'aim',params.model_dump())
        return service.snapshot()

    @app.post('/api/game/{session_id}/simulate')
    async def game_simulate(session_id: str, params: GameDemoParams):
        service.game_action(session_id,'simulate',params.model_dump())
        return service.snapshot()

    @app.get('/api/game/{session_id}/preview')
    async def game_preview(session_id: str):
        return service.game_preview(session_id)

    @app.get('/api/game/{session_id}/recommendations')
    async def game_recommendations(session_id: str):
        return service.game_recommendations(session_id)

    @app.post('/api/range/{session_id}/cleanup')
    async def range_cleanup(session_id: str, params: RangeCleanupParams):
        try:
            if (not service.practice or service.practice.data['id']!=session_id) and await asyncio.to_thread(service.capture_detector):
                raise ValueError('Stop desktop capture before editing saved sessions.')
            return service.cleanup_range(session_id,params.model_dump())
        except FileNotFoundError:
            raise HTTPException(404,'Session not found.')

    @app.post('/api/range/{session_id}/target')
    async def range_target(session_id: str, params: RangeTargetParams):
        try:
            service.target_range(session_id,params.target,params.width,params.depth)
        except FileNotFoundError:
            raise HTTPException(404,'Session not found.')
        return service.snapshot()

    @app.post('/api/range/{session_id}/simulate')
    async def simulate(session_id: str, params: DemoParams):
        try:
            service.simulate_range(session_id,params.count)
        except FileNotFoundError:
            raise HTTPException(404,'Session not found.')
        return service.snapshot()

    @app.post('/api/equipment/bags')
    async def add_bag(params: BagParams):
        service.edit_bag(params.revision, params.name)
        return service.snapshot()

    @app.put('/api/equipment/bags/{bag_id}')
    async def edit_bag(bag_id: str, params: BagParams):
        service.edit_bag(params.revision, params.name, bag_id,
                         [c.model_dump() for c in params.clubs] if params.clubs is not None else None)
        return service.snapshot()

    @app.post("/api/practice/{session_id}/abandon")
    async def abandon(session_id: str):
        service.change_practice(session_id, "abandon")
        return service.snapshot()

    @app.post("/api/practice/{session_id}/exclude")
    async def exclude(session_id: str, params: ExcludeParams):
        service.change_practice(session_id, "exclude", params.key)
        return service.snapshot()

    @app.get("/api/sessions")
    async def sessions(deleted: bool = False):
        return service.sessions(deleted=deleted)

    @app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        try:
            saved = service.load_session(session_id)
        except FileNotFoundError:
            raise HTTPException(404, "Session not found.")
        own = service.practice and service.practice.data["id"] == session_id
        if own and not service.practice.data["ended"]:
            raise ValueError("Finish or abandon the active session before deleting it.")
        if not own and not saved.data["ended"] and await asyncio.to_thread(service.capture_detector):
            raise ValueError("Stop capture in the desktop app before deleting an unfinished session it may be writing.")
        service.delete_session(session_id)
        return service.snapshot()

    @app.post("/api/sessions/{session_id}/restore")
    async def restore_session(session_id: str):
        try:
            service.load_session(session_id, deleted=True)
        except FileNotFoundError:
            raise HTTPException(404, "Deleted session not found.")
        service.restore_session(session_id)
        return service.snapshot()

    @app.get("/api/sessions/{session_id}")
    async def session(session_id: str):
        try:
            saved = service.load_session(session_id)
        except FileNotFoundError:
            raise HTTPException(404, "Session not found.")
        return dict(practice=saved.data, summary=saved.summary())

    @app.post("/api/sessions/{session_id}/exclude")
    async def exclude_saved(session_id: str, params: ExcludeParams):
        if (not service.practice or service.practice.data["id"] != session_id) and await asyncio.to_thread(service.capture_detector):
            raise ValueError("Stop desktop capture before editing saved sessions; it may still be writing this session.")
        return service.exclude_saved(session_id, params.key)

    @app.get('/api/exports/csv')
    async def export_csv():
        if not service.store:
            raise HTTPException(409, 'SQLite storage is required.')
        content = await asyncio.to_thread(service.store.export)
        return Response(content, media_type='application/zip', headers={
            'Content-Disposition':'attachment; filename="traceloft-export.zip"'})

    @app.post('/api/storage/backup')
    async def backup():
        if not service.store:
            raise HTTPException(409, 'SQLite storage is required.')
        path = await asyncio.to_thread(service.store.backup)
        return {'path':str(path),'verified':True,'protection':'local_only'}



    @app.post("/api/service/stop")
    async def stop_service():
        callback = getattr(app.state, "stop_server", None)
        if callback:
            callback()
        return {"stopping": True}

    @app.websocket("/ws")
    async def live(ws: WebSocket):
        if not local_host(ws.headers.get("host")) or not same_origin(ws.headers.get("origin"), ws.headers.get("host")):
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            while True:
                await ws.send_json(service.snapshot())
                await asyncio.sleep(.3)
        except (WebSocketDisconnect, RuntimeError):
            pass

    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "web" / "index.html")

    return app


def main():
    import os
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--resume-session", help=argparse.SUPPRESS)
    args = parser.parse_args()
    service = GolfService()
    if args.resume_session:
        service.resume_practice(args.resume_session)
    service.access.update(lan=args.lan, port=args.port,
        addresses=[f"http://{socket.gethostbyname(socket.gethostname())}:{args.port}"] if args.lan else [])
    app = create_app(service)
    config = uvicorn.Config(app, host="0.0.0.0" if args.lan else "127.0.0.1", port=args.port,
                            log_level="warning", timeout_graceful_shutdown=5)
    server = uvicorn.Server(config)
    app.state.stop_server = lambda: setattr(server, "should_exit", True)
    runtime = ROOT / "web_runtime.json"
    runtime.write_text(json.dumps(dict(pid=os.getpid(), port=args.port, lan=args.lan)))
    print(f"TraceLoft: http://localhost:{args.port}", flush=True)
    if args.lan:
        print(f"LAN address: http://{socket.gethostbyname(socket.gethostname())}:{args.port}", flush=True)
    if args.open:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{args.port}/")).start()
    try:
        server.run()
    finally:
        try:
            if json.loads(runtime.read_text()).get("pid") == os.getpid():
                runtime.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
