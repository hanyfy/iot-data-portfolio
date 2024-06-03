import json
import time
import base64
import datetime
import requests
import folium
import math
import random
from shapely.geometry import Point, Polygon
from models.models import get_last_tracker_info, get_2last_tag_acc, get_lastmaj_data_for_all_device, get_api_active, save_log
from models.models import get_lastmaj_data_for_specific_device
from models.models import get_lastmaj_telemetry, get_lastmaj_analysis

REF_PRODUCT = {}
############################## CONFIG READER ####################################

def load_json_file(file):
    # open json file
    with open(file, 'r') as json_file:
        data = json.load(json_file)
    return data


def load_config(json_path):
    # load config from json file
    CONFIG_POSTGRES = load_json_file(json_path)["POSTGRES"]
    CONFIG_UVICORN = load_json_file(json_path)["UVICORN"]
    CONFIG_MAPPING = load_json_file(json_path)["MAPPING"]
    CONFIG_SECURITY = load_json_file(json_path)["SECURITY"]
    CONFIG_PRODUCT = load_json_file(json_path)["PRODUCT"]

    global REF_PRODUCT
    REF_PRODUCT = CONFIG_PRODUCT

    return CONFIG_POSTGRES, CONFIG_UVICORN, CONFIG_MAPPING, CONFIG_SECURITY, CONFIG_PRODUCT


############################## ENCODE/DECODE TOOLS ####################################

def decode_hex(base64_encoded_data):

    # Decode base64-encoded data
    decoded_bytes = base64.b64decode(base64_encoded_data)

    # Convert the bytes to hexadecimal representation
    hex_representation = " ".join(f"{byte:02X}" for byte in decoded_bytes)

    return hex_representation


def decode_mac_address(hex_mac="", reversed_=True):

    # Split the hex sequence into individual bytes
    if reversed_:
        hex_bytes = reversed(hex_mac.split(" "))
    else:
        hex_bytes = hex_mac.split(" ")

    # Convert hex bytes to integers and format them as MAC address parts
    mac_parts = [f"{int(byte, 16):02X}" for byte in hex_bytes]

    # Combine the MAC address parts
    mac_address = ":".join(mac_parts)

    return mac_address


def decode_ascii_name(hex_tag_name=""):

    # Split the hex sequence into individual bytes
    hex_bytes = hex_tag_name.split()

    # Convert hex bytes to ASCII characters
    ascii_string = "".join([chr(int(byte, 16)) for byte in hex_bytes])

    # Remove null characters
    ascii_string = ascii_string.rstrip("\x00")

    return ascii_string


def decode_acceleration_nok(hex_acc=""):

    # Convert hex representation to signed integer (assuming little-endian)
    acc = int.from_bytes(bytes(hex_acc.replace(
        " ", ""), 'utf-8'), byteorder='little', signed=True)

    # Divide by the scaling factor (1000000000) to get the acceleration in mG
    acc_mg = acc / 1000000000

    return acc_mg


def decode_acceleration(hex_acc=""):
    # Convert hex representation to bytes
    acc_bytes = bytes.fromhex(hex_acc)

    # Convert bytes to signed integer (assuming little-endian)
    acc = int.from_bytes(acc_bytes, byteorder='little', signed=True)

    # Divide by the scaling factor (1000) to get the acceleration in mG
    acc_mg = acc / 1000

    return acc_mg


def decode_data(data="", type_tag=13):
    try:
        hexa = decode_hex(data)

        if type_tag == 13:
            token = hexa.split(" ")
            hex_mac = " ".join(token[0:6])
            mac_address = decode_mac_address(hex_mac=hex_mac)
            hex_tag_name = " ".join(token[6:21])
            tag_name = decode_ascii_name(hex_tag_name=hex_tag_name)
            hex_acc_x = " ".join(token[21:23])
            hex_acc_y = " ".join(token[23:25])
            hex_acc_z = " ".join(token[25:27])
            acc_x = decode_acceleration(hex_acc=hex_acc_x)
            acc_y = decode_acceleration(hex_acc=hex_acc_y)
            acc_z = decode_acceleration(hex_acc=hex_acc_z)

            return [mac_address, tag_name, acc_x, acc_y, acc_z]
        else:
            return [None, None, None, None, None]
    except Exception as e:
        print(f"[ERROR][utils.utils.decode_data] {e}")
        return [None, None, None, None, None]


############################## DATE MANAGEMENT TOOLS ####################################


