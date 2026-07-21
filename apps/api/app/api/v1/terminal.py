"""WebSocket SSH terminal bridge using asyncssh."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.services.ssh_pool import ssh_pool

router = APIRouter()


@router.websocket("/{instance_id}")
async def terminal_ws(websocket: WebSocket, instance_id: int, token: str = "") -> None:
    payload = decode_token(token) if token else None
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    conn = None
    try:
        conn = await ssh_pool.acquire(instance_id)
        chan = await conn.open_session(term_type="xterm-256color")
        chan.set_blocking(False)

        async def read_from_ssh() -> None:
            nonlocal chan
            while True:
                try:
                    data = await chan.read(4096)
                    if not data:
                        break
                    await websocket.send_json({"type": "stdout", "data": data})
                except Exception:
                    break
            await websocket.send_json({"type": "exit", "code": 0})

        ssh_task = asyncio.create_task(read_from_ssh())

        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "cmd":
                    data = msg.get("data", "")
                    if data:
                        await chan.write(data)
                elif msg.get("type") == "resize":
                    cols = int(msg.get("cols", 80))
                    rows = int(msg.get("rows", 24))
                    chan.change_window_size(cols, rows)
        except WebSocketDisconnect:
            pass
        finally:
            ssh_task.cancel()
            try:
                await ssh_task
            except Exception:
                pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "exit", "code": 1, "error": str(exc)})
        except Exception:
            pass
    finally:
        if conn:
            await ssh_pool.release(instance_id)
            try:
                await websocket.close()
            except Exception:
                pass
