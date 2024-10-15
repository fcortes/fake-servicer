# Fake Servicer

Tiny FastAPI-based mock server that lets you implement mock APIs quickly, without complex setups or having to rely on external staging or test service.

It dynamically reads and realoads the python modules defined on `/app/services`
that expose a standard [FastAPI Router](https://fastapi.tiangolo.com/tutorial/bigger-applications/?h=router#apirouter) named `router`.

Mocked endpoints can be added to the `router` using pydantic typing for easy validation.

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
    image: ghcr.io/fcortes/fake-servicer
    volumes: ['./mocked-services:/app/services']
    mounts: ['/var/run/docker.sock:/var/run/docker.sock']
```

Containers connected to the same network (the default docker compose project 
network in the previous example) can access mocked endpoints by making requests
to any of the following urls

- `http://some_service/some-endpoint` (only if the docker socket is mounted)
- `http://fake-services/some_service/some-endpoint`

## Demo

You can setup a quick working demo by cloning this repository and running
`docker compose up`. After the container is built and the server is up, you can
run the following commands to test some mocked endpoints

```
docker compose run --rm http http://example/users
docker compose run --rm http http://other_service/users
docker compose run --rm http http://fake-services/example/users
docker compose run --rm http http://fake-services/other_service/users
```

## (WIP) Dynamic configuration

The following are ideas for defining some sort of admin API allowing dynamic control of the mocked services.
I don't think any of them is ready to be implemented.

Ideally this would allow to write integration tests as follows
```python
import requests

def test_enpoint_with_depending_service(client, env):
  requests.post(
    "/__admin/override-next-request",
    json.dumps({
      "request": {"method": "POST", "path": "/do-something"},
      "response": {"body": "OK!", "status": "201"},
    }),
  )

  res = client.post("/the/endpoint/to/be/tested")

  assert res.code == 200
  assert res.body == "Response message: OK!"
```

One problem with these solutions (except for the last one) is that the
service is no longer completely stateless, so not completely multi-client
or race-condition safe either. Two parallel tests may try to override the
same endpoint in a short span of time which may end up producing flaky tests.

### Admin urls
Dynamically control the behaviour of endpoints by making
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

### Sessions
Create sessions that can dynamically modify the behavior of the mock service

```js
// GET /a-service-name/hello
// Host: mock-services
// 200 World!

// POST /__admin/create-session { "service": "a-service-name" }
// 201 293827837

// GET /293827837/hello
// Host: mock-services
// 200 World!

// PUT /__session/293827837/rule
// { "request": { "method": "GET", "path": "/hello" }, "response": { "body": "goodbye!" } }

// GET /293827837/hello
// Host: mock-services
// 200 goodbye!
```

Sessions could be garbage collected using a lru cache