def parse_and_convert_date(date_string):
    # Formats de date que nous attendons en entrée
    input_formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]

    # Format de date de sortie (timestamp avec zone)
    output_format = "%Y-%m-%dT%H:%M:%SZ"
    
    try:
        # Parcours des formats d'entrée et tentative de conversion
        for input_format in input_formats:
            try:
                parsed_date = datetime.datetime.strptime(date_string, input_format)
                # Convertit la date en format de sortie
                converted_date = parsed_date.strftime(output_format)
                    
                return converted_date
            except ValueError:
                pass
            except UnicodeDecodeError  as e:
                print(f"[ERROR][utils.utils.parse_and_convert_date.UnicodeDecodeError] {e}")
                try:
                    utf8_encoded_string = date_string
                    decoded_unicode_string = utf8_encoded_string.decode("utf-8")
                    return parse_and_convert_date(decoded_unicode_string)
                except:
                    return None
        # Si aucun format ne correspond, renvoie None
    except Exception as e:
        print(f"[ERROR][utils.utils.parse_and_convert_date] {e}")
        return None
        

############################## JSON SEARCH ENGINE ####################################


def find_value_by_key(d, target_key, path=None,  parent_index=None):
    if path is None:
        path = []  # Initialiser le chemin

    target_key_lower = target_key.lower()
    results = []

    if isinstance(d, dict):
        for index, (key, value) in enumerate(d.items()):
            if key.lower() == target_key_lower:
                # Add parent_index, index, full path and value
                results.append((parent_index, index, path, value))
            results.extend(find_value_by_key(
                value, target_key, path + [key], parent_index))
    elif isinstance(d, list):
        for index, item in enumerate(d):
            results.extend(find_value_by_key(
                item, target_key, path + [index], index))

    return results


def find_value_by_listkey(d, target_key_list, path=None,  parent_index=None):
    try:
        for target_key in target_key_list:
            results = find_value_by_key(d, target_key)
            # return list of tuple (parent_index, index_key, full path, value)
            if len(results) > 0:
                return results
        return []
    except Exception as e:
        print(f"[ERROR][utils.utils.find_value_by_listkey] {e}")
        return []


def analog_search(json_data, list_key, analog_number):
    
    result = None
    output_ = find_value_by_listkey(
        json_data, list_key, path=None,  parent_index=None)

    try:
        if len(output_) > 0:
            for _,_,_,value in output_:
                if  isinstance(value, list):
                    for dict_value in value:
                        if isinstance(dict_value, dict):
                            if 'id' in dict_value.keys() and 'val' in dict_value.keys():
                                try:
                                    if int(dict_value['id']) == int(analog_number):
                                        result = dict_value['val']
                                        return result
                                except:
                                    pass
                            elif str(analog_number) in dict_value.keys():
                                try:
                                    result = dict_value[str(analog_number)]
                                    return result
                                except:
                                    pass
                        else: # format du donnees sconsider comme inconnu, pas de recherche possible
                            pass
                elif isinstance(value, dict):
                    if str(analog_number) in value.keys():
                        try:
                            result = value[str(analog_number)]
                            return result
                        except:
                            pass
                else:
                    if value is not None and value != "":
                        return value
            return result
        else:
            return result
    except Exception as e:
        print(f"[ERROR][utils.utils.analog_search] {e}")
        return None




def get_voltage_batt(json_data, list_key):

    analog_number = 1
    try:
        res = analog_search(json_data, list_key, analog_number)
        if res is not None and res != "":
            return int(res)/1000
        else:
            return None
    except Exception as e:
        print(f"[ERROR][utils.utils.get_voltage_batt] {e}")
        return None


def get_ACC_tracker(json_data, list_key, analog_number):

    try:
        res = analog_search(json_data, list_key, analog_number)
        if res is not None and res != "":
            return int(res)/1000
        else:
            return None
    except Exception as e:
        print(f"[ERROR][utils.utils.get_ACC_tracker] {e}")
        return None


def get_temperature(json_data, list_key):

    analog_number = 3
    try:
        res = analog_search(json_data, list_key, analog_number)
        if res is not None and res != "":
            return int(res)/100
        else:
            return None
    except Exception as e:
        print(f"[ERROR][utils.utils.get_temperature] {e}")
        return None 


def get_data(json_data, list_key, index=0):
    
    try:
        output_ = find_value_by_listkey(
            json_data, list_key, path=None,  parent_index=None)

        if len(output_) > 0:
            result = output_[index][3]
            if result == '':
                return None
            return result
    except Exception as e:    
        print(f"[ERROR][utils.utils.get_data] {e}")
        return None

def get_highG_data(json_data, CONFIG_MAPPING):
    try:
        PEAK = None
        AVERAGE = None
        DURATION = None
        output_ = find_value_by_listkey(
            json_data, CONFIG_MAPPING["PEAK"], path=None,  parent_index=None)
        list_peak = []
        if len(output_) > 0:
            for tup in output_:
                list_peak.append(int(tup[3]))
            PEAKINDEX = max(list_peak)
            PEAK = max(list_peak)/1000
            try:
                AVERAGE = get_data(json_data, CONFIG_MAPPING["AVERAGE"], index=list_peak.index(PEAKINDEX))/1000
            except Exception as e:
                print(f"EXCEPT AVERAGE {e} {list_peak.index(PEAK)}")   
            try:
                DURATION = get_data(json_data, CONFIG_MAPPING["DURATION"], index=list_peak.index(PEAKINDEX))
            except:
                pass
        return PEAK, AVERAGE, DURATION
    except Exception as e:    
        print(f"[ERROR][utils.utils.get_highG_data] {e}")
        return None, None, None


