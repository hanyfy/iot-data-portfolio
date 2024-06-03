import requests
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.conf import settings

_BASE_URL_ = settings._BASE_URL_
_LOGIN_ENDPT_ = settings._LOGIN_ENDPT_
_PWD_ENDPT_ = settings._PWD_ENDPT_
_AUTH_=(_LOGIN_ENDPT_, _PWD_ENDPT_)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Redirige vers votre vue de connexion

    def dispatch(self, request, *args, **kwargs):
        # Ajoutez ici toute logique supplémentaire si nécessaire
        return super().dispatch(request, *args, **kwargs)


def request_api(endpoint, data=[]):
    # auth=(username, password)
    try:
        if "get" in endpoint:
            response = requests.get(_BASE_URL_+endpoint, json=data, headers={'Content-Type': 'application/json'}, auth=_AUTH_)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        
        elif "upd" in endpoint:
            response = requests.put(_BASE_URL_+endpoint, json=data, headers={'Content-Type': 'application/json'}, auth=_AUTH_)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        
        if "del" in endpoint:
            response = requests.delete(_BASE_URL_+endpoint, json=data, headers={'Content-Type': 'application/json'}, auth=_AUTH_)
            if response.status_code == 200:
                return response.json()
            else:
                return []
        else:
            response = requests.post(_BASE_URL_+endpoint, json=data, headers={'Content-Type': 'application/json'}, auth=_AUTH_)
            if response.status_code == 200:
                return response.json()
            else:
                return []
    except Exception as e:
        return []


def get_url_api(_type_):
    if _type_ == "webhook":
        return request_api("get_api_webhook")
    elif _type_ == "telemetry":
        return request_api("get_api_telemetry")
    if _type_ == "analysis":
        return request_api("get_api_analysis")
    else:
        return request_api("get_api_geofencing")


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('webhook')
        else:
            messages.error(request, 'login ou mot de passe incorrect..')
    return render(request, 'registration/login.html')



