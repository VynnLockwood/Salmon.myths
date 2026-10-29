import os
from typing import Annotated, Optional

from fastapi import FastAPI, Path, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Origins allowed to call this API from a browser. Override with a
# comma-separated CORS_ORIGINS env var (e.g. in production).
_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# `async def` runs the handler on the event loop directly. These handlers do no
# blocking I/O, so this avoids a threadpool hop on every request.
@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, le=2**31 - 1)],
    q: Annotated[Optional[str], Query(max_length=100)] = None,
):
    return {"item_id": item_id, "q": q}
