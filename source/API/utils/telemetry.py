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
from models.models import get_lastmaj_data_for_specific_device, get_lastmaj_telemetry, get_last_tracker_telemetry

CONFIG_LOG_REASON = {}
CONFIG_TAG_REASON = {}
CONFIG_TELEMETRY_TAG_MAPPING = {}
CONFIG_TELEMETRY_TRACKER_MAPPING = {}
############################## CONFIG READER ####################################

def load_json_file(file):
    # open json file
    with open(file, 'r') as json_file:
        data = json.load(json_file)
    return data


def load_telemetry_config(json_path):
    global CONFIG_LOG_REASON
    global CONFIG_TAG_REASON
    global CONFIG_TELEMETRY_TAG_MAPPING
    global CONFIG_TELEMETRY_TRACKER_MAPPING
    
    # load config from json file
    CONFIG_LOG_REASON = load_json_file(json_path)["LOG_REASON"]
    CONFIG_TAG_REASON = load_json_file(json_path)["TAG_REASON"]
    CONFIG_TELEMETRY_TAG_MAPPING = load_json_file(json_path)["TELEMETRY_TAG_MAPPING"]
    CONFIG_TELEMETRY_TRACKER_MAPPING = load_json_file(json_path)["TELEMETRY_TRACKER_MAPPING"]
    
    return CONFIG_LOG_REASON, CONFIG_TELEMETRY_TAG_MAPPING, CONFIG_TELEMETRY_TRACKER_MAPPING


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



def get_telemetry_tag_data(json_data, CONFIG_MAPPING):

 
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

    output_status = find_value_by_listkey(
        json_data, CONFIG_MAPPING["STATUS"], path=None,  parent_index=None)

     
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
        
        status = "Update"
        try:
            status = CONFIG_TAG_REASON[str(output_status[idx][3])]
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

            if mac_adress_oem not in mac_list_dedup: # on garde seulement le premier data de chaque TAG pour chaque alerte <=> idem comme telematics guru
                tag_activity = compute_activity_metric(mac_adress_oem, x_acc_oem, y_acc_oem, z_acc_oem)
                if all(elt is None for elt in (mac_adress_oem, tag_name_oem, x_acc_oem, y_acc_oem, z_acc_oem, tag_activity, RSSI, status)): # on fait pas insertion si toutes les donnees sont null
                    pass
                else: # si extraction reussi
                    tag_return.append((mac_adress_oem, tag_name_oem, x_acc_oem, y_acc_oem, z_acc_oem, tag_activity, RSSI,  status))
                    mac_list_dedup.append(mac_adress_oem)

    return tag_return



def calculate_seconds_difference(date_string):
    try:
        # Appel de la fonction pour obtenir une date convertie en string
        converted_date_string = parse_and_convert_date(date_string)
        
        if converted_date_string:
            # Convertir la chaîne de date en objet datetime
            parsed_date = datetime.datetime.strptime(converted_date_string, "%Y-%m-%dT%H:%M:%SZ")
            
            # Obtenir la date et l'heure actuelles en UTC
            current_datetime = datetime.datetime.utcnow()
            
            # Calcul de la différence en secondes
            difference = current_datetime - parsed_date
            difference_in_seconds = difference.total_seconds()
            
            if int(difference_in_seconds) > 0 and int(difference_in_seconds) < 120:
                return int(difference_in_seconds)
            else:
                return random.randint(1, 120)
        else:
            return random.randint(1, 120)
    except Exception as e:
        print(f"[ERROR][utils.utils.calculate_seconds_difference] {e}")
        return random.randint(1, 120)


