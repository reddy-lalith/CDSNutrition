import re
import sqlite3
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Function to extract the date from the URL
def extract_date_from_url(url):
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    date = query_params.get('date', [None])[0]
    return date

# Function to check if the dining hall is closed for the day
def is_dining_hall_closed(driver):
    try:
        # Check if the page shows the message about no scheduled hours
        closed_message = driver.find_element(
            By.XPATH,
            '//strong[contains(text(),"Top of Lenoir")]/parent::p'
        ).text
        if "has no scheduled hours" in closed_message:
            return True
    except:
        # If the message isn't found, assume the dining hall is open
        return False

def create_table_and_index():
    conn = sqlite3.connect('dining_data.db')
    c = conn.cursor()

    # Create the food_data table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            food_name TEXT,
            menu_station TEXT,
            time_of_day TEXT,
            ingredients TEXT,
            allergens TEXT,
            bio TEXT,
            amount_per_serving TEXT,
            calories TEXT,
            total_fat TEXT,
            saturated_fat TEXT,
            trans_fat TEXT,
            cholesterol TEXT,
            sodium TEXT,
            total_carbohydrate TEXT,
            dietary_fiber TEXT,
            sugars TEXT,
            added_sugar TEXT,
            protein TEXT,
            calcium TEXT,
            iron TEXT,
            potassium TEXT,
            vitamin_d TEXT
        )
    ''')

    # Create a UNIQUE INDEX to prevent duplicates
    c.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_food
        ON food_data (date, food_name, menu_station, time_of_day)
    ''')

    conn.commit()
    conn.close()