############################## METRIC COMPUTATION ####################################


def compute_activity_metric(mac_address, X2, Y2, Z2):
    try:
        (X0, Y0, Z0), (X1, Y1, Z1) = get_2last_tag_acc(mac_address) 
        accelerations = [X0, Y0, Z0, X1, Y1, Z1, X2, Y2, Z2]
        # compute activity metric
        if all(acc is not None for acc in accelerations):
            activity = abs((X0-X1)) + abs((Y0-Y1)) + abs((Z0-Z1)) + abs((X1-X2)) + abs((Y1-Y2)) + abs((Z1-Z2))
            #print(f"[DBG-INFO] {mac_address}, 2=> {X2}, {Y2}, {Z2}, 1=> {X1}, {Y1}, {Z1}, 0=> {X0}, {Y0}, {Z0}, activity=> {activity}")
            return activity 
        else:
            return None
    except Exception as e:
        print(f"[ERROR][utils.utils.compute_activity_metric] {e}")
        return None


############# RANDOM GEOLOCFOR TAG ###################################################

def gen_tag_coords(lat, lon, rssi):
    if rssi is None:
        try:
            rssi = random.randint(-100, -10) # -10 et - 100 sont les extremites trouve parmi les donnees dans la base et analysé, venant DE DM
        except:
            rssi = -10
        print(f"[RSSI NULL] {rssi}")
    try:
        rssi = float(rssi)    
        #distance=abs(rssi)/10
        distance=10**((abs(rssi)-47)/25)
        # Convertir la latitude et la longitude en radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        # Rayon de la Terre en mètres
        earth_radius = 6371000

        # Convertir la distance en degrés
        distance_in_degrees = distance / earth_radius

        # Choisir un angle aléatoire en radians
        angle = random.uniform(0, 2 * math.pi)

        # Calculer les nouvelles coordonnées
        new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(distance_in_degrees) +
                                math.cos(lat_rad) * math.sin(distance_in_degrees) * math.cos(angle))
        new_lon_rad = lon_rad + math.atan2(math.sin(angle) * math.sin(distance_in_degrees) * math.cos(lat_rad),
                                           math.cos(distance_in_degrees) - math.sin(lat_rad) * math.sin(new_lat_rad))

        # Convertir les nouvelles coordonnées en degrés
        tag_lat = math.degrees(new_lat_rad)
        tag_lon = math.degrees(new_lon_rad)
        return tag_lat, tag_lon, distance
    except Exception as e:
        print(f"[ERROR][utils.utils.gen_tag_coords] {e}")
        distance = 1
        try:
            distance=10**((abs(rssi)-47)/25)
        except:
            distance = 1
        return lat, lon, distance

############################## DATA STRUCT ENGINE ####################################

