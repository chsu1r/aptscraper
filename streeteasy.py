import requests
from bs4 import BeautifulSoup
import json
import os
from decouple import config

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/' + config('IP_ADDR') + ' Safari/537.36'}
CACHE_PATH = "cache/"
CACHE_TOP_FILENAME = "cached_apt_results.json"
CACHE_APTS_FILENAME = "cached_apt_info.json"

class StreetEasyScraper(object):
    def __init__(self, price_cap=4950, amenities=["laundry", "doorman", "elevator"], bedrooms=2, neighborhoods="downtown", debug=False, force_refresh=False):
        self.price_cap = price_cap
        self.amenities = amenities
        self.neighborhoods = neighborhoods
        self.bedrooms = bedrooms
        self.debug = debug
        self.force_refresh = force_refresh
        self.apts = {}  # {"name": {"url":__ , "street_address": __, "unit": __}...}

        self.request_url = self.gen_req_url()
        if self.debug:
            print("[DEBUG] REQUEST URL: " + self.request_url)

        self.get_apts()

    def gen_req_url(self):
        url = "https://streeteasy.com/"
        url += str(self.bedrooms) + "-bedroom-apartments-for-rent/"
        url += self.neighborhoods + "/"
        url += "price:-" + str(self.price_cap)
        url += "%7Camenities:" + ",".join(self.amenities)
        return url

    def exists_in_cache(self, path):
        return os.path.isfile(path)

    def load_from_cache(self, path):
        assert self.exists_in_cache(path)
        with open(path) as infile:
            return json.load(infile)

    def write_to_cache(self, data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def get_apts(self):
        if not (self.exists_in_cache(CACHE_PATH + CACHE_TOP_FILENAME) and not self.force_refresh):
            print("Loading from StreetEasy....")
            apt_dict = {}
            if not self.debug:
                r = requests.get(self.request_url, headers=HEADERS)
                soup = BeautifulSoup(r.content, "html.parser")
                apts = soup.find_all("a", class_="listingCard-link")  # first page
                for apt in apts:
                    street_addr, unit = apt.text.split("#")
                    if street_addr[-1] == " ":
                        street_addr = street_addr[:-1]
                    apt_dict[apt.text] = {"url": apt["href"], "full_address": apt.text, "street_address": street_addr, "unit": unit}
                pages = soup.find_all("li", class_="page")
                for i in range(1, len(pages)):
                    print("Parsing page " + str(i+1))
                    r = requests.get(self.request_url + "?page=" + str(i+1), headers=HEADERS)
                    soup = BeautifulSoup(r.content, "html.parser")
                    apts = soup.find_all("a", class_="listingCard-link")  # first page
                    for apt in apts:
                        street_addr, unit = apt.text.split("#")
                        apt_dict[apt.text] = {"url": apt["href"], "full_address": apt.text, "street_address": street_addr, "unit": unit}
                self.write_to_cache(apt_dict, CACHE_PATH + CACHE_TOP_FILENAME)
            else:
                print("[DEBUG] Loading from StreetEasy and writing to file.")
            self.apts = apt_dict
        else:
            if self.debug:
                print("[DEBUG] Loading apts from cache.")
            else:
                print("Loading apartment search from cache....")
                self.apts = self.load_from_cache(CACHE_PATH + CACHE_TOP_FILENAME)
        
        return self.apts
        
class StreetEasyAptScraper(object):
    def __init__(self, name, url, debug=False, force_refresh=False):
        self.request_url = url
        self.name = name
        self.debug = debug
        self.force_refresh = force_refresh
        self.apt_info = {name: {}}  # {"name": {"url":__ , "lat": __, "lon": __, "price": __, "move_in": __}}

        if self.debug:
            print("[DEBUG] APT REQUEST URL: " + url)

        self.load_apt()

    def exists_in_cache(self, path):
        if not os.path.isfile(path): return False
        with open(path) as infile:
            all_apts = json.load(infile)
            return self.name in all_apts.keys()


    def load_from_cache(self, path):
        assert self.exists_in_cache(path)
        with open(path) as infile:
            all_apts = json.load(infile)
            return all_apts[self.name]

    def write_to_cache(self, data, path):
        to_write = data.copy()
        if os.path.isfile(path):
            with open(path) as infile:
                all_apts = json.load(infile)
                all_apts[self.name] = data[self.name]
                to_write = all_apts
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(to_write, f, ensure_ascii=False, indent=4)
            
    
    def load_apt(self):
        if not (self.exists_in_cache(CACHE_PATH + CACHE_APTS_FILENAME) and not self.force_refresh):
            print("Loading " + self.name + " from StreetEasy....")
            apt_dict = {self.name : {}}

            if self.exists_in_cache(CACHE_PATH + CACHE_APTS_FILENAME):
                apt_dict[self.name] = self.load_from_cache(CACHE_PATH + CACHE_APTS_FILENAME)
            if not self.debug:
                r = requests.get(self.request_url, headers=HEADERS)
                soup = BeautifulSoup(r.content, "html.parser")

                # Add lat/long
                latlon = soup.find("meta", attrs={"name":"geo.position"})["content"]
                latlon = latlon.split(";")
                apt_dict[self.name]["lat"] = latlon[0]
                apt_dict[self.name]["lon"] = latlon[1][1:]
                
                # Add move-in date
                h6_list = soup.findAll("h6")
                available_on = [h for h in h6_list if h.text == "Available on"]
                apt_dict[self.name]["move_in"] = " ".join(available_on[0].next.next.next.text.split())

                # Add rent price
                price =  soup.find_all("div", class_="price")
                dollar_amt = ""
                for price_split in price[0].text.split():
                    if price_split[0] == "$":
                        dollar_amt = price_split
                        break
                apt_dict[self.name]["price"] = dollar_amt

                # Add neighborhood name
                paths = soup.find_all("li", class_="Breadcrumb-crumb")
                apt_dict[self.name]["neighborhood"] = paths[-2].text.strip()
                self.write_to_cache(apt_dict, CACHE_PATH + CACHE_APTS_FILENAME)
            else:
                print("[DEBUG] Loading from StreetEasy and writing to file.")
            self.apt_info = apt_dict
        else:
            if self.debug:
                print("[DEBUG] Loading apts from cache.")
            else:
                print("Loading " +self.name + " from cache....")
                self.apt_info = {self.name : self.load_from_cache(CACHE_PATH + CACHE_APTS_FILENAME)}
        
        return self.apt_info
