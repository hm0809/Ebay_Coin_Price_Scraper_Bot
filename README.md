# This bot will be able to scrape and find the value of essentially every single special edition or normal coin in Australia based on recent Ebay sales.
## I have included every single special edition and normal coin of all denominations with advanced properties, check the search terms folder to view.
### This bot scraper is incredibly useful as it will provide recent prices, not just old coin price lists that may or may not be reliable, its also **free** *smile*


### Note: I have done my best to include the most relevant search terms, but you may have to edit them if they dont procure results on Ebay.
### if you want any other type of coin to be scraped, youll need to make the JSON yourself (although I will eventually add them)

## Instructions For Use (Aus Coin Value Scraper)

## 1. It is required to use Gemini API (to ensure that scraped listings are relevant and cleaned) 
## Set your environment variable for GEMINI_API_KEY using:
python`setx GEMINI_API_KEY "YOUR_API_KEY"`

## 2. Make sure all dependencies are downloaded: python`[your_python] -m pip install -r requirements.txt`

## 3. Run scraper.py (it will take 5-10 minutes if you do a full scrape)

## 4. Run analysis.py (note: this will cost you about a single cent to run with the gemini API, so dont run it recursively I guess (idk why u would))

## 5. Saved information will be in a file called coin_price_analysis.csv and congrats


# This software is intentionally extensible to pretty much any item commonly sold on Ebay! Just edit it to your liking.
## I'm using it for coins cause I have a ton of 50 cent special edition coins that I do not need or want. 


### If you do not have a GEMINI API KEY? Go to [GoogleAPI](https://ai.google.dev/gemini-api/docs/api-key)