def get_structured_data(json_data, CONFIG_MAPPING, endpoint):


    #################################################################################################################################
    #                                               TRACKER DATA EXTRACTION                                                         #
    #################################################################################################################################

    # Initialisation
    type_oem = None
    date_oem = get_data(json_data, CONFIG_MAPPING["DATE"])
    date_oem_parse = parse_and_convert_date(date_oem) 
    sn_oem = get_data(json_data, CONFIG_MAPPING["SERIAL_NUMBER"])
    prod_oem = get_data(json_data, CONFIG_MAPPING["PROD"])
    
    try:
        prod_oem =  str(REF_PRODUCT[str(prod_oem)])+"|"+str(prod_oem) # save type device name and type device ID => Ex : Oyster3 4G BLE|102
    except:
        try:
            prod_oem = str(prod_oem)+"|"
        except:
            pass

    iccid_oem = get_data(json_data, CONFIG_MAPPING["ICCID"])
    imei_oem = get_data(json_data, CONFIG_MAPPING["IMEI"])
    lat_oem = get_data(json_data, CONFIG_MAPPING["LAT"])
    lng_oem = get_data(json_data, CONFIG_MAPPING["LNG"])
    posAcc_oem = get_data(json_data, CONFIG_MAPPING["POSACC"])
    mac_adress_oem = None
    tag_name_oem = None
    x_acc_oem = None
    y_acc_oem = None
    z_acc_oem = None
    activity = None
    RSSI = None
    if lat_oem is not None:
        type_oem = "Tracker"
    else:
        type_oem = "unknow"

    
    ALT = get_data(json_data, CONFIG_MAPPING["ALT"])
    CAP = get_data(json_data, CONFIG_MAPPING["CAP"])
    if CAP is not None:
        try:
            if endpoint != 'send_data_tg':
                CAP = int(CAP) * 2
        except Exception as e:
            pass

    PDOP = get_data(json_data, CONFIG_MAPPING["PDOP"])
    if PDOP is not None:
        try:
            if endpoint != 'send_data_tg':
                PDOP = int(PDOP) / 10
        except Exception as e:
            pass


    VOLT_BAT = get_voltage_batt(json_data, CONFIG_MAPPING["VOLT_BAT"])

    TEMPERATURE = get_temperature(json_data, CONFIG_MAPPING["TEMPERATURE"])

    DOUT = get_data(json_data, CONFIG_MAPPING["DOUT"])
    
    PEAK, AVERAGE, DURATION = get_highG_data(json_data, CONFIG_MAPPING)

    XACC_TRACKER = get_ACC_tracker(json_data, CONFIG_MAPPING["X"], 12)
    YACC_TRACKER = get_ACC_tracker(json_data, CONFIG_MAPPING["Y"], 13)
    ZACC_TRACKER = get_ACC_tracker(json_data, CONFIG_MAPPING["Z"], 14)

    return_tuple = (type_oem, date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, lat_oem,
                       lng_oem, posAcc_oem, mac_adress_oem, tag_name_oem, XACC_TRACKER, YACC_TRACKER, ZACC_TRACKER, 
                       activity, endpoint, ALT, CAP, PDOP, VOLT_BAT, TEMPERATURE, DOUT,
                       PEAK, AVERAGE, DURATION, RSSI)
    """
    condition_tuple = (date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, lat_oem,
                       lng_oem, posAcc_oem, mac_adress_oem, tag_name_oem, x_acc_oem, y_acc_oem, z_acc_oem, activity)
    """
    condition_tuple = (date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, lat_oem,
                       lng_oem, posAcc_oem)
                       
    tracker_return = []
    if all(elt is None for elt in condition_tuple): # on fait pas insertion si toutes les donnees sont null
        pass
    else: # si extraction reussi
        tracker_return.append(return_tuple)        

    #################################################################################################################################
    #                                               TAG DATA EXTRACTION                                                             #
    #################################################################################################################################
    # Intialisation tag array
    tag_return = []

    output_data_tag = find_value_by_listkey(
        json_data, CONFIG_MAPPING["DATA_TAG"], path=None,  parent_index=None)

    output_type_tag = find_value_by_listkey(
        json_data, CONFIG_MAPPING["TYPE_TAG"], path=None,  parent_index=None)


    output_rssi = find_value_by_listkey(
        json_data, CONFIG_MAPPING["RSSI"], path=None,  parent_index=None)


    lat_, lng_, posAcc_, ALT_, CAP_, PDOP_, VOLT_BAT_, TEMPERATURE_, DOUT_ = get_last_tracker_info(sn_oem)

    idx = 0
    mac_list_dedup = []
    for tag in output_data_tag:
        parent_index, index, path, data_hex = tag
        tt = 13 # defaut type tag
        RSSI = None
        
        try:
            tt = output_type_tag[idx][3]
        except:
            pass

        try:
            RSSI = output_rssi[idx][3]
        except:
            pass
        
        idx = idx + 1


        array = decode_data(data=data_hex, type_tag=tt)
        
        # si le decodage est reussi
        if all(info is not None for info in array):
            mac_adress_oem = array[0]
            tag_name_oem = array[1]
            x_acc_oem = array[2]
            y_acc_oem = array[3]
            z_acc_oem = array[4]

            type_oem = "Tag"
            
            
            if lng_oem is not None and lat_oem is not None:
                lng_ = lng_oem
                lat_ = lat_oem
                posAcc_ = posAcc_oem
                ALT_ = ALT
                CAP_ = CAP
                PDOP_ = PDOP
                VOLT_BAT_ = VOLT_BAT
                TEMPERATURE_ = TEMPERATURE
                DOUT_ = DOUT

            lat_, lng_, DOUT_ = gen_tag_coords(lat_, lng_, RSSI)
            if mac_adress_oem not in mac_list_dedup: # on garde seulement le premier data de chaque TAG pour chaque alerte <=> idem comme telematics guru
                tag_activity = compute_activity_metric(mac_adress_oem, x_acc_oem, y_acc_oem, z_acc_oem)
                tag_return.append((type_oem, date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, lat_,
                                   lng_, posAcc_, mac_adress_oem, tag_name_oem, x_acc_oem, y_acc_oem, z_acc_oem, tag_activity, endpoint, ALT_, CAP_, PDOP_, VOLT_BAT_, TEMPERATURE_, DOUT_, PEAK, AVERAGE, DURATION, RSSI))
                mac_list_dedup.append(mac_adress_oem)

    """
    if len(tag_return) > 0: # si tag
        return tag_return
    else:   # si tracker
        return tracker_return
    """
    return tracker_return + tag_return
