import logging
import socket
from os import listdir
from os.path import isdir, isfile, join
import sys

import docker
import importlib.util

from fastapi import FastAPI, Request


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stderr))


module_path = "./services"

modules = [
    f.replace(".py", "")
    for f in listdir(module_path)
    if
        (
            isfile(join(module_path, f))  and
            f.endswith(".py")
        ) or (
            isdir(join(module_path, f)) and
            isfile(join(module_path, f, "__init__.py"))
        )
]


try:
    client = docker.from_env()

    hostname = socket.gethostname()
    container = client.containers.get(hostname)
    networks = container.attrs['NetworkSettings']['Networks']

    if len(networks) != 1:
        logger.info("The service should only be connected to one network")
        raise Exception("Multiple networks connected. Won't register aliases")

    network_id = list(networks.values())[0]['NetworkID']
    network = client.networks.get(network_id)

    logger.info(f"Connecting container to network with aliases {modules}")
    try:
        aliases = container.attrs["NetworkSettings"]["Networks"][network.name]["Aliases"]
        network.disconnect(container)
        network.connect(container, aliases=[*aliases, *modules])
    except Exception:
        logger.error("Unable to register aliases to container")
except Exception:
    logger.warn(
        "Unable to get docker container or network."
        " Only path endpints will be exposed"
    )


app = FastAPI()


@app.middleware("http")
async def route_by_domain(request: Request, call_next):
    host = request.headers.get("host")

    if host is not None and host != "localhost":
        domain = host.split(":")[0]
        if domain in modules:
            request.scope["path"] = f"/{domain}{request.scope['path']}"

    return await call_next(request)


for module_name in modules:
    logger.info(f"Loading {module_name} app")
    module = importlib.import_module(f"services.{module_name}")
    app.include_router(module.router, prefix=f"/{module_name}")
