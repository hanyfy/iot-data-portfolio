import json
import psycopg2
import math
import requests
from math import radians
from decimal import Decimal
from time import gmtime, strftime
from datetime import datetime
from shapely.geometry import Point, Polygon


fuseau_horaire_serveur = strftime("%z", gmtime())   

BDD_CONNEX = None
CONFIG_POSTGRES = None
STRUCT_TABLE_NAME = ""
RAW_TABLE_NAME = ""
API_TABLE_NAME = ""
WEBHOOK_LOG_TABLE_NAME = ""
TELEMETRY_TABLE_NAME = ""
REF_PRODUCT = {}
################################### CONNEX  MANAGEMENT #########################################


def connection_pg(CONFIG_POSTGRES_):
    CONNEX = psycopg2.connect(
            host=CONFIG_POSTGRES_['HOST'],
            port=CONFIG_POSTGRES_['PORT'],
            database=CONFIG_POSTGRES_['DB'],
            user=CONFIG_POSTGRES_['USER'],
            password=CONFIG_POSTGRES_['PASSWORD'])
    print("connex etablished : ", CONNEX)
    return CONNEX



def bdd_connection(CONFIG_POSTGRES_):
    global BDD_CONNEX
    global STRUCT_TABLE_NAME
    global RAW_TABLE_NAME
    global API_TABLE_NAME
    global WEBHOOK_LOG_TABLE_NAME
    global CONFIG_POSTGRES
    global TELEMETRY_TABLE_NAME

    STRUCT_TABLE_NAME = CONFIG_POSTGRES_['STRUCT_TABLE_NAME']
    RAW_TABLE_NAME = CONFIG_POSTGRES_['RAW_TABLE_NAME']
    API_TABLE_NAME = CONFIG_POSTGRES_['API_TABLE_NAME']
    WEBHOOK_LOG_TABLE_NAME = CONFIG_POSTGRES_['WEBHOOK_LOG_TABLE_NAME']
    TELEMETRY_TABLE_NAME = CONFIG_POSTGRES_['TELEMETRY_TABLE_NAME']
    CONFIG_POSTGRES = CONFIG_POSTGRES_
        
    if BDD_CONNEX is not None:
        if not BDD_CONNEX.closed:
            return BDD_CONNEX.cursor()
        else:
            BDD_CONNEX = connection_pg(CONFIG_POSTGRES_)
            return BDD_CONNEX.cursor()
    else:
        # premiere connexion, pas de return cursor ici, sinon cette curseur ne sera pas fermé
        BDD_CONNEX = connection_pg(CONFIG_POSTGRES_)
        print("[INFO][First connexion bdd]")
            

def load_ref_product(CONFIG_PRODUCT):
    global REF_PRODUCT
    REF_PRODUCT = CONFIG_PRODUCT

################################### SEARCH ENGINE #########################################


def get_last_tracker_info(serial_number, day_limit=1):
    lat = None
    lng = None
    posAcc = None
    alt = None
    cap = None
    pdop = None
    volt_bat = None
    temperature = None
    dout = None
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute("select lat, lng, pos_acc, alt, cap, pdop, volt_bat, temperature, dout from "+STRUCT_TABLE_NAME+" where sn = '" +
                        str(serial_number)+"'  and type = 'Tracker' and dout is not null and lat is not null and lng is not null  and receip_datetime >= CURRENT_DATE - INTERVAL '"+str(day_limit)+" days' order by receip_datetime DESC limit 1")
        output = BDD_CUR.fetchall()

        for val in output:
            lat = val[0]
            lng = val[1]
            posAcc = val[2]
            alt = val[3]
            cap = val[4]
            pdop = val[5]
            volt_bat = val[6]
            temperature = val[7]
            dout = val[8]
        BDD_CUR.close()
        return [lat, lng, posAcc, alt, cap, pdop, volt_bat, temperature, dout]
    except Exception as e:
        print(f"[ERROR][models.models.get_last_tracker_info] {e}")
        return [lat, lng, posAcc, alt, cap, pdop, volt_bat, temperature, dout]


def get_2last_tag_acc(mac_address, day_limit=30):
    X0 = None
    X1 = None
    Y0 = None
    Y1 = None
    Z0 = None
    Z1 = None
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute("select x_acc, y_acc, z_acc from "+STRUCT_TABLE_NAME+" where mac_address = '" +
                        str(mac_address)+"'  and type = 'Tag'  and receip_datetime >= CURRENT_DATE - INTERVAL '"+str(day_limit)+" days' order by id DESC limit 2")
        output = BDD_CUR.fetchall()
        length_tag = len(output)
        
        if length_tag == 2:
            (X0, Y0, Z0), (X1, Y1, Z1) = output
            return (float(X0), float(Y0), float(Z0)), (float(X1), float(Y1), float(Z1))
        BDD_CUR.close()
        return (X0, Y0, Z0), (X1, Y1, Z1)

    except Exception as e:
        print(f"[ERROR][models.models.get_2last_tag_acc] {e}")
        return (X0, Y0, Z0), (X1, Y1, Z1)


def compute_info_tag(output_query):
    dict_computing_nb_tag = {}
    dict_coords_tracker = {}
    for row in output_query:
        if row[1] == 'Tag':
            if row[3] not in dict_computing_nb_tag:
                dict_computing_nb_tag[row[3]] = 1 
            else:
                dict_computing_nb_tag[row[3]] = dict_computing_nb_tag[row[3]] + 1
        else: 
            dict_coords_tracker[row[3]] = {"lat" : float(row[6].quantize(Decimal('0.0000001'))), "lng" : float(row[7].quantize(Decimal('0.0000001')))}
    return dict_computing_nb_tag, dict_coords_tracker


def calculer_delta_position(coord1, coord2):
    try:
        # Créer des objets Point à partir des coordonnées
        point1 = Point(coord1[1], coord1[0])  # Latitude, Longitude
        point2 = Point(coord2[1], coord2[0])

        # Approximation de la distance euclidienne (distance de Manhattan)
        distance = point1.distance(point2)
        if distance > 0:
            return 1
        else:
            return 0

    except:
        try:
            if coord1 == coord2:
                return 0
            else:
                return 1
        except:
            return 0


def process_delta_time(type_= 'Tracker', serial=None,id_=None):
    try:
        if type_ == "Tracker":
            query = """
            WITH cte AS (
              SELECT
                *,
                LEAD(COALESCE(peak, 0)) OVER (ORDER BY id DESC) AS prev_activite,
                COALESCE(peak, 0) - LEAD(COALESCE(peak, 0)) OVER (ORDER BY id DESC) AS delta_activite,
                COALESCE(lat, 0) - LEAD(COALESCE(lat, 0)) OVER (ORDER BY id DESC) AS delta_lat,
                COALESCE(lng, 0) - LEAD(COALESCE(lng, 0)) OVER (ORDER BY id DESC) AS delta_lng
              FROM {table_name} WHERE sn = '{sn}' AND type = 'Tracker' AND id < {id_}
            )
            SELECT id, receip_datetime
            FROM cte
            WHERE ((ABS(delta_activite)+ABS(delta_lat)+ABS(delta_lng))>0 OR prev_activite>0) 
            ORDER BY id DESC
            LIMIT 1
            """.format(sn=serial, table_name=STRUCT_TABLE_NAME, id_=id_)

        else:
            query = """
                WITH cte AS (
                  SELECT
                    *,
                    LEAD(COALESCE(activite, 0)) OVER (ORDER BY id DESC) AS prev_activite,
                    COALESCE(activite, 0) - LEAD(COALESCE(activite, 0)) OVER (ORDER BY id DESC) AS delta_activite,
                    COALESCE(lat, 0) - LEAD(COALESCE(lat, 0)) OVER (ORDER BY id DESC) AS delta_lat,
                    COALESCE(lng, 0) - LEAD(COALESCE(lng, 0)) OVER (ORDER BY id DESC) AS delta_lng
                  FROM {table_name} WHERE mac_address = '{sn}' AND type = 'Tag' AND id < {id_}
                )
                SELECT id, receip_datetime
                FROM cte
                WHERE ((ABS(delta_activite)+ABS(delta_lat)+ABS(delta_lng))>0 OR prev_activite>0) 
                ORDER BY id DESC
                LIMIT 1
                """.format(sn=serial, table_name=STRUCT_TABLE_NAME, id_=id_)

        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        length_tag = len(output)
        
        time2 = None

        if length_tag == 1:
            (_, time2) = output[0]

        BDD_CUR.close()
        return time2

    except Exception as e:
        print(f"[ERROR][models.models.delta_time] {e}")
        return None


