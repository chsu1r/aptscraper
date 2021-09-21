import requests
from decouple import config, UndefinedValueError
import requests
import urllib.parse
import geopy.distance
import json
import os

CACHE_PATH = "cache/"
CACHE_TOP_FILENAME = "cached_apt_results.json"
CACHE_APTS_FILENAME = "cached_apt_info.json"

RADIUS = 2000  # meters
MODES = ["driving", "walking", "bicycling", "transit"]
WORK_PLACE_ID = "place_id:ChIJi0hJ7LNbwokR6hCyn5HFhRY"

def generate_find_url(api_key, radius, lat, lon, search_query):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {"locationbias":"circle:" + str(radius) + "@" + lat + "," + lon, "inputtype": "textquery", "input": search_query, "fields": "formatted_address,name,geometry", "key": api_key}
    url += "?" + urllib.parse.urlencode(params)
    return url

def generate_commute_url(api_key, lat, lon, method):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {'origin': str(lat) + "," + str(lon),'destination': WORK_PLACE_ID, "key": api_key, "mode": method}
    if method != 'transit':
        params["departure_time"] = "1663245954"
    else:
        params["departure_time"] = "1632314754"

    url += "?" + urllib.parse.urlencode(params)
    return url

class MapsLookup(object):
    def __init__(self, apt_name, scraper=None, debug=False):
        self.debug = debug
        try:
            self.api_key = config('GOOGLE_MAPS_KEY')
        except UndefinedValueError:
            print("MAPS KEY could not be found. Setting debug to TRUE")
            self.debug = True
            self.api_key = ""
        self.apt_name = apt_name
        self.apt_info = {}
        if scraper is None:
            self.apt_info[self.apt_name] = self.load_from_cache(CACHE_PATH + CACHE_APTS_FILENAME)
        else:
            self.apt_info = scraper.apt_info

    def exists_in_cache(self, path):
        if not os.path.isfile(path): return False
        with open(path) as infile:
            all_apts = json.load(infile)
            return self.apt_name in all_apts.keys()

    def load_from_cache(self, path):
        assert self.exists_in_cache(path)
        with open(path) as infile:
            all_apts = json.load(infile)
            return all_apts[self.apt_name]

    def write_to_cache(self, data, path):
        to_write = data.copy()
        if os.path.isfile(path):
            with open(path) as infile:
                all_apts = json.load(infile)
                all_apts[self.apt_name] = data[self.apt_name]
                to_write = all_apts
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(to_write, f, ensure_ascii=False, indent=4)
    
    def get_commute_times(self, force_refresh=False):
        lat, lon = self.apt_info[self.apt_name]["lat"], self.apt_info[self.apt_name]["lon"]
        if "commute" in self.apt_info[self.apt_name] and self.apt_info[self.apt_name]["commute"] != [] and not force_refresh:
            print("Already loaded commute info for this apt. Loading from cache....")
            return self.apt_info[self.apt_name]["commute"]

        commute_dict = {}
        for method in MODES:
            r = requests.get(generate_commute_url(self.api_key, lat, lon, method))
            if not self.debug: 
                print("Loading commute info from Google Maps for apt: " + self.apt_name + " and method: " + method)
                j = r.json()
                commute_time_list = j["routes"][0]["legs"][0]["duration"]['text'].split()
                minutes = 0
                if "min" in commute_time_list or "mins" in commute_time_list:
                    minutes += int(commute_time_list[-2])
                if "hour" in commute_time_list or "hours" in commute_time_list:
                    minutes += 60 * int(commute_time_list[0])
                commute_dict[method] = {"duration": minutes}

                if method == "transit":
                    for step in j["routes"][0]["legs"][0]["steps"]:
                        if step.get("transit_details", {}):
                            commute_dict[method]["type"] = j["routes"][0]["legs"][0]["steps"][1]['transit_details']['line']['vehicle']['type']
            else:
                print("[DEBUG]: " + generate_commute_url(self.api_key, lat, lon, method))
        self.apt_info[self.apt_name]["commute"] = commute_dict

        if not self.debug: 
            print("Updating apt info with commute times...")
            assert self.exists_in_cache(CACHE_PATH + CACHE_APTS_FILENAME)
            self.write_to_cache(self.apt_info, CACHE_PATH + CACHE_APTS_FILENAME)
        return commute_dict
    

    def find_grocery_stores(self, stores=["Whole Foods", "Trader Joe's"], force_refresh=False):
        if "stores" in self.apt_info[self.apt_name] and self.apt_info[self.apt_name]["stores"] != [] and not force_refresh:
            print("Already loaded store info for this apt. Loading from cache....")
            return self.apt_info

        store_json_list = []
        for store in stores:
            request_url = generate_find_url(self.api_key, RADIUS, self.apt_info[self.apt_name]["lat"], self.apt_info[self.apt_name]["lon"], store)
            if not self.debug: 
                print("Loading store info from Google Maps for apt: " + self.apt_name + " and store: " + store)
                r = requests.get(request_url)
                resp = r.json()
                try:
                    assert resp['status'] == 'OK'
                except:
                    print("Something went wrong when searching URL: ", request_url)
                    return
                for candidate in resp['candidates']:
                    coords_store = (candidate['geometry']['location']['lat'],candidate['geometry']['location']['lng'])
                    coords_apt = (float(self.apt_info[self.apt_name]['lat']), float(self.apt_info[self.apt_name]['lon']))
                    store_dict = {'name': candidate['name'], 'distance': round(geopy.distance.distance(coords_apt, coords_store).miles, 3), 'candidate': candidate}
                    store_json_list.append(store_dict)
            else:
                print("[DEBUG]: " + request_url)

        self.apt_info[self.apt_name]["stores"] = store_json_list
        if not self.debug: 
            print("Updating apt info with stores...")
            assert self.exists_in_cache(CACHE_PATH + CACHE_APTS_FILENAME)
            self.write_to_cache(self.apt_info, CACHE_PATH + CACHE_APTS_FILENAME)

        return self.apt_info
