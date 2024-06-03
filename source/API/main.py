#############################################################################################
#   FASTAPI API CALCUL
#   version : 1.0.0
#############################################################################################

import json
import uvicorn
import datetime
from router import webhook
from router import connecteur
from utils.utils import load_config
from utils.telemetry import load_telemetry_config
from fastapi import Request, FastAPI
from models.models import bdd_connection, load_ref_product
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# path file config
CONFIG_PATH = "config/config.json"
# load config
CONFIG_POSTGRES, CONFIG_UVICORN, _, _,REF_PRODUCT = load_config(
    CONFIG_PATH)
# load telemetry config
_,_,_, = load_telemetry_config(CONFIG_PATH)

# make connection to bdd postgres
bdd_connection(CONFIG_POSTGRES)
# load ref-name product
load_ref_product(REF_PRODUCT)

# include API correcteur
app.include_router(webhook.router, tags=['Webhook Engine'])
app.include_router(connecteur.router, tags=['Connecteur OEM/TG'])



if __name__ == '__main__':
    uvicorn. run(
        app, host=CONFIG_UVICORN["HOST"], port=CONFIG_UVICORN["PORT"])