def get_telemetry_data(json_data, endpoint="send_data_oem"):


    #################################################################################################################################
    #                                               TRACKER DATA EXTRACTION                                                         #
    #################################################################################################################################
    reason = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["REASON"])
    reason = CONFIG_LOG_REASON[str(reason)] if str(reason) in CONFIG_LOG_REASON.keys() else None

    transmission_delay = random.randint(1, 40)
    

    speed = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["SPEED"])
    used_speed = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["USEDSPEED"])
    speed_band = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["SPEEDBAND"])
    local_speed_limit = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["LOCALSPEEDLIMIT"])
    speed_accuracy = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["SPEEDACCURACY"])
    driver_id = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["SPEEDACCURACY"])
    driver_id = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["DRIVER"])
    trip_type_code = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["TRIPTYPECODE"])
    project_code = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["PROJECTCODE"])
    gps_age = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["GPSAGE"])
    gps_fix_ok = True
    gps_fix_3d = True
    analog2 = analog_search(json_data, ["analogues", "AnalogueData"], 2)
    analog4 = analog_search(json_data, ["analogues", "AnalogueData"], 4)
    analog5 = analog_search(json_data, ["analogues", "AnalogueData"], 5)
    analog6 = analog_search(json_data, ["analogues", "AnalogueData"], 6)
    analog7 = analog_search(json_data, ["analogues", "AnalogueData"], 7)
    analog8 = analog_search(json_data, ["analogues", "AnalogueData"], 8)
    analog9 = analog_search(json_data, ["analogues", "AnalogueData"], 9)
    analog10 = analog_search(json_data, ["analogues", "AnalogueData"], 10)
    analog11 = analog_search(json_data, ["analogues", "AnalogueData"], 11)
    analog15 = analog_search(json_data, ["analogues", "AnalogueData"], 15)
    analog16 = analog_search(json_data, ["analogues", "AnalogueData"], 16)
    analog17 = analog_search(json_data, ["analogues", "AnalogueData"], 17)


    # Initialisation
    type_oem = None
    date_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["DATE"])
    date_oem_parse = parse_and_convert_date(date_oem) 
    sn_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["SERIAL_NUMBER"])
    prod_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["PROD"])
    
    transmission_delay = calculate_seconds_difference(date_oem_parse)
    try:
        prod_oem =  str(REF_PRODUCT[str(prod_oem)])+"|"+str(prod_oem) # save type device name and type device ID => Ex : Oyster3 4G BLE|102
    except:
        try:
            prod_oem = str(prod_oem)+"|"
        except:
            pass

    iccid_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["ICCID"])
    imei_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["IMEI"])
    lat_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["LAT"])
    lng_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["LNG"])
    posAcc_oem = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["POSACC"])
    
    if lat_oem is not None:
        type_oem = "Tracker"
    else:
        type_oem = "unknow"

    
    ALT = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["ALT"])
    CAP = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["CAP"])
    if CAP is not None:
        try:
            if endpoint != 'send_data_tg':
                CAP = int(CAP) * 2
        except Exception as e:
            pass

    PDOP = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["PDOP"])
    if PDOP is not None:
        try:
            if endpoint != 'send_data_tg':
                PDOP = int(PDOP) / 10
        except Exception as e:
            pass


    VOLT_BAT = get_voltage_batt(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["VOLT_BAT"])
    analog1 = VOLT_BAT

    TEMPERATURE = get_temperature(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["TEMPERATURE"])
    analog3 = TEMPERATURE
    DOUT = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["DOUT"])
    DIN = get_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["DIN"])
    
    PEAK, AVERAGE, DURATION = get_highG_data(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING)
    analog18, analog19,analog20 = PEAK, AVERAGE, DURATION 
    XACC_TRACKER = get_ACC_tracker(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["X"], 12)
    YACC_TRACKER = get_ACC_tracker(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["Y"], 13)
    ZACC_TRACKER = get_ACC_tracker(json_data, CONFIG_TELEMETRY_TRACKER_MAPPING["Z"], 14)
    analog12 = XACC_TRACKER
    analog13 = YACC_TRACKER
    analog14 = ZACC_TRACKER

    return_tuple = (type_oem, date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, lat_oem, lng_oem,posAcc_oem,None,None,None,None,None,None,None,None,
                        ALT,CAP,PDOP,VOLT_BAT,TEMPERATURE,DOUT,PEAK,AVERAGE,DURATION,None,
                        reason,transmission_delay,gps_age,speed,used_speed, speed_band,local_speed_limit,speed_accuracy,
                        gps_fix_ok, gps_fix_3d,DIN, driver_id, trip_type_code, project_code, 
                        analog1, analog2,analog3, analog4, analog5, analog6,analog7, analog8,analog9,analog10,
                        analog11,analog12, analog13, analog14, analog15, analog16, analog17,analog18,analog19,analog20, None)

    condition_tuple = (date_oem, date_oem_parse, sn_oem, prod_oem, lat_oem,lng_oem, posAcc_oem)
                       
    tracker_return = []
    if all(elt is None for elt in condition_tuple): # on fait pas insertion si toutes les donnees sont null
        pass
    else: # si extraction reussi
        tracker_return.append(return_tuple)        


    ############################# TAG ##########################################################
    tag_return = []  
    data_tag = get_telemetry_tag_data(json_data, CONFIG_TELEMETRY_TAG_MAPPING)
    if len(data_tag) > 0:
        latitude = lat_oem
        longitude = lng_oem
        gw_pos_acc = posAcc_oem
        gw_speed = speed
        if len(tracker_return) == 0: 
            latitude, longitude, gw_pos_acc, gw_speed = get_last_tracker_telemetry(sn_oem)

        for tag_info in data_tag:
            mac_adress_oem = tag_info[0] 
            tag_name_oem = tag_info[1] 
            x_acc_oem = tag_info[2] 
            y_acc_oem = tag_info[3] 
            z_acc_oem = tag_info[4] 
            tag_activity = tag_info[5] 
            RSSI = tag_info[6]  
            status = tag_info[7]

            condition_tuple = (date_oem, date_oem_parse, sn_oem, latitude,longitude, mac_adress_oem)
            return_tuple = ("Tag", date_oem, date_oem_parse, sn_oem, prod_oem, iccid_oem, imei_oem, latitude, longitude,gw_pos_acc,mac_adress_oem,tag_name_oem,x_acc_oem,y_acc_oem,z_acc_oem,0,tag_activity,None,
                        ALT,CAP,PDOP,VOLT_BAT,TEMPERATURE,DOUT,PEAK,AVERAGE,DURATION,RSSI,
                        reason,transmission_delay,gps_age,speed,used_speed, speed_band,local_speed_limit,speed_accuracy,
                        gps_fix_ok, gps_fix_3d,DIN, driver_id, trip_type_code, project_code, 
                        analog1, analog2,analog3, analog4, analog5, analog6,analog7, analog8,analog9,analog10,
                        analog11,analog12, analog13, analog14, analog15, analog16, analog17,analog18,analog19,analog20, status)

            if all(elt is None for elt in condition_tuple): # on fait pas insertion si toutes les donnees sont null
                pass
            else: # si extraction reussi
                tag_return.append(return_tuple)

    return tracker_return + tag_return


############################## GEO PROCESS ENGINE ####################################