############################## GEO PROCESS ENGINE ####################################

def transform_poly(dict_coordinates):

    # Trier les coordonnées en fonction de la clé "order"
    sorted_coordinates = sorted(dict_coordinates, key=lambda x: x["order"])
    
    # Formater les données sans "order"
    formatted_data = [
        {"longitude": point["longitude"], "latitude": point["latitude"]}
        for point in sorted_coordinates
    ]

    
    # retouner le résultat
    return formatted_data


def geofencing(coordinates,latitude,longitude,crossingDistance):
    try:
        status = "success"
        poly_json=transform_poly(coordinates)
        coords = [(sommet["latitude"], sommet["longitude"]) for sommet in poly_json]
        premier=(poly_json[0]["latitude"], poly_json[0]["longitude"])
        coords.append(premier)

        # creer un polygone
        poly = Polygon(coords)

        # Chercher le centroid du polygone
        centroid=poly.centroid

        # creer le point
        objet=Point(latitude,longitude ).buffer(crossingDistance/100000)
        point=Point(latitude,longitude )

        # tester si le point est contenu dans le polygone
        if poly.intersection(objet).area==0:
            intersection_marge = False
        else:
            intersection_marge = True
            
        intersection_position=poly.contains(point)
       
        return intersection_position,intersection_marge, status
    except Exception as e:
        print(f"[ERROR][utils.utils.geofencing] {e}")
        return False, False, "error"
   


# cette fonction extracte et valide les donnes avant de faire une calcul de geofencing
def validation_json_zone(json_zone):
    crossingDistance = None
    coordinates = None
    _id = ""
    name = ""
    userId = ""
    validation = "success"
    
    try:
        if isinstance(json_zone, dict):
            json_zone = [json_zone]
        
        output_list = []
        
        for zone_dict in json_zone:
            
            crossingDistance = None
            coordinates = None
            _id = ""
            name = ""
            userId = ""
            validation = "success"

            output_coodinates = find_value_by_listkey(
            zone_dict, ["coordinates"], path=None,  parent_index=None)

            if len(output_coodinates) > 0:
                coordinates = output_coodinates[0][3]
            
            output_crossingDistance = find_value_by_listkey(
            zone_dict, ["crossingDistance"], path=None,  parent_index=None)             

            if len(output_crossingDistance) > 0:
                crossingDistance = output_crossingDistance[0][3]

            output_id = find_value_by_listkey(
            zone_dict, ["id"], path=None,  parent_index=None)             

            if len(output_id) > 0:
                _id = output_id[0][3]

            
            output_name = find_value_by_listkey(
            zone_dict, ["name"], path=None,  parent_index=None)             

            if len(output_name) > 0:
                name = output_name[0][3]

            output_userId = find_value_by_listkey(
            zone_dict, ["userId"], path=None,  parent_index=None)             

            if len(output_userId) > 0:
                userId = output_userId[0][3]
                        

            if crossingDistance is None or crossingDistance == "":
                validation = "error"

            try:
                int_value = int(crossingDistance)
                float_value = float(crossingDistance)
            except ValueError:
                validation = "error"
            except Exception as e:
                validation = "error"

            if not isinstance(coordinates, list):
                validation = "error"
            else:
                if len(coordinates) == 0:
                    validation = "error"

            dict_extract = {"validation" : validation,
                "coordinates" : coordinates,
                "crossingDistance" : crossingDistance,
                "id" : _id,
                "name" : name,
                "userId" : userId
                }

            output_list.append(dict_extract)
        return output_list
    except Exception as e:
        print(f"[ERROR][utils.utils.validation_json_zone] {e}")
        return [{"validation" : "error",
                "coordinates" : None,
                "crossingDistance" : None,
                "id" : "",
                "name" : "",
                "userId" : ""
                }]



def get_majdata_and_geofencing(json_geofencing):

    data_zone = validation_json_zone(json_geofencing) # extrait et valide les zones
    
    data_device = get_lastmaj_data_for_all_device() # donnes recents des devices tag et Tracker
    
    for device in data_device:
        data_zone_add = []
        for zone in data_zone:
            dict_zone = {}
            dict_zone["id"] = zone["id"]
            dict_zone["name"] = zone["name"]
            dict_zone["userId"] = zone["userId"]
            dict_zone["crossingDistance"] = zone["crossingDistance"]
            if zone["validation"] == "success":
                intersection_position, intersection_marge, status = geofencing(zone["coordinates"],device["lat"],device["lng"],float(zone["crossingDistance"]))
                dict_zone["intersection_position"] = intersection_position
                dict_zone["intersection_marge"] = intersection_marge
                if status == "success":
                    dict_zone["status"] = "success"
                    data_zone_add.append(dict_zone)
                else:
                    dict_zone["status"] = "error"
                    data_zone_add.append(dict_zone)

        device["geofencing"] = data_zone_add

    return data_device