def delta_coords_delta_time(type_= 'Tracker', coord1=None, time1=None, serial=None, id_=0):
    try:
        if type_ == "Tracker":
            query = """
            SELECT id, receip_datetime, lat, lng, peak
            FROM (
                SELECT
                    id, receip_datetime, lat, lng, peak,
                    ROW_NUMBER() OVER (PARTITION BY sn ORDER BY receip_datetime DESC) AS order_in_partition
                FROM {table_name} where type = 'Tracker' and lat is not null and lng is not null and sn is not null and sn = '{sn}'
            ) AS ranked
            WHERE order_in_partition = 2
            ORDER BY id, receip_datetime
            """.format(sn=serial, table_name=STRUCT_TABLE_NAME)

        else:
            query = """
                SELECT id, receip_datetime, lat, lng, activite
                FROM (
                    SELECT
                        id, receip_datetime, lat, lng, activite,
                        ROW_NUMBER() OVER (PARTITION BY mac_address ORDER BY receip_datetime DESC) AS order_in_partition
                    FROM {table_name} where type = 'Tag' and activite is not null and lat is not null and lng is not null and mac_address is not null and  mac_address = '{sn}'
                ) AS ranked
                WHERE order_in_partition = 2
                ORDER BY id, receip_datetime
            """.format(sn=serial ,table_name=STRUCT_TABLE_NAME)

        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        length_tag = len(output)

        delta_coords = 0
        delta_time = 0
        prev_activite = 0
        if length_tag == 1:
            
            (_, time2, lat2, lng2, prev_activite) = output[0]
            coord2 = (float(lat2.quantize(Decimal('0.0000001'))),float(lng2.quantize(Decimal('0.0000001'))))
            
            time2 = process_delta_time(type_, serial,id_)
            
    
            if time1 is not None and time1 != "" and time2 is not None and time2 != "": 
                time2 = time2.strftime("%Y-%m-%d %H:%M:%S")
                time1 = datetime.strptime(time1, "%Y-%m-%d %H:%M:%S")
                time2 = datetime.strptime(time2, "%Y-%m-%d %H:%M:%S")
                delta_time = abs((time2 - time1).total_seconds())

            delta_coords = calculer_delta_position(coord1, coord2)
        
        BDD_CUR.close()
        return delta_coords, delta_time, prev_activite

    except Exception as e:
        print(f"[ERROR][models.models.delta] {e}")
        return 0, 0



def distance_tag_med(coord_tracker, lat2, lng2):
    try:
        lat1 = coord_tracker['lat']
        lng1 = coord_tracker['lng']
        # Rayon de la Terre en mètres
        earth_radius = 6371000.0
        
        # Conversion des coordonnées en radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Calcul des différences de latitude et de longitude
        delta_lat = lat2_rad - lat1_rad
        delta_lng = lng2_rad - lng1_rad
        
        # Formule de la distance haversine
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = earth_radius * c
        
        return round(distance,1)

    except Exception as e:
        print(f"[ERROR][models.models.distance_tag_med] {e}")
        return 1


