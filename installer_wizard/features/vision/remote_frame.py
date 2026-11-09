from fastapi import HTTPException, Request

WIDTH = 320
HEIGHT = 240
FRAME_BYTES = WIDTH * HEIGHT * 4
CONTENT_TYPE = "application/octet-stream"


async def read_frame(request: Request) -> bytes:
    if request.headers.get("content-type") != CONTENT_TYPE:
        raise HTTPException(415, "camera.frame.type")
    if request.headers.get("content-length") != str(FRAME_BYTES):
        raise HTTPException(413, "camera.frame.size")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > FRAME_BYTES:
            raise HTTPException(413, "camera.frame.size")
        data.extend(chunk)
    if len(data) != FRAME_BYTES:
        raise HTTPException(400, "camera.frame.incomplete")
    return bytes(data)