def get_majdata_and_geofencing_force_alert(data):
    list_tracker = []
    list_tag = []
    json_geofencing = None

    if isinstance(data, dict):
        if 'area' in data.keys():
            json_geofencing = data['area']
        if 'devices' in data.keys():
            if isinstance(data['devices'], list):
                for dev in data['devices']:
                    if isinstance(dev, dict):
                        if "type"  in dev.keys() and "serialNumber" in dev.keys():
                            if str(dev["type"]).upper() == "TAG":
                                list_tag.append(str(dev["serialNumber"]).upper())
                            if str(dev["type"]).upper() == "TRACKER":
                                list_tracker.append(dev["serialNumber"]) 
    
    if len(list_tracker) == 0:
        list_tracker.append('XXXXXXXXX')
    if len(list_tag) == 0:
        list_tag.append('XXXXXXXXX')
    
    data_zone = validation_json_zone(json_geofencing) # extrait et valide les zones
    
    data_device = get_lastmaj_data_for_specific_device(list_tracker, list_tag) # donnes recents des devices tag et Tracker
    
    for device in data_device:
        data_zone_add = []
        for zone in data_zone:
            dict_zone = {}
            dict_zone["id"] = zone["id"]
            dict_zone["name"] = zone["name"]
            dict_zone["userId"] = zone["userId"]
            dict_zone["crossingDistance"] = zone["crossingDistance"]
            if zone["validation"] == "success":
                intersection_position, intersection_marge, status = geofencing(zone["coordinates"],device["lat"],device["lng"],float(zone["crossingDistance"]))
                dict_zone["intersection_position"] = intersection_position
                dict_zone["intersection_marge"] = intersection_marge
                if status == "success":
                    dict_zone["status"] = "success"
                    data_zone_add.append(dict_zone)
                else:
                    dict_zone["status"] = "error"
                    data_zone_add.append(dict_zone)

        device["geofencing"] = data_zone_add

    return data_device



######################################## ALPES ECO V2 ########################################

def get_majdata_telemetry():    
    return get_lastmaj_telemetry() # donnees recent des devices tag et Tracker

def get_majdata_analysis():    
    return get_lastmaj_analysis() # donnes recents des devices tag et Tracker

######################################## END ALPES ECO V2 ####################################



# cette fonction va servir a creer une donnee zone fitcif en guise de test
def test_json_zone(option='dict'):
    
    json_input={
      "coordinates": [
        {
          "order": 1,
          "latitude": 37.78379442578297,
          "longitude": -122.4558076635003
        },
        {
          "order": 2,
          "latitude": 37.7832321398541,
          "longitude": -122.4342370033264
        },
        {
          "order": 3,
          "latitude": 37.76466900358004,
          "longitude": -122.4364887177944
        },
        {
          "order": 4,
          "latitude": 37.76963846369145,
          "longitude": -122.4561630561948
        },
        {
          "order": 5,
          "latitude": 37.77857443543847,
          "longitude": -122.4719854071736
        },
        {
          "order": 6,
          "latitude": 37.79266456941215,
          "longitude": -122.473585344851
        }
      ],
      "activationTimes": [
        {
          "start": "2023-08-23T18:24:42.286Z",
          "end": "2023-08-23T18:24:42.286Z"
        }
      ],
      "id": "64e6533944a5031fbf29c740",
      "name": "Zone-vache",
      "crossingDistance": 20,
      "isShared": True,
      "userId": "64e4f1bf75586ad93ad05ecd",
      "createdAt": "2023-08-23T18:43:05.365Z",
      "updatedAt": "2023-08-23T18:43:05.365Z"
    }
    if option == 'dict':
        return json_input
    else: return [json_input]



################################### WEBHOOK ENGINE #######################

def make_url_api(data_api):
    try:
        url = data_api["url"]
        headers = {"Content-Type": "application/json"}
        if data_api["hk1"] is not None and data_api["hv1"] is not None and data_api["hk1"] != "" and data_api["hv1"] != "":
             headers[data_api["hk1"]] = data_api["hv1"]

        if data_api["hk2"] is not None and data_api["hv2"] is not None and data_api["hk2"] != "" and data_api["hv2"] != "":
             headers[data_api["hk2"]] = data_api["hv2"]

        if data_api["hk3"] is not None and data_api["hv3"] is not None and data_api["hk3"] != "" and data_api["hv3"] != "":
             headers[data_api["hk3"]] = data_api["hv3"]

        if data_api["hk4"] is not None and data_api["hv4"] is not None and data_api["hk4"] != "" and data_api["hv4"] != "":
             headers[data_api["hk4"]] = data_api["hv4"]

        auth = (data_api["login"], data_api["password"])

        no_auth = False
        no_header = False
        if headers == {}:
            no_header = False
        if data_api["login"] is None or data_api["login"] == "":
            no_auth = True
        elif data_api["password"] is None or data_api["password"] == "":
            no_auth = True
        else:
            auth = (data_api["login"].encode('utf-8'), data_api["password"].encode('utf-8'))

        return url, headers, auth, no_auth, no_header
    except Exception as e:
        print(f"[ERROR][utils.utils.make_url_api] {e}")
        return "", {}, None, True, True