def get_lastmaj_data_for_all_device(time_limit=3, time_unit='days'):
    query = """
        (SELECT id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc , alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc
        FROM (
            SELECT
                id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc, alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc,
                ROW_NUMBER() OVER (PARTITION BY mac_address ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tag' and activite is not null and lat is not null and lng is not null and mac_address is not null and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
        UNION
        (SELECT id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc , alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc
        FROM (
            SELECT
                id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp,pos_acc, alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc,
                ROW_NUMBER() OVER (PARTITION BY sn ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tracker' and lat is not null and lng is not null and sn is not null and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []

        nb_tag_tracker_process = {}
        
        dict_nbtag, dict_coords_tracker = compute_info_tag(output)

        for row in output:
            
            formated_date = ""
            try:
                formated_date = row[2].strftime("%Y-%m-%d %H:%M:%S") #if row[9] is None else row[9].strftime("%Y-%m-%d %H:%M:%S")
            except:
                formated_date = ""
            
            serial = row[3] if row[1] == "Tracker" else row[5]
            coord1 = (float(row[6].quantize(Decimal('0.0000001'))), float(row[7].quantize(Decimal('0.0000001'))))
            delta_coords, delta_time, prev_activite = delta_coords_delta_time(row[1], coord1, formated_date, serial, row[0])
            
            try:
                prev_activite = float(prev_activite)
            except Exception as e:
                prev_activite = 0

            activite = 0
            try:
                if row[1] == "Tracker":
                    try:
                        activite = float(row[17])
                    except Exception as e:
                        activite = 0          
                else:    
                    activite = float(row[8]) if row[8] is not None else 0
            except:
                pass

            nb_tag = None
            if row[1] == "Tracker":
                if row[3] in dict_nbtag:
                    nb_tag = dict_nbtag[row[3]]
                else:
                    nb_tag = 0                

            asset_type = None
            
            distance = None
            if row[1] == "Tag":
                #distance = float(row[16]) if row[16] is not None else None
                try:
                    distance = distance_tag_med(dict_coords_tracker[row[3]], float(row[6].quantize(Decimal('0.0000001'))), float(row[7].quantize(Decimal('0.0000001'))))
                except:
                    distance = float(row[16]) if row[16] is not None else None

            if row[1] == "Tracker":
                try:
                    asset_type = str(row[18]).split("|")[0]
                except:
                    pass
            elif row[1] == "Tag":
                asset_type = None

            result_dict = {
                "date_heure" : formated_date,
                "name" : row[19] if (row[19] is not None and row[1] == "Tag") else None,
                "type": row[1],
                "sn": row[3],
                "type_materiel" : asset_type,
                "iccid": row[4],
                "mac_address": row[5],
                "lat": float(row[6].quantize(Decimal('0.0000001'))),
                "lng": float(row[7].quantize(Decimal('0.0000001'))),
                "activite": activite,
                "prev_activite" : prev_activite,
                "position_relative": float(row[10]) if row[10] is not None else None,
                "altitude" : float(row[11]) if row[11] is not None else None,
                "direction" : row[12] if row[12] is not None else None,
                "force_signal": float(row[13]) if row[13] is not None else None,
                "voltage_batterie" : float(row[14]) if (row[14] is not None and row[1] == "Tracker") else None,
                "temperature" : row[15] if row[15] is not None else None,
                "nb_tag" : nb_tag,
                "distance" : distance,
                "timezone" : fuseau_horaire_serveur,
                "X" : abs(float(row[20])) if (row[20] is not None) else 0,
                "Y" : abs(float(row[21])) if (row[21] is not None) else 0,
                "Z" : abs(float(row[22])) if (row[22] is not None) else 0,
                "delta_coords" : delta_coords,
                "delta_time" : delta_time
            }
            results.append(result_dict)

        return results

    except Exception as e:
        print(f"[ERROR][models.models.get_lastmaj_data_for_all_device] {e}")
        return []  



def get_lastmaj_data_for_specific_device(list_tracker, list_tag, time_limit=3, time_unit='days'):

    sn_tracker = ', '.join(["'" + str(sn) + "'" for sn in list_tracker])
    mac_tag = ', '.join(["'" + str(sn) + "'" for sn in list_tag])

    query = """
        (SELECT id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc , alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc
        FROM (
            SELECT
                id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc, alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc,
                ROW_NUMBER() OVER (PARTITION BY mac_address ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tag' and  mac_address IN ({mac_tag}) and activite is not null and lat is not null and lng is not null and mac_address is not null and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
        UNION
        (SELECT id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp, pos_acc , alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc
        FROM (
            SELECT
                id, type, receip_datetime, sn, iccid, mac_address, lat, lng, activite, oem_timestamp,pos_acc, alt, cap, pdop, volt_bat, temperature, dout, peak, prod, tag_name, x_acc, y_acc, z_acc,
                ROW_NUMBER() OVER (PARTITION BY sn ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tracker' and  sn IN ({sn_tracker}) and lat is not null and lng is not null and sn is not null and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME, sn_tracker=sn_tracker, mac_tag=mac_tag)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []

        nb_tag_tracker_process = {}
        
        dict_nbtag, dict_coords_tracker = compute_info_tag(output)

        for row in output:
            formated_date = ""
            try:
                formated_date = row[2].strftime("%Y-%m-%d %H:%M:%S") #if row[9] is None else row[9].strftime("%Y-%m-%d %H:%M:%S")
            except:
                formated_date = ""
            
            serial = row[3] if row[1] == "Tracker" else row[5]
            coord1 = (float(row[6].quantize(Decimal('0.0000001'))), float(row[7].quantize(Decimal('0.0000001'))))
            delta_coords, delta_time, prev_activite = delta_coords_delta_time(row[1], coord1, formated_date, serial, row[0])
            
            try:
                prev_activite = float(prev_activite)
            except Exception as e:
                prev_activite = 0

            activite = 0
            try:
                if row[1] == "Tracker":
                    try:
                        activite = float(row[17])
                    except Exception as e:
                        activite = 0          
                else:    
                    activite = float(row[8]) if row[8] is not None else None
            except:
                pass

            nb_tag = None
            if row[1] == "Tracker":
                if row[3] in dict_nbtag:
                    nb_tag = dict_nbtag[row[3]]
                else:
                    nb_tag = 0                

            asset_type = None
            
            distance = None
            if row[1] == "Tag":
                #distance = float(row[16]) if row[16] is not None else None
                try:
                    distance = distance_tag_med(dict_coords_tracker[row[3]], float(row[6].quantize(Decimal('0.0000001'))), float(row[7].quantize(Decimal('0.0000001'))))
                except:
                    distance = float(row[16]) if row[16] is not None else None

            if row[1] == "Tracker":
                try:
                    asset_type = str(row[18]).split("|")[0]
                except:
                    pass
            elif row[1] == "Tag":
                asset_type = None

            result_dict = {
                "date_heure" : formated_date,
                "name" : row[19] if (row[19] is not None and row[1] == "Tag") else None,
                "type": row[1],
                "sn": row[3],
                "type_materiel" : asset_type,
                "iccid": row[4],
                "mac_address": row[5],
                "lat": float(row[6].quantize(Decimal('0.0000001'))),
                "lng": float(row[7].quantize(Decimal('0.0000001'))),
                "activite": activite,
                "prev_activite": prev_activite,
                "position_relative": float(row[10]) if row[10] is not None else None,
                "altitude" : float(row[11]) if row[11] is not None else None,
                "direction" : row[12] if row[12] is not None else None,
                "force_signal": float(row[13]) if row[13] is not None else None,
                "voltage_batterie" : float(row[14]) if (row[14] is not None and row[1] == "Tracker") else None,
                "temperature" : row[15] if row[15] is not None else None,
                "nb_tag" : nb_tag,
                "distance" : distance,
                "timezone" : fuseau_horaire_serveur,
                "X" : abs(float(row[20])) if (row[20] is not None) else 0,
                "Y" : abs(float(row[21])) if (row[21] is not None) else 0,
                "Z" : abs(float(row[22])) if (row[22] is not None) else 0,
                "delta_coords" : delta_coords,
                "delta_time" : delta_time
            }
            results.append(result_dict)

        return results

    except Exception as e:
        print(f"[ERROR][models.models.get_lastmaj_data_for_specific_device] {e}")
        return []

################################### OEM && TG DATA INTEGRATION #########################################

def log_maintenance(table_name="webhook_log", day_limit = 7): # in order to avoid overloading the database, we only keep 75 days of data
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """DELETE FROM """+table_name+""" WHERE date < CURRENT_DATE - INTERVAL '"""+str(day_limit)+""" days' """
        BDD_CUR.execute(query)
        BDD_CONNEX.commit()
        BDD_CUR.close()
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.log_maintenance] {e}")
        return "error"

def database_maintenance(table_name, day_limit = 30): # in order to avoid overloading the database, we only keep 75 days of data
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """DELETE FROM """+table_name+""" WHERE receip_datetime < CURRENT_DATE - INTERVAL '"""+str(day_limit)+""" days' """
        BDD_CUR.execute(query)
        BDD_CONNEX.commit()
        BDD_CUR.close()
        log_maintenance()
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.database_maintenance] {e}")
        return "error"




def insert_structured(data):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = '''INSERT INTO '''+STRUCT_TABLE_NAME+'''(receip_datetime, type, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi)
                     VALUES(current_timestamp, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )'''
        for tup in data:
            BDD_CUR.execute(query, tup)
        BDD_CONNEX.commit()
        BDD_CUR.close()
        database_maintenance(STRUCT_TABLE_NAME)
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.insert_structured] {e}")
        return "error"


def insert_raw(data, endpoint):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """INSERT INTO """+RAW_TABLE_NAME+"""(receip_datetime, json, endpoint)
                     VALUES(current_timestamp, %s, %s)"""
        BDD_CUR.execute(query, (json.dumps(data), endpoint))
        BDD_CONNEX.commit()
        BDD_CUR.close()
        database_maintenance(RAW_TABLE_NAME)
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.insert_raw] {e}")
        return "error"


################################### ALPES ECO V2 ####################################
max_id_app = 0

def get_lastmaj_telemetry(time_limit=15, time_unit='minutes'):
    global max_id_app
    print(f"[INFO][models.models.get_lastmaj_telemetry.max_id_app] {str(max_id_app)}")
    query = """
        (SELECT id, receip_datetime, type1, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, tx_power, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi,
                        reason ,trans_delay ,gps_age ,speed ,used_speed_limit ,speed_band ,local_speed_limit ,
                        speed_acc ,gps_fix_ok ,gps_fix_3d ,din ,driver_id ,trip_type_code ,project_code ,
                        analog1 ,analog2 ,analog3 ,analog4 ,analog5 ,analog6 ,analog7 ,analog8 ,analog9 ,analog10 ,
                        analog11 ,analog12 ,analog13 ,analog14 ,analog15 ,analog16 ,analog17 ,analog18 ,analog19 ,analog20 ,status
        FROM (
            SELECT
                id, type, receip_datetime, type AS type1, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, tx_power, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi,
                        reason ,trans_delay ,gps_age ,speed ,used_speed_limit ,speed_band ,local_speed_limit ,
                        speed_acc ,gps_fix_ok ,gps_fix_3d ,din ,driver_id ,trip_type_code ,project_code ,
                        analog1 ,analog2 ,analog3 ,analog4 ,analog5 ,analog6 ,analog7 ,analog8 ,analog9 ,analog10 ,
                        analog11 ,analog12 ,analog13 ,analog14 ,analog15 ,analog16 ,analog17 ,analog18 ,analog19 ,analog20 ,status,
                ROW_NUMBER() OVER (PARTITION BY mac_address ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tag' and activite is not null and lat is not null and lng is not null and mac_address is not null and id > {max_id_app} and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
        UNION
        (SELECT id, receip_datetime, type2, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, tx_power, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi,
                        reason ,trans_delay ,gps_age ,speed ,used_speed_limit ,speed_band ,local_speed_limit ,
                        speed_acc ,gps_fix_ok ,gps_fix_3d ,din ,driver_id ,trip_type_code ,project_code ,
                        analog1 ,analog2 ,analog3 ,analog4 ,analog5 ,analog6 ,analog7 ,analog8 ,analog9 ,analog10 ,
                        analog11 ,analog12 ,analog13 ,analog14 ,analog15 ,analog16 ,analog17 ,analog18 ,analog19 ,analog20 ,status
        FROM (
            SELECT
                id, receip_datetime, type AS type2, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, tx_power, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi,
                        reason ,trans_delay ,gps_age ,speed ,used_speed_limit ,speed_band ,local_speed_limit ,
                        speed_acc ,gps_fix_ok ,gps_fix_3d ,din ,driver_id ,trip_type_code ,project_code ,
                        analog1 ,analog2 ,analog3 ,analog4 ,analog5 ,analog6 ,analog7 ,analog8 ,analog9 ,analog10 ,
                        analog11 ,analog12 ,analog13 ,analog14 ,analog15 ,analog16 ,analog17 ,analog18 ,analog19 ,analog20 ,status,
                ROW_NUMBER() OVER (PARTITION BY sn ORDER BY receip_datetime DESC) AS order_in_partition
            FROM {table_name} where type = 'Tracker' and lat is not null and lng is not null and sn is not null and id > {max_id_app} and receip_datetime >= NOW() - INTERVAL '{time_limit} {time_unit}'
        ) AS ranked2
        WHERE order_in_partition = 1
        ORDER BY id, receip_datetime)
    """.format(time_limit=time_limit, time_unit=time_unit, max_id_app=max_id_app ,table_name=TELEMETRY_TABLE_NAME)
    ids = []
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []

        for row in output:
            try:
                ids.append(int(row[0]))
                max_id_app = max(ids)
            except:
                pass

            formated_date = ""
            try:
                formated_date = row[1].strftime("%Y-%m-%d %H:%M:%S") 
            except:
                formated_date = ""
            tx_power =None
            try:
                tx_power = float(row[17])
            except:
                tx_power = None

            transmdelay =None
            try:
                transmdelay = float(row[31])
            except:
                transmdelay = None

            gpsAge =None
            try:
                gpsAge = float(row[32])
            except:
                gpsAge = None

            speedBand =None
            try:
                speedBand = float(row[35]) # le modele de donnee ao BO est faux, a l'avenir on va changer en str pas en float
            except:
                speedBand = None

            speedAcc =None
            try:
                speedAcc = float(row[37])
            except:
                speedAcc = None
            result_dict = {
                "all_date_heure" : formated_date, #OK
                "all_type": row[2], #OK FOR WHERE CLAUSE
                "all_lat": float(row[9].quantize(Decimal('0.0000001'))), #OK
                "all_lng": float(row[10].quantize(Decimal('0.0000001'))), #OK
                "tracker_reason" : row[30], #OK
                "tracker_delay" : transmdelay, #OK 
                "tracker_sn": row[5], # OK FOR WHERE CLAUSE
                "tracker_gps_age": gpsAge, # OK
                "tracker_speed": float(row[33]) if row[33] is not None else None, # OK
                "tracker_used_speed_limit": float(row[34]) if row[34] is not None else None, # OK
                "tracker_speed_band": speedBand, # OK
                "tracker_local_speed_limit": float(row[36]) if row[36] is not None else None, # OK
                "tracker_speed_acc": speedAcc, # OK
                "tracker_heading_degrees": row[21], # OK
                "tracker_alt": float(row[20]) if row[20] is not None else None, # OK
                "tracker_pos_acc": float(row[11]) if row[11] is not None else None, # OK
                "tracker_pdop": float(row[22]) if row[22] is not None else None, # OK
                "tracker_gps_fix_ok": row[38], # OK
                "tracker_gps_fix_3d": row[39], # OK
                "tracker_din": float(row[40]) if row[40] is not None else None, # OK
                "tracker_dout": float(row[25]) if row[25] is not None else None, # OK
                "tracker_driver_id": row[41], # OK
                "tracker_trip_type_code": row[42], # OK
                "tracker_project_code": row[43], # OK
                "tracker_analog1": float(row[44]) if row[44] is not None else None, # OK
                "tracker_analog2": float(row[45]) if row[45] is not None else None, # OK
                "tracker_analog3": float(row[46]) if row[46] is not None else None, # OK
                "tracker_analog4": float(row[47]) if row[47] is not None else None, # OK
                "tracker_analog5": float(row[48]) if row[48] is not None else None, # OK
                "tracker_analog6": float(row[49]) if row[49] is not None else None, # OK
                "tracker_analog7": float(row[50]) if row[50] is not None else None, # OK
                "tracker_analog8": float(row[51]) if row[51] is not None else None, # OK
                "tracker_analog9": float(row[52]) if row[52] is not None else None, # OK
                "tracker_analog10": float(row[53]) if row[53] is not None else None, # OK
                "tracker_analog11": float(row[54]) if row[54] is not None else None, # OK
                "tracker_analog12": float(row[55]) if row[55] is not None else None, # OK
                "tracker_analog13": float(row[56]) if row[56] is not None else None, # OK
                "tracker_analog14": float(row[57]) if row[57] is not None else None, # OK
                "tracker_analog15": float(row[58]) if row[58] is not None else None, # OK
                "tracker_analog16": float(row[59]) if row[59] is not None else None, # OK
                "tracker_analog17": float(row[60]) if row[60] is not None else None, # OK
                "tracker_analog18": float(row[61]) if row[61] is not None else None, # OK
                "tracker_analog19": float(row[62]) if row[62] is not None else None, # OK
                "tracker_analog20": float(row[63]) if row[63] is not None else None, # OK
                "tag_mac_address": row[12], # OK FOR WHERE CLAUSE
                "tag_gateway":  row[5], #OK
                "tag_gateway_pos_acc":  float(row[11]) if row[11] is not None else None, #OK
                "tag_gateway_speed":  float(row[33]) if row[33] is not None else None, #OK
                "tag_status":  str(row[64]) if row[64] is not None else None, #OK
                "tag_battery_voltage":  None, #OK
                "tag_rssi":  float(row[29]) if row[29] is not None else None, #OK
                "tag_tx_power": tx_power, #OK
                "tag_x_acc":  float(row[14]) if row[14] is not None else None, #OK
                "tag_y_acc":  float(row[15]) if row[15] is not None else None, #OK
                "tag_z_acc":  float(row[16]) if row[16] is not None else None, #OK
                "timezone" : fuseau_horaire_serveur
            }
            results.append(result_dict)


        return results

    except Exception as e:
        print(f"[ERROR][models.models.get_lastmaj_telemetry] {e}")
        return []


def get_last_tracker_telemetry(serial_number, day_limit=1):
    lat = None
    lng = None
    posAcc = None
    speed = None
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute("select lat, lng, pos_acc, speed from "+TELEMETRY_TABLE_NAME+" where sn = '" +
                        str(serial_number)+"'  and type = 'Tracker' and lat is not null and lng is not null  and receip_datetime >= CURRENT_DATE - INTERVAL '"+str(day_limit)+" days' order by receip_datetime DESC limit 1")
        output = BDD_CUR.fetchall()

        for val in output:
            lat = val[0]
            lng = val[1]
            posAcc = val[2]
            speed = val[3]
        BDD_CUR.close()
        return [lat, lng, posAcc, speed]
    except Exception as e:
        print(f"[ERROR][models.models.get_last_tracker_telemetry] {e}")
        return [lat, lng, posAcc, speed]


def insert_telemetry(data):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = '''INSERT INTO '''+TELEMETRY_TABLE_NAME+'''(receip_datetime, type, date_oem, oem_timestamp, sn, prod, iccid, imei, lat, lng, pos_acc, 
                        mac_address, tag_name, x_acc, y_acc, z_acc, tx_power, activite, endpoint, 
                        alt, cap, pdop, volt_bat, temperature, dout, peak, average, duration, rssi,
                        reason ,trans_delay ,gps_age ,speed ,used_speed_limit ,speed_band ,local_speed_limit ,
                        speed_acc ,gps_fix_ok ,gps_fix_3d ,din ,driver_id ,trip_type_code ,project_code ,
                        analog1 ,analog2 ,analog3 ,analog4 ,analog5 ,analog6 ,analog7 ,analog8 ,analog9 ,analog10 ,
                        analog11 ,analog12 ,analog13 ,analog14 ,analog15 ,analog16 ,analog17 ,analog18 ,analog19 ,analog20, status)
                     VALUES(current_timestamp, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )'''
        for tup in data:
            BDD_CUR.execute(query, tup)
        BDD_CONNEX.commit()
        BDD_CUR.close()
        database_maintenance(TELEMETRY_TABLE_NAME)
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.insert_telemetry] {e}")
        return "error"

 
def process_base_individuelle(time_limit=3, time_unit='days'):
    query = """
            WITH daily_data AS (
                SELECT 
                    sn,
                    date_trunc('day', receip_datetime) AS day,
                    CASE 
                        WHEN EXTRACT(HOUR FROM receip_datetime) BETWEEN 6 AND 18 THEN 'diurne'
                        ELSE 'nocturne'
                    END AS time_period,
                    MAX(alt) AS max_altitude,
                    MIN(alt) AS min_altitude
                FROM {table_name}
                WHERE receip_datetime >= CURRENT_DATE - INTERVAL '{time_limit} {time_unit}'
                AND receip_datetime <= CURRENT_DATE + INTERVAL '1 day' 
                AND type = 'Tracker'
                GROUP BY sn, day, time_period
            ),
            daily_data_general AS (
                SELECT 
                    sn,
                    date_trunc('day', receip_datetime) AS day,
                    MAX(alt) AS max_altitude,
                    MIN(alt) AS min_altitude
                FROM {table_name}
                WHERE receip_datetime >= CURRENT_DATE - INTERVAL '{time_limit} {time_unit}'
                AND receip_datetime <= CURRENT_DATE + INTERVAL '1 day' 
                AND type = 'Tracker'
                GROUP BY sn, day
            ),
            sorted_data AS (
                SELECT 
                    sn,
                    receip_datetime,
                    lat,
                    lng,
                    COALESCE(LAG(lat) OVER (PARTITION BY sn ORDER BY receip_datetime),lat) AS prev_lat,
                    COALESCE(LAG(lng) OVER (PARTITION BY sn ORDER BY receip_datetime),lng) AS prev_lng
                FROM {table_name}
                WHERE receip_datetime >= CURRENT_DATE - INTERVAL '{time_limit} {time_unit}'
                AND receip_datetime <= CURRENT_DATE + INTERVAL '1 day'
                AND lat is not null AND lng is not null
                AND type = 'Tracker'
            ),
            distances AS (
                SELECT 
                    date_trunc('day', receip_datetime) AS day,
                    CASE 
                        WHEN EXTRACT(HOUR FROM receip_datetime) BETWEEN 6 AND 18 THEN 'diurne'
                        ELSE 'nocturne'
                    END AS time_period,
                    sn,
                    6372.795477598 * acos(
                        LEAST(GREATEST(
                            cos(radians(lat)) * cos(radians(prev_lat)) * cos(radians(prev_lng) - radians(lng)) +
                            sin(radians(lat)) * sin(radians(prev_lat))
                        , -1), 1)
                    ) AS distance
                FROM sorted_data
                WHERE prev_lat IS NOT NULL AND prev_lng IS NOT NULL
                AND prev_lat > 0 AND prev_lng > 0
            ),
            distances_general AS (
                SELECT 
                    date_trunc('day', receip_datetime) AS day,
                    sn,
                    6372.795477598 * acos(
                        LEAST(GREATEST(
                            cos(radians(lat)) * cos(radians(prev_lat)) * cos(radians(prev_lng) - radians(lng)) +
                            sin(radians(lat)) * sin(radians(prev_lat))
                        , -1), 1)
                    ) AS distance
                FROM sorted_data
                WHERE prev_lat IS NOT NULL AND prev_lng IS NOT NULL
                AND prev_lat > 0 AND prev_lng > 0
            ),
            daily_distance AS (
                SELECT 
                    sn,
                    day,
                    time_period,
                    SUM(distance) AS total_distance_km
                FROM distances
                GROUP BY sn, time_period, day
            ),
            avg_distance AS (
                SELECT 
                    sn,
                    time_period,
                    AVG(total_distance_km) AS avg_dist_daily
                FROM daily_distance
                GROUP BY sn, time_period
            ),
            daily_distance_general AS (
                SELECT 
                    sn,
                    day,
                    SUM(distance) AS total_distance_km
                FROM distances_general
                GROUP BY sn, day
            ),
            avg_distance_general AS (
                SELECT 
                    sn,
                    AVG(total_distance_km) AS avg_dist_general
                FROM daily_distance_general
                GROUP BY sn
            ),
            daily_differences AS (
                SELECT 
                    sn,
                    time_period,
                    day,
                    MAX(max_altitude - min_altitude) AS daily_difference
                FROM daily_data
                GROUP BY sn, time_period, day
            ),
            daily_averages AS (
                SELECT 
                    sn,
                    time_period,
                    AVG(daily_difference) AS average_difference
                FROM daily_differences
                GROUP BY sn, time_period
            ),
            daily_differences_general AS (
                SELECT 
                    sn,
                    day,
                    MAX(max_altitude - min_altitude) AS daily_difference
                FROM daily_data_general
                GROUP BY sn, day
            ),
            daily_averages_general AS (
                SELECT 
                    sn,
                    AVG(daily_difference) AS average_difference_general
                FROM daily_differences_general
                GROUP BY sn
            )
            SELECT 
                d.sn,
                 ROUND(CAST(MAX(CASE WHEN d.time_period = 'diurne' THEN average_difference END) AS numeric), 2) AS d_avg_deniv,
                ROUND(CAST(MAX(CASE WHEN d.time_period = 'nocturne' THEN average_difference END) AS numeric), 2) AS n_avg_deniv,
                ROUND(CAST(MAX(average_difference_general) AS numeric), 2) AS g_avg_deniv,
                ROUND(CAST(MAX(CASE WHEN a.time_period = 'diurne' THEN avg_dist_daily END) AS numeric), 2) AS d_avg_dist,
                ROUND(CAST(MAX(CASE WHEN a.time_period = 'nocturne' THEN avg_dist_daily END) AS numeric), 2) AS n_avg_dist,
                ROUND(CAST(MAX(b.avg_dist_general) AS numeric), 2) AS g_avg_dist 
            FROM daily_averages d
            LEFT JOIN daily_averages_general g ON g.sn = d.sn
            LEFT JOIN avg_distance a ON a.sn = d.sn
            LEFT JOIN avg_distance_general b ON b.sn = d.sn
            GROUP BY d.sn
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request execute
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []
        data = {}
        for row in output:
            serial = row[0]
            if str(serial) not in data.keys():
                data[str(serial)] = {
                                        "deniv_diurne" : float(row[1]) if row[1] is not None else None, 
                                        "deniv_nocturne" : float(row[2]) if row[2] is not None else None, 
                                        "deniv_general" : float(row[3]) if row[3] is not None else None,
                                        "dist_diurne" : float(row[4]) if row[4] is not None else None, 
                                        "dist_nocturne" : float(row[5]) if row[5] is not None else None, 
                                        "dist_general" : float(row[6]) if row[6] is not None else None
                                    }
        return data

    except Exception as e:
        print(f"[ERROR][models.models.process_base_individuelle] {e}")
        return {}




def get_denivele_positif(time_limit=3, time_unit='days'):
    query = """
            WITH sorted_data AS (
                SELECT 
                    sn, 
                    receip_datetime, 
                    alt, 
                    LAG(alt) OVER (PARTITION BY sn ORDER BY receip_datetime) AS prev_alt
                FROM {table_name}
                WHERE date_trunc('day', receip_datetime) = CURRENT_DATE
            ),
            positive_gain AS (
                SELECT 
                    sn, 
                    receip_datetime::date AS day,
                    GREATEST(alt - prev_alt, 0) AS gain
                FROM sorted_data
                WHERE prev_alt IS NOT NULL
            ),
            daily_positive_gain AS (
                SELECT 
                    sn, 
                    day,
                    SUM(gain) AS daily_positive_gain
                FROM positive_gain
                GROUP BY sn, day
            ),
            max_daily_positive_gain AS (
                SELECT 
                    sn,
                    MAX(daily_positive_gain) AS positive_gain
                FROM daily_positive_gain
                GROUP BY sn
            )
            SELECT 
                sn,
                ROUND(CAST(positive_gain AS numeric), 2)
            FROM max_daily_positive_gain
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request execute
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []
        data = {}
        for row in output:
            serial = row[0]
            if str(serial) not in data.keys():
                data[str(serial)] = {"total_denivele_positif" : float(row[1]) if row[1] is not None else 0}

        return data

    except Exception as e:
        print(f"[ERROR][models.models.get_denivele_positif] {e}")
        return {}



def get_distance(time_limit=3, time_unit='days'):
    query = """
            WITH sorted_data AS (
                SELECT 
                    sn,
                    receip_datetime,
                    lat,
                    lng,
                    COALESCE(LAG(lat) OVER (PARTITION BY sn ORDER BY receip_datetime),lat) AS prev_lat,
                    COALESCE(LAG(lng) OVER (PARTITION BY sn ORDER BY receip_datetime),lng) AS prev_lng
                FROM {table_name}
                WHERE date_trunc('day', receip_datetime) = CURRENT_DATE
                AND type = 'Tracker'
            ),
            distances AS (
                SELECT 
                    sn,
                    6372.795477598 * acos(
                        LEAST(GREATEST(
                            cos(radians(lat)) * cos(radians(prev_lat)) * cos(radians(prev_lng) - radians(lng)) +
                            sin(radians(lat)) * sin(radians(prev_lat))
                        , -1), 1)
                    ) AS distance
                FROM sorted_data
                WHERE prev_lat IS NOT NULL AND prev_lng IS NOT NULL
                AND prev_lat > 0 AND prev_lng > 0
            )
            SELECT 
                sn,
                ROUND(CAST(SUM(distance) AS numeric), 2) AS total_distance_km
            FROM distances
            GROUP BY sn
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request execute
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []
        data = {}
        for row in output:
            serial = row[0]
            if str(serial) not in data.keys():
                data[str(serial)] = {"total_distance" : float(row[1]) if row[1] is not None else 0}

        return data

    except Exception as e:
        print(f"[ERROR][models.models.get_distance] {e}")
        return {}


def get_daily_perf(time_limit=3, time_unit='days'):
    query = """
            
                SELECT 
                    sn,
                    ROUND(CAST(AVG(alt) AS numeric), 2),
                    ROUND(CAST(MIN(alt) AS numeric), 2),
                    ROUND(CAST(MAX(alt) AS numeric), 2),
                    ROUND(CAST(AVG(temperature) AS numeric), 2),
                    ROUND(CAST(MIN(temperature) AS numeric), 2),
                    ROUND(CAST(MAX(temperature) AS numeric), 2)
                FROM {table_name}
                WHERE date_trunc('day', receip_datetime) = CURRENT_DATE
                GROUP BY sn
            
    """.format(time_limit=time_limit, time_unit=time_unit ,table_name=STRUCT_TABLE_NAME)
    #print(query)
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request execute
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results = []
        data = {}
        for row in output:
            serial = row[0]
            if str(serial) not in data.keys():

                data[str(serial)] = {
                    "avg_alt" : float(row[1]) if row[1] is not None else None,
                    "min_alt" : float(row[2]) if row[2] is not None else None,
                    "max_alt" : float(row[3]) if row[3] is not None else None,
                    "avg_temperature" : float(row[4]) if row[4] is not None else None,
                    "min_temperature" : float(row[5]) if row[5] is not None else None,
                    "max_temperature" : float(row[6]) if row[6] is not None else None
                    }

        return data

    except Exception as e:
        print(f"[ERROR][models.models.get_daily_perf] {e}")
        return {}


# device_weather_data storage, do not call the api every as need weather data, only call every 3 hour for every device
device_weather_data = {}

def estimate_relative_humidity(temperature, datetime):
    try:
        # Splitting datetime into month and hour
        month = datetime.month
        hour = datetime.hour

        # Estimation based on temperature, month, and hour
        if month in [12, 1, 2]:  # Winter
            if hour >= 8 and hour <= 18:  # Daytime
                if temperature >= 10:
                    return 60
                else:
                    return 80
            else:  # Nighttime
                return 80
        elif month in [3, 4, 5]:  # Spring
            if hour >= 7 and hour <= 19:  # Daytime
                if temperature >= 15:
                    return 50
                else:
                    return 70
            else:  # Nighttime
                return 70
        elif month in [6, 7, 8]:  # Summer
            if hour >= 6 and hour <= 20:  # Daytime
                if temperature >= 25:
                    return 40
                else:
                    return 60
            else:  # Nighttime
                return 60
        elif month in [9, 10, 11]:  # Autumn
            if hour >= 7 and hour <= 18:  # Daytime
                if temperature >= 20:
                    return 50
                else:
                    return 70
            else:  # Nighttime
                return 70
    except Exception as e:
        print(f"[ERROR][utils.utils.estimate_relative_humidity] {e}")
        return 55


def diff_hour(datetime1, datetime2):
    try:
        diff = datetime1 - datetime2
        return diff.total_seconds() / 3600
    except Exception as e:
        return 3

def process_thi_perso(temperature, humidity):
    if temperature is not None and humidity is not None:
        thi = temperature - ((0.55 - 0.0055 * humidity) * (temperature - 14.5))
    else:
        thi = None
    return thi


def get_weather_data(serial, latitude, longitude, temperature, api_key='68524bb768bf4b17ab3133216241705'):
    try:
        global device_weather_data
        current_datetime = datetime.now()
        ########### get weather data for device serial ####################################
        if str(serial) in device_weather_data.keys():
            if device_weather_data[str(serial)]["update_at"] is not None: #      revoir implementation
                if abs(diff_hour(current_datetime, device_weather_data[str(serial)]["update_at"])) < 4: # if inf 3hour, get stock data
                    humidity = device_weather_data[str(serial)]['Humidity_(%)']
                    thi_perso = process_thi_perso(temperature, humidity)
                    device_weather_data[str(serial)]['thi_personel'] = thi_perso
                    return device_weather_data[str(serial)]

        ########### call api for new weather data for device serial ####################################
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={latitude},{longitude}&days=1"
        
        response = requests.get(url)
        data = response.json()
        
        
        # Extract relevant weather data
        forecast = data['forecast']['forecastday'][0]['day']
        
        precipitation = forecast.get('totalprecip_mm', None)
        cloud_cover = forecast.get('avgvis_km', None)
        temp_max = forecast.get('maxtemp_c', None)
        temp_min = forecast.get('mintemp_c', None)
        humidity = forecast.get('avghumidity', None)
        wind_max = forecast.get('maxwind_kph', None)
        pressure = forecast.get('pressure_mb', None)
        
        try:  
            precipitation = float(precipitation) if precipitation is not None else None
        except:
            precipitation = None

        try:  
            cloud_cover = float(cloud_cover) if cloud_cover is not None else None
        except:
            cloud_cover = None

        try:  
            wind_max = float(wind_max) if wind_max is not None else None
        except:
            wind_max = None

        try:  
            pressure = float(pressure) if pressure is not None else None
        except:
            pressure = None


        if humidity is None:
            humidity = float(estimate_relative_humidity(temperature, current_datetime))
        if temp_max is None:
            temp_max = temperature

        # Calculate THI if temperature and humidity are available
        if temp_max is not None and humidity is not None:
            thi = temp_max - ((0.55 - 0.0055 * humidity) * (temp_max - 14.5))
        else:
            thi = None
        
        # Check if request was successful
        if all(elt is None for elt in (precipitation, cloud_cover, temp_min, wind_max, pressure, thi)): #request api failed
            if str(serial) in device_weather_data.keys():
                if device_weather_data[str(serial)]["update_at"] is not None and device_weather_data[str(serial)]["status"] == 'success': # don't maj data
                    device_weather_data[str(serial)]['thi_personel'] = process_thi_perso(temperature, humidity) # update only thi personnel
                else:
                    device_weather_data[str(serial)] = {
                                        'Precipitation_(mm/day)': None,
                                        'Cloud_Cover_(%)': None,
                                        'Max_Temperature_(°C)': temperature,
                                        'Min_Temperature_(°C)': temperature,
                                        'Humidity_(%)': float(estimate_relative_humidity(temperature, current_datetime)),
                                        'Max_Wind_Speed_(Km/h)': None,
                                        'Pressure_(MB)': None,
                                        'THI_Index': None,
                                        'thi_personel' : process_thi_perso(temperature, humidity),
                                        'update_at': None,
                                        'status' : 'temprorary' # valeur temporaire
                                    }
            else:
                device_weather_data[str(serial)] = {
                                        'Precipitation_(mm/day)': None,
                                        'Cloud_Cover_(%)': None,
                                        'Max_Temperature_(°C)': temperature,
                                        'Min_Temperature_(°C)': temperature,
                                        'Humidity_(%)': float(estimate_relative_humidity(temperature, current_datetime)),
                                        'Max_Wind_Speed_(Km/h)': None,
                                        'Pressure_(MB)': None,
                                        'THI_Index': None,
                                        'thi_personel' : process_thi_perso(temperature, humidity),
                                        'update_at': None,
                                        'status' : 'temprorary' # valeur temporaire
                                    }
        else: # request api success
            device_weather_data[str(serial)] = {
                    'Precipitation_(mm/day)': precipitation,
                    'Cloud_Cover_(%)': cloud_cover,
                    'Max_Temperature_(°C)': temp_max,
                    'Min_Temperature_(°C)': temp_min,
                    'Humidity_(%)': humidity,
                    'Max_Wind_Speed_(Km/h)': wind_max,
                    'Pressure_(MB)': pressure,
                    'THI_Index': thi,
                    'thi_personel' : process_thi_perso(temperature, humidity),
                    'update_at': datetime.now(),
                    'status' : 'success'
                }

        return device_weather_data[str(serial)]
    except Exception as e:
        print(f"[ERROR][models.models.get_weather_data] {e}")
        current_datetime = datetime.now()
        humidity = float(estimate_relative_humidity(temperature, current_datetime))
        return {
                'Precipitation_(mm/day)': None,
                'Cloud_Cover_(%)': None,
                'Max_Temperature_(°C)': temperature,
                'Min_Temperature_(°C)': temperature,
                'Humidity_(%)': humidity,
                'Max_Wind_Speed_(Km/h)': None,
                'Pressure_(MB)': None,
                'THI_Index': None,
                'thi_personel' : process_thi_perso(temperature, humidity),
                'update_at': None,
                'status' : 'temprorary'
            }



def process_depense_eneregetique(base_indiv_value, time_period):
    try:
        base_indiv_value = math.floor(base_indiv_value)
        if time_period == 'general':
            if base_indiv_value is not None and base_indiv_value > 0:
                return 9/10/1000*8/base_indiv_value*1000
            else:
                return None
        elif time_period == 'diurnal':
            if base_indiv_value is not None and base_indiv_value > 0:
                return 12/13/1000*11/base_indiv_value*1000
            else:
                return None
        elif time_period == 'nocturnal':
            if base_indiv_value is not None and base_indiv_value > 0:
                return 15/16/1000*14/base_indiv_value*1000
            else:
                return None
        else:
            return None
    except Exception  as e:
        print(f"[ERROR][models.models.process_depense_eneregetique] {e}")
        return None


def get_lastmaj_analysis(time_limit=3, time_unit='days'):
    
    try:
        data_base_individuelle = process_base_individuelle(time_limit=3, time_unit='days')
        data_daily_perf = get_daily_perf()
        data_denivele_positif = get_denivele_positif()
        data_distance = get_distance()
        data_base_daily = process_base_individuelle(time_limit=0, time_unit='day')
        
        list_sn = list(data_base_individuelle.keys())+list(data_denivele_positif.keys())+list(data_distance.keys())+list(data_daily_perf.keys())+list(data_base_daily.keys())
        serial_list = set(list_sn)
        data_return = []
        data_analysis = {}
        #print("serial_list =====================",serial_list)
        index = 0
        for serial in serial_list:
            index = index + 1
            #print(serial)
            lat, lng,_,_,_,_,_, temperature,_ = get_last_tracker_info(serial, day_limit=2)
            if lat is None and lng is None:
                continue

            weather_data = get_weather_data(serial, lat, lng, temperature)

            if str(serial) not in data_base_individuelle.keys():
                data_base_individuelle[str(serial)] = {"deniv_diurne" : None, "deniv_nocturne" : None, "deniv_general" : None,
                                                        "dist_diurne" : None, "dist_nocturne" : None, "dist_general" : None}
            if str(serial) not in data_daily_perf.keys():
                data_daily_perf[str(serial)] = {
                    "avg_alt" : None,
                    "min_alt" : None,
                    "max_alt" : None,
                    "avg_temperature" : None,
                    "min_temperature" : None,
                    "max_temperature" : None
                    }
            if str(serial) not in data_denivele_positif.keys():
                data_denivele_positif[str(serial)] = {
                    "total_denivele_positif" : None
                    }

            if str(serial) not in data_distance.keys():
                data_distance[str(serial)] = {
                    "total_distance" : None
                    }

            if str(serial) not in data_base_daily.keys():
                data_base_daily[str(serial)] = {"deniv_diurne" : None, "deniv_nocturne" : None, "deniv_general" : None,
                                                        "dist_diurne" : None, "dist_nocturne" : None, "dist_general" : None}

            data_analysis[str(serial)] = {
                "individualBase" : {
                    "general" : {
                        "deniveleAverageDaily" : data_base_individuelle[str(serial)]["deniv_general"],
                        "distanceAverageDaily" : data_base_individuelle[str(serial)]["dist_general"]
                    },
                    "diurnal" : {
                        "deniveleAverageDaily" : data_base_individuelle[str(serial)]["deniv_diurne"],
                        "distanceAverageDaily" : data_base_individuelle[str(serial)]["dist_diurne"]
                    },
                    "nocturnal" : {
                        "deniveleAverageDaily" : data_base_individuelle[str(serial)]["deniv_nocturne"],
                        "distanceAverageDaily" : data_base_individuelle[str(serial)]["dist_nocturne"]
                    }
                },

                "dailyPerformance" : {
                    "altitudeAverage": data_daily_perf[str(serial)]["avg_alt"],       
                    "altitudeMin": data_daily_perf[str(serial)]["min_alt"],           
                    "altitudeMax": data_daily_perf[str(serial)]["max_alt"],           
                    "temperatureAverage": data_daily_perf[str(serial)]["avg_temperature"],     
                    "temperatureMax": data_daily_perf[str(serial)]["max_temperature"],         
                    "temperatureMin": data_daily_perf[str(serial)]["min_temperature"],         
                    "denivelePositive": data_denivele_positif[str(serial)]["total_denivele_positif"],    
                    "distanceTraveled": data_distance[str(serial)]["total_distance"], # distance parcourue currente day, maj jusqu 24h 
                    "distanceTraveledDiurnal": data_base_daily[str(serial)]["dist_diurne"],# pas dans le cdc
                    "distanceTraveledNocturnal": data_base_daily[str(serial)]["dist_nocturne"], # pas dans le cdc
                    "indexTHIPersonal": weather_data['thi_personel'],      
                    "deniveleDiurnal": data_base_daily[str(serial)]["deniv_diurne"],       # pas dans le cdc
                    "deniveleNocturnal": data_base_daily[str(serial)]["deniv_diurne"],      # pas dans le cdc
                    "energyExpenseGeneral": process_depense_eneregetique(data_base_daily[str(serial)]["dist_general"], 'general'),   # a faire/calculer
                    "energyExpenseDiurnal": process_depense_eneregetique(data_base_daily[str(serial)]["dist_diurne"], 'diurnal'),   # a faire/calculer
                    "energyExpenseNocturnal": process_depense_eneregetique(data_base_daily[str(serial)]["dist_nocturne"], 'nocturnal'),# a faire/calculer
                    "extraordinaryNocturnal": None, # a faire au BO == du coup remettre le valeur deja dans le Bo 
                    "dangerNocturnal": None,          # a faire au BO == du coup remettre le valeur deja dans le Bo
                    "extraordinaryDiurnal": None,    # a faire au BO == du coup remettre le valeur deja dans le Bo
                    "dangerDiurnal": None           # a faire au BO == du coup remettre le valeur deja dans le Bo
                },

                "localWeather" : {
                    "precipitation":  weather_data['Precipitation_(mm/day)'],
                    "cloudCover":   weather_data['Cloud_Cover_(%)'],  
                    "temperatureMax" :weather_data['Max_Temperature_(°C)'],
                    "temperatureMin": weather_data['Min_Temperature_(°C)'],
                    "humidityLevel":  weather_data['Humidity_(%)'],
                    "WindSpeedMax":  weather_data['Max_Wind_Speed_(Km/h)'], 
                    "pressure":  weather_data['Pressure_(MB)'],     
                    "lunarCycle":   None,  
                    "indexTHI":weather_data['THI_Index']
                }
            }
            if index % 2 == 0:
                data_return.append(data_analysis)
                data_analysis = {}
            if index == len(serial_list):
                data_return.append(data_analysis)
        return data_return
    except Exception as e:
        print(f"[ERROR][models.models.get_lastmaj_analysis] {e}")
        return []



################################### WEBHOOK #########################################
# disable all other api on create new
def disable_api_on_new(data):
    try:
        status, _type_= data[0][6], data[0][0]
        status = int(status)
        if status == 1:
            BDD_CUR = bdd_connection(CONFIG_POSTGRES)
            query_status_manage = "UPDATE "+API_TABLE_NAME+" SET status=0 where type = '"+_type_+"'"
            BDD_CUR.execute(query_status_manage)
            BDD_CONNEX.commit()
            BDD_CUR.close()
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.disable_api_on_new] {e}")



# save_api
def sv_api(data):
    try:
        #disable_api_on_new(data)
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """INSERT INTO """+API_TABLE_NAME+"""(d_creation, type, env, name, description, url, login, password, status, hkey1, hkey2, hkey3, hkey4, hvalue1, hvalue2, hvalue3, hvalue4 )
                     VALUES(current_timestamp, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        for tup in data:
            BDD_CUR.execute(query, tup)
        BDD_CONNEX.commit()
        BDD_CUR.close()

        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.sv_webhook] {e}")
        return "error"


# disable all other api if one api is set to active
def disable_api_management(data):
    try:
        status, id_api = data[0][5], data[0][14]
        status = int(status)
        if status == 1:
            BDD_CUR = bdd_connection(CONFIG_POSTGRES)
            BDD_CUR.execute("select type from "+API_TABLE_NAME+" where id = " +
                        str(id_api)+" limit 1")
            _type_ = ""
            output = BDD_CUR.fetchall()
            for row in output:
                _type_ = row[0]

            query_status_manage = "UPDATE "+API_TABLE_NAME+" SET status=0 where type = '"+_type_+"' and id <> "+str(id_api)
            BDD_CUR.execute(query_status_manage)
            BDD_CONNEX.commit()
            BDD_CUR.close()
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.disable_api_management] {e}")
        


