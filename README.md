# Fake Servicer

Minimalistic FastAPI-based mock server that lets you simulate APIs quickly, without complex setups or waiting for real service

It dynamically reads and realoads the python modules defined on `/app/services`
which must expose a standard [FastAPI Router](https://fastapi.tiangolo.com/tutorial/bigger-applications/?h=router#apirouter) named `router` with any required mocked endpoint.

```python
# ./mocked-services/some_service.py
from fastapi import Router
from pydantic import BaseModel

router = Router()


class ThingResponse(BaseModel):
  id: int
  name: str


@router.get('/thing/{id}', response_model=ThingResponse)
def get_thing(id: int):
  return 200, { "id": id, "name": "plumbus" }
```

You can then add it as a new service into your project docker compose file so
it exposes all mock endpoints to the connected containers

```yaml
services:
  # ... your real services

  fake-services:
    image: fake-servicer
    volumes: ['./mocked-services:/app/services']
    mounts: ['/var/run/docker.sock']
```

Containers connected to the same network (the default docker compose project 
network in the previous example) can access mocked endpoints by making requests
to
- `http://some_service/some-endpoint` (only if the docker socket is mounted)
- `http://fake-services/some_service/some-endpoint`

## Demo

You can setup a quick working demo by cloning this repository and running
`docker compose up`. After the container is built and the server is up, you can
run the following commands to test some mocked endpoints

```
docker compose run --rm http http://example/users
docker compose run --rm http http://other_service/users
docker compose run --rm http http://mock-services/example/users
docker compose run --rm http http://mock-services/other_service/users
```

## Possible (not yet implemented) extensions

### Admin urls (WIP)
You'll also be able to dynamically control the behaviour of endpoints by making
requests to admin endpoints on the `/__admin` namespace.

```js
// POST `/__admin/responses`
{
  "filter": [
    "path": "/some-path",
  ],
  "response": "",
}
```

### Next request response override (WIP)
By including a `X-Fake-Servicer-Next-Request-{Status,Body,Headers}` header, the
specified response object will be overriden. This allows using the same
endpoints to simulate errors or other conditions

```python
import requests
import json


def test_some_service_auth_error_shows_relevant_message(client):
    requests.get("http://some_service/users", headers={
        "X-Fake-Servicer-Next-Request-Status": "403",
        "X-Fake-Servicer-Next-Request-Body": json.dumps({
            "status": "error",
            "detail": "Authentication error",
        }),
        "X-Fake-Servicer-Next-Request-Headers": json.dumps({
            "Content-Type": "application/json",
        }),
    })

    res = client.post("/calculate-some-service-users-stats")

    assert res.status_code == 502
    assert res.json()["detail"] == "Error fetching users from some service: Authentication error"

```

One caveat of these approaches is that the application is not longer completely
stateless, so not completely "multi-client" or race-condition safe either. Two
parallel tests may try to override the same endpoint in a short span of time
which may end up producing flaky tests.