def split_list_of_dicts(list_of_dicts, group_size=10):
    """
    Split a list of dictionaries into groups of a specified size (default is 10).

    :param list_of_dicts: List of dictionaries to be split.
    :param group_size: Maximum number of elements in each group.
    :return: List of lists, each containing up to `group_size` dictionaries.
    """
    try:
        divided_list = [list_of_dicts[i:i + group_size] for i in range(0, len(list_of_dicts), group_size)]
        return divided_list
    except Exception as e:
        print(f"[ERROR][utils.utils.split_list_of_dicts] {e}")
        return list_of_dicts


def isAuthorize(current_minute, cadence_minutes, reversed_ = True):
    try:
        if reversed_ == True:   # pause de 1 minutes toutes les {cadence_minutes}
            if cadence_minutes == 0:
                return True
            elif current_minute % cadence_minutes == 0:
                return False
            else:
                return True
        else:                   # ne pas authorise que toutes les {cadence_minutes}
            if cadence_minutes == 0:
                return True
            elif current_minute % cadence_minutes == 0:
                return True
            else:
                return False
    except:
        return False


# default timeout : 15s
def run_single_webhook(list_api_wh = [], list_api_gf = [], current_minute=1, cadence_minutes=3,  _timeout_=15):
    
    json_geofencing = {}

    if len(list_api_wh) > 0 and isAuthorize(current_minute, cadence_minutes) == True: # maj toutes les 3minutes # 2 minutes wait to avoid overloading the server with threads.
        if len(list_api_gf) > 0:
            for data_api_fg in list_api_gf: 
                url, headers, auth, no_auth, no_header = make_url_api(data_api_fg)
                
                try:
                    response = None
                    if no_auth == True and no_header == True:
                        response = requests.get(url, timeout=_timeout_)
                    elif no_auth == False and no_header == True:
                        response = requests.get(url ,auth=auth, timeout=_timeout_)
                    elif no_auth == True and no_header == False:
                        response = requests.get(url ,headers=headers, timeout=_timeout_)
                    else:
                        response = requests.get(url ,auth=auth ,headers=headers, timeout=_timeout_)
                    if response.status_code == 200:
                        json_geofencing = response.json()
                        save_log([(data_api_fg["id"], url, 'get', response.status_code, '', response.text)])
                        break
                    else:
                        save_log([(data_api_fg["id"], url, 'get', response.status_code, '', '')])
                except Exception as e:
                    print(e)
                    try:
                        response = None
                        
                        if no_auth == True and no_header == True:
                            response = requests.post(url, timeout=_timeout_)
                        elif no_auth == False and no_header == True:
                            response = requests.post(url ,auth=auth, timeout=_timeout_)
                        elif no_auth == True and no_header == False:
                            response = requests.post(url ,headers=headers, timeout=_timeout_)
                        else:
                            response = requests.post(url ,auth=auth ,headers=headers, timeout=_timeout_)

                        if response.status_code == 200:
                            json_geofencing = response.json()
                            save_log([(data_api_fg["id"], url, 'post', response.status_code, '', response.text)])
                            break
                        else:
                            save_log([(data_api_fg["id"], url, 'post', response.status_code, '', '')])
                    except Exception as e:
                        save_log([(data_api_fg["id"], url, 'post', 'error', str(e), '')])

        all_data = get_majdata_and_geofencing(json_geofencing)
        #print("len all data : ",len(all_data))

        if len(all_data) > 0:
            for data in split_list_of_dicts(all_data, group_size=2):
                _timeout_ = 5 # on libere api-calcul apres 5 seconde pour ne pas engorge le systeme
                try:
                    data = json.dumps(data)
                    
                    for data_api_wh in list_api_wh: 
                        url, headers, auth, no_auth, no_header = make_url_api(data_api_wh)
                        try:
                            response = None
                            if no_auth == True and no_header == True:
                                response = requests.post(url, data=data, timeout=_timeout_)
                            elif no_auth == False and no_header == True:
                                response = requests.post(url ,data=data, auth=auth, timeout=_timeout_)
                            elif no_auth == True and no_header == False:
                                response = requests.post(url, data=data ,headers=headers, timeout=_timeout_)
                            else:
                                response = requests.post(url, data=data ,auth=auth ,headers=headers, timeout=_timeout_)
                            if response.status_code == 200:
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                                #print(response.status_code)
                            else:
                                #print(response.status_code)
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                        except Exception as e:
                            save_log([(data_api_wh["id"], url, 'post', 'error', str(e), '')])
                    
                except Exception as e:
                    print(e)
                    pass
                #time.sleep(1)
            #time.sleep(5) # sleep 5 seconde before run next webhook 