# upd_api
def upd_api(data):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """
                UPDATE {table_name}
                SET env = %s, name = %s, description = %s, url = %s, login = %s, password = %s,
                    status = %s, hkey1 = %s, hkey2 = %s, hkey3 = %s, hkey4 = %s,
                    hvalue1 = %s, hvalue2 = %s, hvalue3 = %s, hvalue4 = %s
                WHERE id = %s
            """.format(table_name=API_TABLE_NAME)

        for tup in data:
            BDD_CUR.execute(query, tup)

        BDD_CONNEX.commit()
        BDD_CUR.close()
        #disable_api_management(data)
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.upd_api] {e}")
        return "error"
    



# del_api
def del_api(data):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = "DELETE FROM {table_name} WHERE id = %s".format(table_name=API_TABLE_NAME)

        for tup in data:
            BDD_CUR.execute(query, tup)

        BDD_CONNEX.commit()
        BDD_CUR.close()
        return "success"
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.upd_api] {e}")
        return "error"


# get_all_api
#_type_ in ['webhook', 'geofencing']
def get_all_api(_type_):
    
    try:
        out_lst = []
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute("select id, type, name, description, url, login, password, status, hkey1, hkey2, hkey3, hkey4, hvalue1, hvalue2, hvalue3, hvalue4, env FROM "+API_TABLE_NAME+" where type = '" + str(_type_)+"' ORDER BY id ASC")
        output = BDD_CUR.fetchall()

        for val in output:
            out_dict = {}
            out_dict["id"] = val[0]
            out_dict["type"] = val[1]
            out_dict["name"] = val[2]
            out_dict["description"] = val[3]
            out_dict["url"] = val[4]
            out_dict["login"] = val[5]
            out_dict["password"] = val[6]
            out_dict["status"] = val[7]
            out_dict["hk1"] = val[8]
            out_dict["hk2"] = val[9]
            out_dict["hk3"] = val[10]
            out_dict["hk4"] = val[11]
            out_dict["hv1"] = val[12]
            out_dict["hv2"] = val[13]
            out_dict["hv3"] = val[14]
            out_dict["hv4"] = val[15]
            out_dict["env"] = val[16]
            out_lst.append(out_dict)

        BDD_CUR.close()
        return out_lst
    except Exception as e:
        print(f"[ERROR][models.models.get_all_api] {e}")
        return []


