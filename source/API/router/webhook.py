import asyncio
import json
from fastapi import Request
from fastapi import APIRouter
from models.models import sv_api
from models.models import upd_api
from models.models import del_api
from models.models import get_all_api
from utils.utils import load_config
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import FastAPI, Depends, HTTPException, status

# path file config
CONFIG_PATH = "config/config.json"
# load config
_, _, _, CONFIG_SECURITY,_ = load_config(
    CONFIG_PATH)


router = APIRouter()
security = HTTPBasic()


# Fonction pour verifier les informations d'authentification
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = CONFIG_SECURITY["LOGIN_ENDPT"]
    correct_password = CONFIG_SECURITY["PWD_ENDPT"]
    if credentials.username == correct_username and credentials.password == correct_password:
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Mauvaises informations d'identification",
        headers={"WWW-Authenticate": "Basic"},
    )


# save_api
@router.post("/sv_api")
async def save_api_webhook(request: Request, username: str = Depends(verify_credentials)):
    """
    Create a new API.
    
    Possible responses:
    - "success": Operation succeeded.
    - "error": Error during the operation.
    """

    data = await request.json()
    message = sv_api(data)
    return message


# upd_api
@router.put("/upd_api")
async def update_api(request: Request, username: str = Depends(verify_credentials)):
    """
    Update API.
    
    Possible responses:
    - "success": Operation succeeded.
    - "error": Error during the operation.
    """
    data = await request.json()
    message = upd_api(data)
    return message


# del_api
@router.delete("/del_api")
async def delete_api(request: Request, username: str = Depends(verify_credentials)):
    """
    delete API.
    
    Possible responses:
    - "success": Operation succeeded.
    - "error": Error during the operation.
    """

    data = await request.json()
    message = del_api(data)
    return message
    

# get_all_webhook
@router.get("/get_api_webhook")
async def get_api_webhook(request: Request, username: str = Depends(verify_credentials)):
    return get_all_api('webhook')
    


# get_all_geofencing
@router.get("/get_api_geofencing")
async def get_api_geofencing(request: Request, username: str = Depends(verify_credentials)):
    return get_all_api('geofencing')


# get_all_telemetry
@router.get("/get_api_telemetry")
async def get_api_telemetry(request: Request, username: str = Depends(verify_credentials)):
    return get_all_api('telemetry')


# get_all_telemetry
@router.get("/get_api_analysis")
async def get_api_analysis(request: Request, username: str = Depends(verify_credentials)):
    return get_all_api('analysis')