# default timeout : 15s
def run_telemetry_webhook(list_api_wh = [], current_minute=1, cadence_minutes=3,  _timeout_=15):
    
    if len(list_api_wh) > 0 and isAuthorize(current_minute, cadence_minutes) == True: # maj toutes les 10minutes # 9 minutes wait to avoid overloading the server with threads.

        all_data = get_majdata_telemetry()
        #print("len all data : ",len(all_data))
        if len(all_data) > 0:
            for data in split_list_of_dicts(all_data, group_size=2):
                #print("len data : ",len(data))
                try:
                    data = json.dumps(data)
                    
                    for data_api_wh in list_api_wh: 
                        url, headers, auth, no_auth, no_header = make_url_api(data_api_wh)
                        try:
                            response = None
                            if no_auth == True and no_header == True:
                                response = requests.post(url, data=data, timeout=_timeout_)
                            elif no_auth == False and no_header == True:
                                response = requests.post(url ,data=data, auth=auth, timeout=_timeout_)
                            elif no_auth == True and no_header == False:
                                response = requests.post(url, data=data ,headers=headers, timeout=_timeout_)
                            else:
                                response = requests.post(url, data=data ,auth=auth ,headers=headers, timeout=_timeout_)
                            if response.status_code == 200:
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                                #print(response.status_code)
                            else:
                                #print(response.status_code)
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                        except Exception as e:
                            save_log([(data_api_wh["id"], url, 'post', 'error', str(e), '')])
                    
                except Exception as e:
                    print(e)
                    pass
                #time.sleep(1)
            #time.sleep(5) # sleep 5 seconde before run next webhook


# default timeout : 15s
def run_analysis_webhook(list_api_wh = [], current_minute=1, cadence_minutes=9, _timeout_=15):
    
    if len(list_api_wh) > 0 and isAuthorize(current_minute, cadence_minutes, False) == True: # NE FAIRE LA MLAJ QUE toutes les 9minutes

        all_data = get_majdata_analysis()
        if len(all_data) > 0:
            for data in all_data:
                try:
                    data = json.dumps(data)
                    
                    for data_api_wh in list_api_wh: 
                        url, headers, auth, no_auth, no_header = make_url_api(data_api_wh)
                        try:
                            response = None
                            if no_auth == True and no_header == True:
                                response = requests.post(url, data=data, timeout=_timeout_)
                            elif no_auth == False and no_header == True:
                                response = requests.post(url ,data=data, auth=auth, timeout=_timeout_)
                            elif no_auth == True and no_header == False:
                                response = requests.post(url, data=data ,headers=headers, timeout=_timeout_)
                            else:
                                response = requests.post(url, data=data ,auth=auth ,headers=headers, timeout=_timeout_)
                            if response.status_code == 200:
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                                #print(response.status_code)
                            else:
                                #print(response.status_code)
                                save_log([(data_api_wh["id"], url, 'post', response.status_code, '', data)])
                        except Exception as e:
                            save_log([(data_api_wh["id"], url, 'post', 'error', str(e), '')])
                    
                except Exception as e:
                    print(e)
                    pass
                #time.sleep(1)


# default timeout : 6min
def run_webhook(_timeout_=15):
    current_minute = time.localtime().tm_min
    #if current_minute % 2 == 0: # 2minutes # 1 minute wait to avoid overloading the server with threads.
    #    return None 
    env_list = ["PROD", "PREPROD", "STAGING", "TEST1", "TEST2"]
    for _env_ in env_list:
        print("BEG ===>", _env_)
        list_api_wh = get_api_active(_type_ = 'webhook', status_api=1, env=_env_)
        list_api_gf = get_api_active(_type_ = 'geofencing', status_api=1, env=_env_)
        list_api_analysis = get_api_active(_type_ = 'analysis', status_api=1, env=_env_)
        list_api_telemetry = get_api_active(_type_ = 'telemetry', status_api=1, env=_env_)
        run_single_webhook(list_api_wh = list_api_wh, list_api_gf = list_api_gf,current_minute=current_minute, cadence_minutes=3,  _timeout_=_timeout_)#3
        run_telemetry_webhook(list_api_wh = list_api_telemetry,current_minute=current_minute, cadence_minutes=3,  _timeout_=5)#3
        run_analysis_webhook(list_api_wh = list_api_analysis,current_minute=current_minute, cadence_minutes=3,  _timeout_=5)#9
        print("END ===>", _env_)
    
 
