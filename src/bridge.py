import os
from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()

CORE_IP = os.getenv("CORE_IP")
HOST_HEADER = "booqable-gateway.arctic-fortress.com"
FORWARD_PATH = "/webhook/9f4c2e8b7a1d3c6f5b8e0a4d2c7f9b1e6a3d5c8f0e1b4a7c2d6f9e0b3a5c1d8"

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

@app.on_event("startup")
async def startup():
    print("Bridge starting")
    print(f"Core IP: {CORE_IP}")
    print(f"Forward path: {FORWARD_PATH}")
    print(f"Host header override: {HOST_HEADER}")

    app.state.client = httpx.AsyncClient(
        follow_redirects=False,
        verify=False,
        timeout=15.0,
    )

@app.on_event("shutdown")
async def shutdown():
    print("Bridge shutting down")
    await app.state.client.aclose()

@app.post("/{path:path}")
async def forward(request: Request, path: str):

    body = await request.body()

    print(f"Incoming request: {request.method} {request.url.path}")
    print(f"Query string: {request.url.query or 'None'}")
    print(f"Content length: {len(body)} bytes")

    filtered_headers = {}

    for name, value in request.headers.items():

        lower = name.lower()

        if lower in HOP_BY_HOP:
            print(f"Skipping hop-by-hop header: {name}")
            continue

        if lower == "host":
            print("Replacing Host header")
            continue

        filtered_headers[name] = value

    filtered_headers["Host"] = HOST_HEADER

    upstream_url = f"https://{CORE_IP}{FORWARD_PATH}"

    print(f"Forwarding to upstream URL: {upstream_url}")
    print(f"Forwarding with {len(filtered_headers)} headers")

    try:
        response = await app.state.client.post(
            upstream_url,
            content=body,
            headers=filtered_headers,
        )

        print(f"Upstream responded with status: {response.status_code}")

    except httpx.TimeoutException:
        print("Upstream timeout")
        return Response("Upstream timeout", status_code=504)

    except httpx.RequestError as error:
        print(f"Upstream request error: {error}")
        return Response("Upstream connection error", status_code=502)

    outgoing_headers = {}

    for name, value in response.headers.items():

        lower = name.lower()

        if lower in HOP_BY_HOP:
            continue

        if lower == "content-length":
            continue

        outgoing_headers[name] = value

    print(f"Returning response to caller with status {response.status_code}")

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=outgoing_headers,
    )