def insert_into_database(date, food_name, menu_station, time_of_day,
                         ingredients, allergens, bio, nutrition_facts):
    try:
        conn = sqlite3.connect('dining_data.db')
        c = conn.cursor()

        # Normalize data before insertion
        date = date.strip()
        food_name = food_name.strip().lower()
        menu_station = menu_station.strip().lower()
        time_of_day = time_of_day.strip().lower()
        ingredients = ingredients.strip()
        allergens = allergens.strip()
        bio = bio.strip()

        # Prepare the nutrition facts to insert into the database
        # Default to N/A if any fact is missing
        amount_per_serving = nutrition_facts.get('Amount Per Serving', 'N/A')
        calories = nutrition_facts.get('Calories', 'N/A')
        total_fat = nutrition_facts.get('Total Fat', 'N/A')
        saturated_fat = nutrition_facts.get('Saturated Fat', 'N/A')
        trans_fat = nutrition_facts.get('Trans Fat', 'N/A')
        cholesterol = nutrition_facts.get('Cholesterol', 'N/A')
        sodium = nutrition_facts.get('Sodium', 'N/A')
        total_carbohydrate = nutrition_facts.get('Total Carbohydrate', 'N/A')
        dietary_fiber = nutrition_facts.get('Dietary Fiber', 'N/A')
        sugars = nutrition_facts.get('Sugars', 'N/A')
        added_sugar = nutrition_facts.get('Added Sugar', 'N/A')
        protein = nutrition_facts.get('Protein', 'N/A')
        calcium = nutrition_facts.get('Calcium', 'N/A')
        iron = nutrition_facts.get('Iron', 'N/A')
        potassium = nutrition_facts.get('Potassium', 'N/A')
        vitamin_d = nutrition_facts.get('Vitamin D', 'N/A')

        # Convert all values to strings
        values = (
            str(date), str(food_name), str(menu_station), str(time_of_day),
            str(ingredients), str(allergens), str(bio),
            str(amount_per_serving), str(calories), str(total_fat),
            str(saturated_fat), str(trans_fat), str(cholesterol),
            str(sodium), str(total_carbohydrate), str(dietary_fiber),
            str(sugars), str(added_sugar), str(protein), str(calcium),
            str(iron), str(potassium), str(vitamin_d)
        )

        # Insert the food data into the database using INSERT OR IGNORE
        c.execute('''
            INSERT OR IGNORE INTO food_data (
                date, food_name, menu_station, time_of_day, ingredients,
                allergens, bio, amount_per_serving, calories, total_fat,
                saturated_fat, trans_fat, cholesterol, sodium,
                total_carbohydrate, dietary_fiber, sugars, added_sugar,
                protein, calcium, iron, potassium, vitamin_d
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', values)

        # Check if the insertion was successful
        if c.rowcount == 0:
            print(f"Duplicate entry for '{food_name}' on date '{date}' and time '{time_of_day}'. Skipping insertion.\n")
        else:
            # Commit the changes
            conn.commit()
            print(f"Data for '{food_name}' inserted successfully.\n")

    except Exception as e:
        print(f"Error inserting data into database for '{food_name}': {str(e)}")
    finally:
        conn.close()

def test_click_and_scrape_info(driver, food_name, menu_station, time_of_day, selected_date):
    try:
        food_item = driver.find_element(By.XPATH, f'//a[@tabindex="0" and text()="{food_name}"]')
        driver.execute_script("arguments[0].click();", food_item)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#nutrition-info-header'))
        )

        # Initialize variables
        bio_text = ""
        allergens_text = ""
        ingredients_text = ""
        nutrition_facts = {}

        # Scrape the allergen information
        try:
            allergens_element = driver.find_element(
                By.XPATH,
                '//div[@id="nutrition-slider-stage"]//h6[text()="Allergens"]/following-sibling::p'
            )
            allergens_text = allergens_element.text.strip()
        except:
            allergens_text = "N/A"

        # Scrape the ingredients information
        try:
            ingredients_element = driver.find_element(
                By.XPATH,
                '//strong[text()="Ingredients:"]/parent::p'
            )
            ingredients_text = ingredients_element.text.strip().replace('Ingredients:', '').strip()
        except:
            ingredients_text = "N/A"

        # Scrape the bio information, ensuring it's not just a repetition of allergens or ingredients
        try:
            bio_element = driver.find_element(
                By.XPATH,
                '//div[@id="nutrition-slider-stage"]//p[not(preceding-sibling::strong)]'
            )
            bio_text = bio_element.text.strip()

            # Check if bio_text is the same as allergens or ingredients, or contains "Ingredients:"
            if (
                bio_text == allergens_text
                or bio_text == ingredients_text
                or "Ingredients:" in bio_text
            ):
                bio_text = "N/A"
        except:
            bio_text = "N/A"

        # Scrape the nutritional facts
        try:
            nutrition_rows = driver.find_elements(By.XPATH, '//table[@class="nutrition-facts-table"]//tr')
            for row in nutrition_rows:
                try:
                    # Extracting the nutrient name and value separately
                    key_element = row.find_element(By.TAG_NAME, 'th').text.strip()

                    # Generalized regex to capture numbers with or without units
                    match = re.match(r"(.+?)\s+(\d+\.?\d*\s*\w*)$", key_element)

                    if match:
                        key = match.group(1).strip()  # Nutrient name
                        value = match.group(2).strip()  # Value (e.g., 250)
                    else:
                        key = key_element
                        value = ""

                    # If the value is not found or empty, try to get it from the next column
                    if not value:
                        try:
                            value = row.find_element(By.CLASS_NAME, 'nutrition-amount').text.strip()
                        except:
                            value = "N/A"

                    # Save the nutrient name and value in the dictionary
                    nutrition_facts[key] = value
                except Exception as e:
                    print(f"Error scraping row: {e}")
                    continue
        except Exception as e:
            print(f"Error scraping nutrition facts: {e}")

        # Print the scraped data, including the selected date
        print(f"Date: {selected_date}")
        print(f"Food Name: {food_name}")
        print(f"Menu Station: {menu_station}")
        print(f"Time of Day: {time_of_day}")
        print(f"Ingredients: {ingredients_text}")
        print(f"Allergens: {allergens_text}")
        print(f"Bio: {bio_text}")

        # Insert the data into the SQLite database
        insert_into_database(
            selected_date, food_name, menu_station, time_of_day,
            ingredients_text, allergens_text, bio_text, nutrition_facts
        )

        print("-" * 40)  # Divider for readability

        # Close the sidebar
        close_button = driver.find_element(By.CSS_SELECTOR, '.c-modal__close')
        close_button.click()

    except Exception as e:
        print(f"Error processing {food_name}: {str(e)}")

# Set up the WebDriver
driver = webdriver.Safari()

# Create the table and index (this will not drop existing data)
create_table_and_index()

# List of URLs to scrape
urls = [
    'https://dining.unc.edu/locations/top-of-lenoir/?date=2024-09-16'
]

# Loop through each URL and scrape the menu
for url in urls:
    # Extract the date from the URL
    date = extract_date_from_url(url)
    if not date:
        print(f"No date found in URL: {url}. Skipping.")
        continue

    print(f"Processing date: {date}")

    try:
        driver.get(url)

        # Check if the dining hall is closed for the day
        if is_dining_hall_closed(driver):
            print(f"Dining hall closed for {date}. Skipping to next day.")
            continue

        # Find all time-of-day tabs
        time_of_day_tabs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.c-tabs-nav__link-inner'))
        )

        MAX_RETRIES = 3

        # Iterate through each time-of-day tab
        for tab in time_of_day_tabs:
            # Get the time-of-day label (e.g., "Lite Lunch (3pm-5pm)")
            time_of_day_label = tab.text.strip()

            retries = 0
            while retries < MAX_RETRIES:
                try:
                    # Scroll the tab into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", tab)

                    # Click the tab using JavaScript to ensure the click is registered
                    driver.execute_script("arguments[0].click();", tab)

                    # Add a brief delay to ensure the content loads
                    time.sleep(2)

                    # Wait for the content of the active tab to load completely
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.c-tab.is-active'))
                    )

                    break  # Break out of the retry loop if successful
                except:
                    retries += 1
                    if retries == MAX_RETRIES:
                        print(f"Failed to click tab: {time_of_day_label} after {MAX_RETRIES} attempts")

            # Now find the content within the active tab
            active_tab_content = driver.find_element(By.CSS_SELECTOR, '.c-tab.is-active')

            # Find all menu stations within the active tab content
            menu_station_elements = active_tab_content.find_elements(By.CSS_SELECTOR, '.menu-station')

            # Iterate over each menu station element within the active tab content
            for station_element in menu_station_elements:
                # Get the station name
                station_name = station_element.find_element(By.CSS_SELECTOR, '.toggle-menu-station-data').text.strip()

                # Find all food items under this station
                food_items = station_element.find_elements(By.CSS_SELECTOR, 'a.show-nutrition')

                if food_items:
                    for food in food_items:
                        food_name = food.text.strip()

                        # Scrape information for each food item
                        test_click_and_scrape_info(driver, food_name, station_name, time_of_day_label, date)
                else:
                    print("  No food items listed.")

                print()  # Add a blank line between stations for readability

    except Exception as e:
        print(f"An error occurred while processing date {date}: {e}")
        continue

# Close the browser once scraping is done
driver.quit()
