# Fake Servicer

[FastAPI](https://fastapi.tiangolo.com/) server that autoloads and hot-reloads 
services defined in files stored in `/app/services`. Each file can define a
service using a standard FastAPI [Router](https://fastapi.tiangolo.com/tutorial/bigger-applications/?h=router#apirouter).

```python
# ./mocked-services/some_service.py
from fastapi import Router
from pydantic import BaseModel

router = Router()


class ThingResponse(BaseModel):
  id: int
  name: str


@router.get('/thing', response={200: ThingResponse, 403: str})
def get_thing(id: number):
  import random

  if random.random() < 0.1:
    return 403, "Auth error"

  return 200, { "id": id, "name": faker.name() }
```

You can then serve it on a docker compose project by defining a new service

```yaml
services:
  # ... your real services

  fake-services:
    image: fake-servicer
    volumes: ['./mocked-services:/app/services']
    mounts: ['/var/run/docker.sock']
```

While mounting the docker socket is optional, if available, the service will
reattach the container to its only network and set each found mocked service
name as an alias for the container. By doing this other containers on the same
network can access the mocked services by using `http://some_service` as the
base url (i.e. port 80 o host with the same name as the python module defining
the router).

The services will also be available on `http://fake-services/some_service` which
will work even when no docker socket is found.

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

## Possible not yet implemented extensions

## Admin urls (WIP)
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

## Next request response override (WIP)
By including a `X-Fake-Servicer-Next-Request-{Status,Body,Headers}` header, any
the specified response object will be overriden. This allows using the same
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

One caveat of this approach is that the application stops being
completely stateless, thus not completely thread or race-condition safe. Two
parallel tests may try to override the same endpoint in a short span of time
which would almost definitely end up in flaky tests.
