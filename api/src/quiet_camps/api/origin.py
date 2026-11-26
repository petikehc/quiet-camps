"""Behind CloudFront: answer only requests that came through it, and know each viewer's address.

On AWS the API is a Lambda function URL, which anyone could call directly. CloudFront adds a
secret header on its way to the function, and the API turns away requests without it.
"""

import hmac
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from quiet_camps.api.problems import problem

ORIGIN_HEADER = "x-origin-verify"


def require_origin_secret(app: FastAPI, secret: str) -> None:
    async def from_cloudfront_only(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        sent = request.headers.get(ORIGIN_HEADER, "")
        if not hmac.compare_digest(sent.encode(), secret.encode()):  # in constant time
            return problem(403, "Use the site's own address.")
        return await call_next(request)

    app.middleware("http")(from_cloudfront_only)


def client_ip(request: Request, header: str | None) -> str:
    """The viewer's address: from `header` when it's set and sent, else the connection's.

    CloudFront-Viewer-Address is "address:port", for IPv6 too (without brackets). CloudFront
    sets it itself, so unlike X-Forwarded-For a viewer can't choose it.
    """
    if header and (value := request.headers.get(header)):
        return value.rsplit(":", 1)[0]
    return request.client.host if request.client else "unknown"
