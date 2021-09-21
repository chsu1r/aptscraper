from maps import MapsLookup
from streeteasy import StreetEasyAptScraper, StreetEasyScraper

streeteasy_scraper = StreetEasyScraper()
# print(streeteasy_scraper.apts)

for name, apt in streeteasy_scraper.apts.items():
    apt_scraper = StreetEasyAptScraper(name, apt["url"], force_refresh=True)
    maps_lookup = MapsLookup(name, apt_scraper)
    maps_lookup.find_grocery_stores()
    maps_lookup.get_commute_times()
    print("\n")    
