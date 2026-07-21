"""Async SSH connection pool keyed by instance id."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

try:
    import asyncssh
except ImportError:  # pragma: no cover
    asyncssh = None  # type: ignore[assignment]

from app.core.db import SessionLocal
from app.models.models import Instance


class _PooledConn:
    __slots__ = ("conn", "last_used", "lock")

    def __init__(self, conn: Any) -> None:
        self.conn = conn
        self.last_used = time.monotonic()
        self.lock = asyncio.Lock()


class SSHPool:
    """Lazy connection pool with idle TTL (seconds)."""

    def __init__(self, idle_ttl: int = 600) -> None:
        self._conns: dict[int, _PooledConn] = {}
        self._idle_ttl = idle_ttl
        self._gc_task: Optional[asyncio.Task[None]] = None

    async def _gc_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            stale = [iid for iid, pc in self._conns.items() if now - pc.last_used > self._idle_ttl]
            for iid in stale:
                pc = self._conns.pop(iid, None)
                if pc and pc.conn:
                    try:
                        pc.conn.close()
                        await pc.conn.wait_closed()
                    except Exception:
                        pass

    def start_gc(self) -> None:
        if self._gc_task is None or self._gc_task.done():
            self._gc_task = asyncio.create_task(self._gc_loop())

    async def stop(self) -> None:
        if self._gc_task and not self._gc_task.done():
            self._gc_task.cancel()
            try:
                await self._gc_task
            except Exception:
                pass
        for pc in list(self._conns.values()):
            if pc.conn:
                try:
                    pc.conn.close()
                    await pc.conn.wait_closed()
                except Exception:
                    pass
        self._conns.clear()

    async def _load_instance(self, instance_id: int) -> Instance:
        async with SessionLocal() as session:
            inst = await session.get(Instance, instance_id)
            if inst is None:
                raise KeyError(f"instance {instance_id} not found")
            return inst

    async def _connect(self, inst: Instance) -> Any:
        if asyncssh is None:
            raise RuntimeError("asyncssh not installed")
        key_file = inst.ssh_key_ref or None
        kwargs: dict[str, Any] = {
            "host": inst.host,
            "port": inst.port,
            "username": inst.ssh_user,
            "known_hosts": None,
        }
        if key_file:
            kwargs["client_keys"] = [key_file]
        return await asyncssh.connect(**kwargs)

    async def acquire(self, instance_id: int) -> Any:
        self.start_gc()
        pc = self._conns.get(instance_id)
        if pc is None:
            inst = await self._load_instance(instance_id)
            conn = await self._connect(inst)
            pc = _PooledConn(conn)
            self._conns[instance_id] = pc
        pc.last_used = time.monotonic()
        return pc.conn

    async def release(self, instance_id: int) -> None:
        # connection stays in pool; GC handles idle eviction
        pc = self._conns.get(instance_id)
        if pc:
            pc.last_used = time.monotonic()

    async def run_command(self, instance_id: int, command: str, timeout: int = 120) -> dict[str, Any]:
        conn = await self.acquire(instance_id)
        try:
            result = await conn.run(command, timeout=timeout, check=False)
            return {
                "exit_code": result.exit_status,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
            }
        finally:
            await self.release(instance_id)


# module-level singleton
ssh_pool = SSHPool()
