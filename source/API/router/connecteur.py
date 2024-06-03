from fastapi import Request
from fastapi import APIRouter
from concurrent.futures import ThreadPoolExecutor
import threading
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import FastAPI, Depends, HTTPException, status
from utils.utils import load_config, get_structured_data, run_webhook, test_json_zone, get_majdata_and_geofencing_force_alert
from models.models import insert_structured, insert_raw, query_process, insert_telemetry
from utils.telemetry import get_telemetry_data

# path file config
CONFIG_PATH = "config/config.json"
# load config
_, _, CONFIG_MAPPING, CONFIG_SECURITY,_ = load_config(
    CONFIG_PATH)

# Utilisation d'un ThreadPoolExecutor pour gerer les threads en arriere-plan
executor = ThreadPoolExecutor(max_workers=5)  # Vous pouvez ajuster le nombre de threads

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


# oem_http
@router.post("/oem_http")
async def receive_data_from_oem_server_v2(request: Request, username: str = Depends(verify_credentials)):
    try:
        data = await request.json()
        print(data)
        #insert_raw(data, "oem_http")
        insert_structured(get_structured_data(data, CONFIG_MAPPING, "oem_http"))
        insert_telemetry(get_telemetry_data(data))
        if executor._work_queue.qsize() < 1:
            executor.submit(run_webhook)
        #executor.submit(run_webhook)
        #run_webhook()

        return ""
    except Exception as e:
        print(f'[ERROR][receive_data_from_oem_server_v2][request.json] {e}')
        return ""

# receive data telematic guru webhook
@router.post("/send_data_tg")
async def receive_data_from_telematics_guru(request: Request, username: str = Depends(verify_credentials)):
    try:
        data = await request.json()
        print(data)
        #insert_raw(data, "send_data_tg")
        insert_structured(get_structured_data(data, CONFIG_MAPPING, "send_data_tg"))
        insert_telemetry(get_telemetry_data(data))
        if executor._work_queue.qsize() < 1:
            executor.submit(run_webhook)
        #executor.submit(run_webhook)
        #run_webhook()
        return ""
    except Exception as e:
        print(f'[ERROR][receive_data_from_telematics_guru][request.json] {e}')
        return ""


# receive date OEM webhook
@router.post("/send_data_oem")
async def receive_data_from_oem_server_v1(request: Request, username: str = Depends(verify_credentials)):
    try:
        data = await request.json()
        print(data)
        #insert_raw(data, "send_data_oem")
        insert_structured(get_structured_data(data, CONFIG_MAPPING, "send_data_oem"))
        insert_telemetry(get_telemetry_data(data))
        if executor._work_queue.qsize() < 1:
            executor.submit(run_webhook)
        #executor.submit(run_webhook)
        #run_webhook()
        return ""
    except Exception as e:
        print(f'[ERROR][receive_data_from_oem_server_v1][request.json] {e}')
        return ""