# get_api
#_type_ in ['webhook', 'geofencing']
def get_api_active(_type_='webhook', status_api=1, env='TEST1'):
    
    try:
        out_lst = []
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        # request last tracker geoloc position
        BDD_CUR.execute("select id, type, name, description, url, login, password, status, hkey1, hkey2, hkey3, hkey4, hvalue1, hvalue2, hvalue3, hvalue4 FROM "+API_TABLE_NAME+" where type = '" + str(_type_)+"' and status = " + str(status_api)+" and env = '" + str(env)+"' ORDER BY id ASC")
        output = BDD_CUR.fetchall()

        for val in output:
            out_dict = {}
            out_dict["id"] = val[0]
            out_dict["type"] = val[1]
            out_dict["name"] = val[2]
            out_dict["description"] = val[3]
            out_dict["url"] = val[4]
            out_dict["login"] = val[5]
            out_dict["password"] = val[6]
            out_dict["status"] = val[7]
            out_dict["hk1"] = val[8]
            out_dict["hk2"] = val[9]
            out_dict["hk3"] = val[10]
            out_dict["hk4"] = val[11]
            out_dict["hv1"] = val[12]
            out_dict["hv2"] = val[13]
            out_dict["hv3"] = val[14]
            out_dict["hv4"] = val[15]
            out_lst.append(out_dict)

        BDD_CUR.close()
        return out_lst
    except Exception as e:
        print(f"[ERROR][models.models.get_all_api] {e}")
        return []


# save_log
def save_log(data):
    try:
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        query = """INSERT INTO """+WEBHOOK_LOG_TABLE_NAME+"""(date ,id_api, url, method, status, exception, response)
                     VALUES(current_timestamp, %s, %s, %s, %s, %s, %s)"""
        for tup in data:
            BDD_CUR.execute(query, tup)
        BDD_CONNEX.commit()
        BDD_CUR.close()
    except Exception as e:
        try:
            BDD_CONNEX.rollback()
        except:
            pass
        print(f"[ERROR][models.models.save_log] {e}")



def query_process(query):    
    try:
        out_lst = []
        BDD_CUR = bdd_connection(CONFIG_POSTGRES)
        BDD_CUR.execute(query)
        output = BDD_CUR.fetchall()
        results_as_strings = [str(result) for result in output]
        BDD_CUR.close()
        return results_as_strings
    except Exception as e:
        print(f"[ERROR][models.models.query_process] {e}")
        return []