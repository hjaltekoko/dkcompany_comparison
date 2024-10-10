import streamlit as st
import pandas as pd
import time
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import math
from datetime import datetime
import re
import pytz

def create_file_name(store_name):
    # Get current date and time
    
    local_timezone = pytz.timezone('Europe/Copenhagen')

    now = datetime.now(local_timezone)

    # Convert to string suitable for a file name
    current_time_str = now.strftime("%Y%m%d_%H%M%S")

    return store_name + current_time_str + "_data.xlsx"

def fetch_page_number_magasin(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    element = soup.find('js-productlisting')
    #print(element)
    result_count = int(element['data-resultcount'])
    pages = math.ceil(result_count/36)
    return pages

def fetch_page_number_boozt(start_url):
    # Fetch the webpage
    page = requests.get(start_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    try:
        page_number_container = soup.find('div',class_="palette-dropdown")
        page_number = page_number_container.find('span',class_="palette-button__label typography typography--body typography--body2 typography--ellipsis typography--color-inherit typography--weight-regular").get_text()
        page_number = page_number.strip().replace("Side 1/","")
        page_number = int(page_number)
        return page_number
    except AttributeError:
        return 1

# Function to scrape products from a single Boozt URL
def fetch_price_boozt(url,max_pages):
    # List to hold the processed product data

    processed_data = []
    # Loop through pages
    for page_number in range(1, max_pages + 1):
        time.sleep(7)

        paginated_url = f"{url}?grid=large&page={page_number}"
        print(paginated_url)
        # Fetch the webpage
        page = requests.get(paginated_url)
        soup = BeautifulSoup(page.content, 'html.parser')

        # Find all product elements on the current page
        products = soup.find_all(
            'div', class_="palette-product-card-description__content palette-product-card-description__content--vertical palette-product-card-description__content--large")
        print(len(products))
        # If no products are found, break out of the loop (assumes last page)
        #if not products:
        #    break

        # Loop through each product and extract details
        for product in products:
            product_name_container = product.find('span', class_="palette-product-card-description__title-row palette-product-card-description__title-row--has-favorite-button typography typography--body2 typography--ellipsis typography--color-light typography--weight-regular")
            if product_name_container:
                product_name = product_name_container.get_text().strip()

                product_brand_container = product.find('span', class_="palette-product-card-description__title-row palette-product-card-description__title-row--has-favorite-button typography typography--body1 typography--ellipsis typography--color-strong typography--weight-regular")
                if product_brand_container:
                    product_brand = product_brand_container.get_text().strip()

                    product_price_container = product.find('div', class_="palette-product-card-price palette-product-card-price--large")
                    if product_price_container:
                        product_price = product_price_container.get_text().split("kr")

                        # Clean up the price list using regex to extract only numbers
                        product_price = [re.sub(r'\D', '', price) for price in product_price if price.strip()]  # Remove non-digit characters

                        if len(product_price) > 1:
                            sale_price = int(product_price[0])
                            original_price = int(product_price[1])
                        else:
                            sale_price = "not on sale"
                            original_price = int(product_price[0]) if product_price else "N/A"

                        # Append the data to the list
                        processed_data.append([product_name, product_brand, original_price, sale_price])

    # Create a DataFrame from the data
    df = pd.DataFrame(processed_data, columns=["Product Name", "Product Brand", "Original Price", "Sale Price"])
    return df

def fetch_price_magasin(url,pages):
    product_data = []
    for i in range(1,pages+1):
    #for i in range(1,101):
        if i == 1:
            page_url = url
        else:
            page_url = url + f"?page={i}" 
        print(page_url)

        page = requests.get(page_url)
        soup = BeautifulSoup(page.content, 'html.parser')
        # Find all product elements
        products = soup.find_all('div', class_="product-tile__inner")
        for product in products:
            try:
                product_brand = product.find('div',class_="product-tile__name").get_text().strip()

                product_name = product.find('div',class_="product-tile__description").get_text().strip()

                # Find all elements with class="price"
                price_element = product.find(class_="price")
                
                if price_element:
                    # Find all elements inside the current price element that have the content attribute
                    content_elements = price_element.find_all(attrs={"content": True})
                    prices = [element['content'] for element in content_elements]

                    # Check the number of prices and assign appropriately
                    if len(prices) >= 2:
                        # If there are two or more prices, first price is sale price, last price is original price
                        sale_price = int(round(float(prices[0])))
                        original_price = int(round(float(prices[-1])))
                    elif len(prices) == 1:
                        # Only one price means it's the original price and no sale
                        sale_price = "not on sale"
                        original_price = int(round(float(prices[0])))
                    else:
                        # Handle case with no price found, if necessary
                        sale_price = "no price found"
                        original_price = "no price found"
                    
                    # Append to the price data list
                    product_data.append({
                        "Product Name": product_name,
                        "Product Brand": product_brand,
                        "Original Price": original_price,
                        "Sale Price": sale_price
                    })
            except AttributeError:
                break
    df = pd.DataFrame(product_data)
    return df

def scrape_multiple_urls(urls_to_scrape, store_name):
    combined_df = pd.DataFrame(columns=["Product Name", "Product Brand", "Original Price", "Sale Price"])
    
    total_urls = len(urls_to_scrape)
    progress_bar = st.progress(0)  # Initialize progress bar
    status_text = st.empty()  # Placeholder for status updates

    for index, url in enumerate(urls_to_scrape, start=1):
        # Update the status and progress bar
        status_text.write(f"Processing {index} of {total_urls} URLs...")
        progress_bar.progress(index / total_urls)

        # Get the DataFrame from each URL and concatenate it with the existing data
        if store_name == "Magasin":
            pages = fetch_page_number_magasin(url)
            df = fetch_price_magasin(url, pages)
        else:
            pages = fetch_page_number_boozt(url)
            df = fetch_price_boozt(url, pages)
        
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    # Clear the progress bar and status text after completion
    status_text.write("Scraping completed!")
    progress_bar.empty()

    return combined_df

# Streamlit app starts here
st.title("Product Data Scraper")

# Define the lists of URLs for Magasin and Boozt
magasin_urls = [
    "https://www.magasin.dk/maerker/saint-tropez/",
    "https://www.magasin.dk/maerker/gestuz/",
    "https://www.magasin.dk/maerker/inwear/",
    "https://www.magasin.dk/herre/matinique/",
    "https://www.magasin.dk/maerker/fransa/",
    "https://www.magasin.dk/maerker/ichi/",
    "https://www.magasin.dk/maerker/karen-by-simonsen/",
    "https://www.magasin.dk/maerker/solid/",
    "https://www.magasin.dk/maerker/soaked-in-luxury/",
    "https://www.magasin.dk/maerker/casual-friday/",
    "https://www.magasin.dk/maerker/pulz-jeans/",
]

boozt_urls = [
    "https://www.boozt.com/dk/da/saint-tropez",
    "https://www.boozt.com/dk/da/gestuz",
    "https://www.boozt.com/dk/da/inwear",
    "https://www.boozt.com/dk/da/matinique",
    "https://www.boozt.com/dk/da/fransa",
    "https://www.boozt.com/dk/da/ichi",
    "https://www.boozt.com/dk/da/karen-by-simonsen/kvinder",
    "https://www.boozt.com/dk/da/solid/maend",
    "https://www.boozt.com/dk/da/soaked-in-luxury/kvinder",
    "https://www.boozt.com/dk/da/casual-friday/maend",
    "https://www.boozt.com/dk/da/pulz-jeans/women",
]

# Choose the store
store = st.selectbox("Select the Store", ["Magasin", "Boozt"])

if store == "Magasin":
    urls = magasin_urls
else:
    urls = boozt_urls

# Button to trigger the scraping
if st.button("Scrape Data and Download Excel"):
    with st.spinner("Scraping data..."):
        df = scrape_multiple_urls(urls, store)
        st.write(df)  # Display the DataFrame on the page
        
        # Convert the dataframe to an Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        # Download button for the Excel file
        st.download_button(
            label="Download Excel",
            data=output,
            file_name=create_file_name(store),
            mime="application/vnd.ms-excel"
        )