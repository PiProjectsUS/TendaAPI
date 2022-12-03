import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from Helper.Tenda import TendaManager

from Conf import *

Manager = TendaManager(ROUTER_URL, ROUTER_PASS)
Manager.track_online_run()

app = FastAPI()
security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = AUTH_USER.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = AUTH_PASS.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/")
async def root():
    return {"message": "TendaRouter-API"}


@app.get("/client/list/")
async def say_hello(credentials: HTTPBasicCredentials = Depends(security)):
    Manager.get_online_devices_with_stats()
    return Manager.online_log


@app.get("/client/block/name/")
async def say_hello(name: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if Manager.online_log[ip]['Named'].casefold() == name.casefold():
            return Manager.block_device(Manager.online_log[ip]['MAC'])
    return {"error": "Client Not Found"}


@app.get("/client/block/mac/")
async def say_hello(mac: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if Manager.online_log[ip]['MAC'].casefold() == mac.casefold():
            return Manager.block_device(Manager.online_log[ip]['MAC'])
    return {"error": "Client Not Found"}


@app.get("/client/block/ip/")
async def say_hello(ip_addr: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if ip_addr == ip:
            return Manager.block_device(Manager.online_log[ip]['IP'])
    return {"error": "Client Not Found"}


@app.get("/client/unblock/name/")
async def say_hello(name: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if Manager.online_log[ip]['Named'].casefold() == name.casefold():
            return Manager.unblock_device(Manager.online_log[ip]['MAC'])
    return {"error": "Client Not Found"}


@app.get("/client/unblock/mac/")
async def say_hello(mac: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if Manager.online_log[ip]['MAC'].casefold() == mac.casefold():
            return Manager.unblock_device(Manager.online_log[ip]['MAC'])
    return {"error": "Client Not Found"}


@app.get("/client/unblock/ip/")
async def say_hello(ip_addr: str, credentials: HTTPBasicCredentials = Depends(security)):
    for ip in Manager.online_log:
        if ip_addr == ip:
            return Manager.unblock_device(Manager.online_log[ip]['IP'])
    return {"error": "Client Not Found"}