def sv_webhook(request):
    if request.method == 'POST':
        env = request.POST['env_wh']
        name = request.POST['name_wh']
        description = request.POST['description_wh']
        url = request.POST['url_wh']
        login = request.POST['login_wh']
        password = request.POST['pwd_wh']
        status = 0
        if request.POST.get('status_wh') != None:
            status = 1
        hk1 = request.POST['hk1_wh']
        hk2 = request.POST['hk2_wh']
        hk3 = request.POST['hk3_wh']
        hk4 = request.POST['hk4_wh']
        hv1 = request.POST['hv1_wh']
        hv2 = request.POST['hv2_wh']
        hv3 = request.POST['hv3_wh']
        hv4 = request.POST['hv4_wh']
        print("[INFO][sv_webhook][INSERT]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [("webhook", env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4 )]
        message = request_api("sv_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][sv_webhook][INSERT] "+message)
        return redirect('webhook')


def upd_webhook(request, id):
    if request.method == 'POST':
        env = request.POST['env_wh'+'_'+str(id)]
        name = request.POST['name_wh'+'_'+str(id)]
        description = request.POST['description_wh'+'_'+str(id)]
        url = request.POST['url_wh'+'_'+str(id)]
        login = request.POST['login_wh'+'_'+str(id)]
        password = request.POST['pwd_wh'+'_'+str(id)]
        status = 0
        if request.POST.get('status_wh'+'_'+str(id)) != None:
            status = 1
        hk1 = request.POST['hk1_wh'+'_'+str(id)]
        hk2 = request.POST['hk2_wh'+'_'+str(id)]
        hk3 = request.POST['hk3_wh'+'_'+str(id)]
        hk4 = request.POST['hk4_wh'+'_'+str(id)]
        hv1 = request.POST['hv1_wh'+'_'+str(id)]
        hv2 = request.POST['hv2_wh'+'_'+str(id)]
        hv3 = request.POST['hv3_wh'+'_'+str(id)]
        hv4 = request.POST['hv4_wh'+'_'+str(id)]
        print("[INFO][upd_webhook][UPDATE]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [(env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4, id )]
        message = request_api("upd_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][upd_webhook][UPDATE] "+message)

        return redirect('webhook')


def del_webhook(request, id):
    if request.method == 'POST':
        print("[INFO][del_webhook][DELETE]", str(id))
        data = [(id, )]
        message = request_api("del_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][del_webhook][DELETE] "+message)
        return redirect('webhook')


def sv_geofencing(request):
    if request.method == 'POST':
        env = request.POST['env_gf']
        name = request.POST['name_gf']
        description = request.POST['description_gf']
        url = request.POST['url_gf']
        login = request.POST['login_gf']
        password = request.POST['pwd_gf']
        status = 0
        if request.POST.get('status_gf') != None:
            status = 1
        hk1 = request.POST['hk1_gf']
        hk2 = request.POST['hk2_gf']
        hk3 = request.POST['hk3_gf']
        hk4 = request.POST['hk4_gf']
        hv1 = request.POST['hv1_gf']
        hv2 = request.POST['hv2_gf']
        hv3 = request.POST['hv3_gf']
        hv4 = request.POST['hv4_gf']

        print("[INFO][sv_geofencing][INSERT]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [("geofencing", env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4 )]
        message = request_api("sv_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][sv_geofencing][INSERT] "+message)

        return redirect('webhook')



def upd_geofencing(request, id):
    if request.method == 'POST':
        env = request.POST['env_gf'+'_'+str(id)]
        name = request.POST['name_gf'+'_'+str(id)]
        description = request.POST['description_gf'+'_'+str(id)]
        url = request.POST['url_gf'+'_'+str(id)]
        login = request.POST['login_gf'+'_'+str(id)]
        password = request.POST['pwd_gf'+'_'+str(id)]
        status = 0
        if request.POST.get('status_gf'+'_'+str(id)) != None:
            status = 1
        hk1 = request.POST['hk1_gf'+'_'+str(id)]
        hk2 = request.POST['hk2_gf'+'_'+str(id)]
        hk3 = request.POST['hk3_gf'+'_'+str(id)]
        hk4 = request.POST['hk4_gf'+'_'+str(id)]
        hv1 = request.POST['hv1_gf'+'_'+str(id)]
        hv2 = request.POST['hv2_gf'+'_'+str(id)]
        hv3 = request.POST['hv3_gf'+'_'+str(id)]
        hv4 = request.POST['hv4_gf'+'_'+str(id)]

        print("[INFO][upd_geofencing][UPDATE]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [(env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4, id )]
        message = request_api("upd_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][upd_geofencing][UPDATE] "+message)

        return redirect('webhook')


def del_geofencing(request, id):
    if request.method == 'POST':
        print("[INFO][del_webhook][DELETE]", str(id))
        data = [(id, )]
        message = request_api("del_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][del_geofencing][DELETE] "+message)        
        return redirect('webhook')


def sv_telemetry(request):
    if request.method == 'POST':
        env = request.POST['env_tel']
        name = request.POST['name_tel']
        description = request.POST['description_tel']
        url = request.POST['url_tel']
        login = request.POST['login_tel']
        password = request.POST['pwd_tel']
        status = 0
        if request.POST.get('status_tel') != None:
            status = 1
        hk1 = request.POST['hk1_tel']
        hk2 = request.POST['hk2_tel']
        hk3 = request.POST['hk3_tel']
        hk4 = request.POST['hk4_tel']
        hv1 = request.POST['hv1_tel']
        hv2 = request.POST['hv2_tel']
        hv3 = request.POST['hv3_tel']
        hv4 = request.POST['hv4_tel']

        print("[INFO][sv_telemetry][INSERT]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [("telemetry", env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4 )]
        message = request_api("sv_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][sv_telemetry][INSERT] "+message)

        return redirect('webhook')



def upd_telemetry(request, id):
    if request.method == 'POST':
        env = request.POST['env_tel'+'_'+str(id)]
        name = request.POST['name_tel'+'_'+str(id)]
        description = request.POST['description_tel'+'_'+str(id)]
        url = request.POST['url_tel'+'_'+str(id)]
        login = request.POST['login_tel'+'_'+str(id)]
        password = request.POST['pwd_tel'+'_'+str(id)]
        status = 0
        if request.POST.get('status_tel'+'_'+str(id)) != None:
            status = 1
        hk1 = request.POST['hk1_tel'+'_'+str(id)]
        hk2 = request.POST['hk2_tel'+'_'+str(id)]
        hk3 = request.POST['hk3_tel'+'_'+str(id)]
        hk4 = request.POST['hk4_tel'+'_'+str(id)]
        hv1 = request.POST['hv1_tel'+'_'+str(id)]
        hv2 = request.POST['hv2_tel'+'_'+str(id)]
        hv3 = request.POST['hv3_tel'+'_'+str(id)]
        hv4 = request.POST['hv4_tel'+'_'+str(id)]

        print("[INFO][upd_telemetry][UPDATE]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [(env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4, id )]
        message = request_api("upd_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][upd_telemetry][UPDATE] "+message)

        return redirect('webhook')


def del_telemetry(request, id):
    if request.method == 'POST':
        print("[INFO][del_telemetry][DELETE]", str(id))
        data = [(id, )]
        message = request_api("del_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][del_telemetry][DELETE] "+message)        
        return redirect('webhook')



def sv_analysis(request):
    if request.method == 'POST':
        env = request.POST['env_ana']
        name = request.POST['name_ana']
        description = request.POST['description_ana']
        url = request.POST['url_ana']
        login = request.POST['login_ana']
        password = request.POST['pwd_ana']
        status = 0
        if request.POST.get('status_ana') != None:
            status = 1
        hk1 = request.POST['hk1_ana']
        hk2 = request.POST['hk2_ana']
        hk3 = request.POST['hk3_ana']
        hk4 = request.POST['hk4_ana']
        hv1 = request.POST['hv1_ana']
        hv2 = request.POST['hv2_ana']
        hv3 = request.POST['hv3_ana']
        hv4 = request.POST['hv4_ana']

        print("[INFO][sv_analysis][INSERT]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [("analysis", env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4 )]
        message = request_api("sv_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][sv_analysis][INSERT] "+message)

        return redirect('webhook')



def upd_analysis(request, id):
    if request.method == 'POST':
        env = request.POST['env_ana'+'_'+str(id)]
        name = request.POST['name_ana'+'_'+str(id)]
        description = request.POST['description_ana'+'_'+str(id)]
        url = request.POST['url_ana'+'_'+str(id)]
        login = request.POST['login_ana'+'_'+str(id)]
        password = request.POST['pwd_ana'+'_'+str(id)]
        status = 0
        if request.POST.get('status_ana'+'_'+str(id)) != None:
            status = 1
        hk1 = request.POST['hk1_ana'+'_'+str(id)]
        hk2 = request.POST['hk2_ana'+'_'+str(id)]
        hk3 = request.POST['hk3_ana'+'_'+str(id)]
        hk4 = request.POST['hk4_ana'+'_'+str(id)]
        hv1 = request.POST['hv1_ana'+'_'+str(id)]
        hv2 = request.POST['hv2_ana'+'_'+str(id)]
        hv3 = request.POST['hv3_ana'+'_'+str(id)]
        hv4 = request.POST['hv4_ana'+'_'+str(id)]

        print("[INFO][upd_analysis][UPDATE]", env, name, description, url, login, password,status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4)
        data = [(env, name, description, url, login, password, status,  hk1, hk2, hk3, hk4, hv1, hv2, hv3, hv4, id )]
        message = request_api("upd_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][upd_analysis][UPDATE] "+message)

        return redirect('webhook')


def del_analysis(request, id):
    if request.method == 'POST':
        print("[INFO][del_analysis][DELETE]", str(id))
        data = [(id, )]
        message = request_api("del_api", data=data)
        if isinstance(message, list):
            message = "error"
        messages.info(request, "[INFO][del_analysis][DELETE] "+message)        
        return redirect('webhook')



@login_required(login_url='login')
def webhook(request):
    
    data = {}
    data["data_webhook"] = get_url_api("webhook")
    data["data_geofencing"] = get_url_api("geofencing")
    data["data_telemetry"] = get_url_api("telemetry")
    data["data_analysis"] = get_url_api("analysis")

    return render(request, 'webhook/webhook.html', data)


