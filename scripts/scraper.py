import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SEARCH_TERMS_DIR = os.path.join(os.path.dirname(__file__), '..', 'search_terms')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
TEMP_DATA_FILE = os.path.join(DATA_DIR, 'temp_scraped_data.json')


def get_user_input():
    print("Welcome to the eBay Coin Price Scraper!")
    print("-" * 40)
    denominations = [f.replace('_terms.json', '') for f in os.listdir(SEARCH_TERMS_DIR) if f.endswith('.json')]
    if not denominations:
        print(f"Error: No search term files found in '{SEARCH_TERMS_DIR}'.")
        return None, None
    print("Available coin denominations:")
    for i, denom in enumerate(denominations, 1):
        print(f"  {i}. {denom}")
    while True:
        try:
            choice = int(input("Please select a denomination by number: "))
            if 1 <= choice <= len(denominations):
                selected_denom = denominations[choice - 1]
                json_path = os.path.join(SEARCH_TERMS_DIR, f"{selected_denom}_terms.json")
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    print("\nSelect the type of scrape you want to perform:")
    print("  1. Full Scale (Scrape all coins in the selected file)")
    print("  2. Individual (Scrape a single coin by its ID)")
    while True:
        scrape_type_choice = input("Please select a scrape type (1 or 2): ")
        if scrape_type_choice in ['1', '2']:
            scrape_type = "full" if scrape_type_choice == '1' else "individual"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    return json_path, scrape_type

def load_coin_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{filepath}'.")
        return None

def scrape_coin_data(coins_to_scrape):
    all_scraped_data = []

    for coin in coins_to_scrape:
        coin_id, coin_name = coin.get('id', 'N/A'), coin.get('name', 'Unknown Coin')
        print(f"\n--- Scraping ID: {coin_id} | Name: {coin_name} ---")

        search_term = coin['search_terms'][0]
        url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&_sacat=0&LH_Complete=1&LH_Sold=1"
        print(f"Connecting to: {url}")

        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        #Window size needs to be left unchanged for consistent pointers for scraper

        print("Setting browser window to 1920x1080 for consistent layout.")
        driver.set_window_size(1920, 1080)
        
        scraped_listings, processed_ids = [], set()
        
        try:
            driver.get(url)
            print("Waiting for page to load...")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.s-item")))
            print("Page loaded. Starting scrape...")
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while len(scraped_listings) < 10:
                listings = driver.find_elements(By.CSS_SELECTOR, 'li.s-item')
                
                for listing in listings:
                    listing_id = listing.get_attribute('id')
                    if not listing_id or listing_id in processed_ids:
                        continue
                    
                    processed_ids.add(listing_id)

                    try:
                        #1. Isolate the main info container for this listing
                        info_container = listing.find_element(By.CSS_SELECTOR, 'div.s-item__info')

                        #2. Find the name, price, and date
                        name = info_container.find_element(By.CSS_SELECTOR, 'div.s-item__title span[role="heading"]').text.strip()
                        price = info_container.find_element(By.CSS_SELECTOR, 'span.s-item__price').text.strip()
                        sale_date = info_container.find_element(By.CSS_SELECTOR, 'div.s-item__caption span.s-item__caption--signal').text.strip().replace('Sold', '').strip()
                        
                        #3. If all data is found, append it
                        scraped_listings.append({
                            "name": name,
                            "price": price,
                            "sale_date": sale_date
                        })
                        
                        if len(scraped_listings) >= 10: break

                    except NoSuchElementException:
                        continue

                print(f"Scraped {len(scraped_listings)} listings so far...")
                if len(scraped_listings) >= 10: break

                print("Scrolling down to load more results...")
                driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(3)

                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached the end of the search results.")
                    break
                last_height = new_height

            print(f"\nFinished scraping for this coin. Total found: {len(scraped_listings)}.")
        except TimeoutException:
            print("The page timed out or no listing items were found to begin with for this search term.")
        except Exception as e:
            print(f"A critical error occurred: {e}")
        finally:
            driver.quit()
            
        all_scraped_data.append({
            "id": coin_id,
            "coin_name": coin_name,
            "scraped_listings": scraped_listings
        })
        time.sleep(2)
        
    return all_scraped_data

def main():
    json_path, scrape_type = get_user_input()
    if not json_path: return
    all_coins = load_coin_data(json_path)
    if not all_coins: return
    
    coins_to_scrape = []
    if scrape_type == "full":
        coins_to_scrape = all_coins
    elif scrape_type == "individual":
        while True:
            try:
                coin_id = int(input("Enter the ID of the coin you wish to scrape: "))
                selected_coin = next((c for c in all_coins if c.get('id') == coin_id), None)
                if selected_coin:
                    coins_to_scrape.append(selected_coin)
                    break
                else:
                    print("Error: No coin found with that ID. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number for the ID.")
    
    if not coins_to_scrape:
        print("No coins selected for scraping. Exiting.")
        return
        
    scraped_data = scrape_coin_data(coins_to_scrape)
    
    if scraped_data:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(TEMP_DATA_FILE, 'w') as f:
                json.dump(scraped_data, f, indent=4)
            print(f"\nScraping complete. Raw data saved to '{TEMP_DATA_FILE}'")
        except IOError as e:
            print(f"\nError: Could not write data to file. {e}")
    else:
        print("\nNo data was scraped.")

if __name__ == "__main__":
    main()