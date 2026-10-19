import asyncio

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound streamed request bodies as well as Content-Length declarations."""

    def __init__(self, app, max_bytes=1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        try:
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    total += len(message.get("body", b""))
                    if total > self.max_bytes:
                        return await JSONResponse({"detail": "Request too large"}, status_code=413)(
                            scope, receive, send
                        )
                    chunks.append(message)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse({"detail": "Request body timeout"}, status_code=408)(
                scope, receive, send
            )

        async def replay():
            return chunks.pop(0) if chunks else await receive()

        return await self.app(scope, replay, send)
