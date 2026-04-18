import argparse
import asyncio

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.sync.service import run_gmail_sync_cycle


async def _run(tenant_slug: str, once: bool) -> None:
    while True:
        async with SessionLocal() as session:
            result = await run_gmail_sync_cycle(session, tenant_slug=tenant_slug)
            print(result)
        if once:
            return
        await asyncio.sleep(max(1, get_settings().gmail_poll_interval_seconds))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tenant-slug", default="demo")
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    asyncio.run(_run(tenant_slug=args.tenant_slug, once=args.once))


if __name__ == "__main__":
    main()
