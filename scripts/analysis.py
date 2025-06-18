import os
import json
import csv
import google.generativeai as genai

#config
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
SEARCH_TERMS_DIR = os.path.join(os.path.dirname(__file__), '..', 'search_terms')
TEMP_DATA_FILE = os.path.join(DATA_DIR, 'temp_scraped_data.json')
FINAL_CSV_FILE = os.path.join(DATA_DIR, 'coin_price_analysis.csv')

try:
    #Make sure you get the API key from your env variable, see README.md for instructions
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found. Please set it before running the script.")
    
    genai.configure(api_key=api_key)
    
    #You can change the model but this is cheap and all you need
    AI_MODEL = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini AI model initialized successfully.")

except Exception as e:
    print(f"Error during AI setup: {e}")
    AI_MODEL = None 


def get_user_input_for_analysis():
    print("\nStarting Data Analysis and Cleaning")
    print("-" * 40)
    denominations = [f.replace('_terms.json', '') for f in os.listdir(SEARCH_TERMS_DIR) if f.endswith('.json')]
    if not denominations:
        print(f"Error: No search term files found in '{SEARCH_TERMS_DIR}'.")
        return None
    print("Which denomination does the scraped data in 'temp_scraped_data.json' belong to?")
    for i, denom in enumerate(denominations, 1):
        print(f"  {i}. {denom}")
    while True:
        try:
            choice = int(input("Please select a denomination by number: "))
            if 1 <= choice <= len(denominations):
                selected_denom = denominations[choice - 1]
                return os.path.join(SEARCH_TERMS_DIR, f"{selected_denom}_terms.json")
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def load_json_data(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found. Please run the scraper first.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'. The file might be empty or corrupt.")
        return None

def clean_data_with_ai(model, reference_coin, scraped_listings):

    print(f"  > Sending {len(scraped_listings)} listings to Gemini for validation...")
    
    prompt = f"""
    You are a numismatic expert specializing in Australian coins. Your task is to analyze a list of recently sold eBay listings for a specific coin and clean the data.

    The target coin is:
    - Name: "{reference_coin['name']}"
    - Year: {reference_coin['year']}

    Please review the following scraped listings. For each listing, determine three things:
    1.  `is_relevant`: Is the listing for the correct target coin? (True/False). Ignore minor variations in the title if the core item is correct. A listing for a different year or a completely different coin is not relevant.
    2.  `cleaned_price`: What is the sale price for a *single* coin? If the listing is for a bulk lot (e.g., "5x coin", "lot of 3"), divide the total price by the quantity to get the single-item price. Extract only the numerical value. If price cannot be determined, return null.
    3.  `original_name`: The original title of the listing.

    Return the data ONLY as a valid JSON array of objects, with no other text, explanations, or markdown formatting.
    Scraped Listings:
    {json.dumps(scraped_listings, indent=2)}
    """
    
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "original_name": {"type": "STRING"},
                    "is_relevant": {"type": "BOOLEAN"},
                    "cleaned_price": {"type": "NUMBER"}
                },
                 "required": ["original_name", "is_relevant", "cleaned_price"]
            }
        }
    )
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"  > An exception occurred during the Gemini API call: {e}")
        return None

def save_to_csv(final_data, output_file):
    if not final_data:
        print("No data to save. CSV file not created.")
        return
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=final_data[0].keys())
            writer.writeheader()
            writer.writerows(final_data)
        print("-" * 40)
        print(f"Analysis complete! Data saved to '{output_file}'")
    except IOError as e:
        print(f"Error saving CSV file: {e}")


def main():
    if not AI_MODEL:
        print("AI model not initialized due to an error. Cannot proceed with analysis.")
        return
        
    reference_file_path = get_user_input_for_analysis()
    if not reference_file_path:
        return

    scraped_data = load_json_data(TEMP_DATA_FILE)
    reference_coins = load_json_data(reference_file_path)
    if not scraped_data or not reference_coins:
        return
        
    final_analysis_results = []

    for coin_data in scraped_data:
        coin_id = coin_data.get('id')
        reference_coin = next((c for c in reference_coins if c.get('id') == coin_id), None)
        
        if not reference_coin:
            print(f"Warning: No reference data found for coin ID {coin_id}. Skipping.")
            continue
            
        print(f"\nProcessing ID: {coin_id} | Name: {reference_coin['name']}")

        if not coin_data['scraped_listings']:
            print("  > No listings were scraped for this coin. Skipping analysis.")
            final_analysis_results.append({
                'ID': coin_id, 'Coin Name': reference_coin['name'], 'Year': reference_coin.get('year', 'N/A'),
                'Average Price': "N/A", 'Lowest Price': "N/A", 'Highest Price': "N/A", 'Valid Listings Count': 0
            })
            continue

        cleaned_listings = clean_data_with_ai(AI_MODEL, reference_coin, coin_data['scraped_listings'])
        
        if not cleaned_listings:
            print("  > Failed to get cleaned data from AI. Skipping analysis for this coin.")
            continue

        valid_prices = [
            listing.get('cleaned_price') for listing in cleaned_listings 
            if listing.get('is_relevant') and isinstance(listing.get('cleaned_price'), (int, float))
        ]

        print(f"  > Found {len(valid_prices)} relevant listings after AI cleaning.")

        if valid_prices:
            average_price = sum(valid_prices) / len(valid_prices)
            final_analysis_results.append({
                'ID': coin_id, 'Coin Name': reference_coin['name'], 'Year': reference_coin.get('year', 'N/A'),
                'Average Price': f"${average_price:.2f}", 'Lowest Price': f"${min(valid_prices):.2f}",
                'Highest Price': f"${max(valid_prices):.2f}", 'Valid Listings Count': len(valid_prices)
            })
        else:
             final_analysis_results.append({
                'ID': coin_id, 'Coin Name': reference_coin['name'], 'Year': reference_coin.get('year', 'N/A'),
                'Average Price': "N/A", 'Lowest Price': "N/A", 'Highest Price': "N/A", 'Valid Listings Count': 0
            })
            
    save_to_csv(final_analysis_results, FINAL_CSV_FILE)

if __name__ == "__main__":
    main()