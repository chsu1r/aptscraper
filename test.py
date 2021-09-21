from streeteasy import StreetEasyScraper,StreetEasyAptScraper, CACHE_PATH
from maps import generate_find_url, MapsLookup, generate_commute_url

TEST_CACHE_FILENAME = "test.json"
TEST_APTS_FILENAME = "test_apts.json"
test_scraper = StreetEasyScraper(debug=True, force_refresh=False)

assert test_scraper.request_url == "https://streeteasy.com/2-bedroom-apartments-for-rent/downtown/price:-4950%7Camenities:laundry,doorman,elevator"
assert test_scraper.exists_in_cache(CACHE_PATH + TEST_CACHE_FILENAME)
assert test_scraper.load_from_cache(CACHE_PATH + TEST_CACHE_FILENAME) == {"test": {
        "a": 1,
        "b": 2
    }
}

assert not test_scraper.exists_in_cache(CACHE_PATH + "not_Test.json")

assert test_scraper.apts == {}

test_scraper = StreetEasyAptScraper("test name", "test_url", debug=True)
assert test_scraper.exists_in_cache(CACHE_PATH + TEST_APTS_FILENAME)

assert test_scraper.load_from_cache(CACHE_PATH + TEST_APTS_FILENAME) == {"url":"test_url" , "lat": "24", "lon": "12", "price": "$12", "move_in": "Available Now"}
assert test_scraper.apt_info[test_scraper.name] == {}

test_scraper.name = "other name"
assert not test_scraper.exists_in_cache(CACHE_PATH + TEST_APTS_FILENAME)


test_url = generate_find_url("AIza", 2000, "40.72797292", "-73.98678763", "Whole Foods")
assert test_url == "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?locationbias=circle%3A2000%4040.72797292%2C-73.98678763&inputtype=textquery&input=Whole+Foods&fields=formatted_address%2Cname%2Cgeometry&key=AIza"


test_url = generate_commute_url("AIza",  "40.72797292", "-73.98678763", "walking")
test_scraper = StreetEasyAptScraper("test name", "test_url", debug=True)
test_scraper.apt_info[test_scraper.name] = test_scraper.load_from_cache(CACHE_PATH + TEST_APTS_FILENAME)
test_maps_lookup = MapsLookup("test name", test_scraper, debug=True)

assert test_maps_lookup.exists_in_cache(CACHE_PATH + TEST_APTS_FILENAME)
assert test_maps_lookup.load_from_cache(CACHE_PATH + TEST_APTS_FILENAME)== {"url":"test_url" , "lat": "24", "lon": "12", "price": "$12", "move_in": "Available Now"}
assert test_maps_lookup.find_grocery_stores()["test name"]["stores"] == []