import requests
import json
import time
import os
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains

import multiprocessing
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

PATH="C:\Program Files (x86)\chromedriver.exe"

RULES_SEARCH_PAGE = {
      'url':{'tag':'a', 'class':'rfexzly dir dir-ltr','get':'href'},
      'description':{'tag':'span','class':'t6mzqp7 dir dir-ltr'},
      'name':{'tag':'div','class':'t1jojoys dir dir-ltr'},
      'superhost': {'tag': 'div', 'class': 't1mwk1n0 dir dir-ltr'},
      'price per night': {'tag': 'span', 'class': '_tyxjp1'},
      'actual price': {'tag': 'span', 'class': '_1ks8cgb'},
      'beds': {'tag': 'span', 'class': 'dir dir-ltr'},
      'rating':{'tag':'span'}
}

RULES_DETAIL_PAGE = {
    'location': {'tag': 'span', 'class': '_9xiloll'},
    'unit rental details': {'tag': 'div', 'class': '_tqmy57'},
    'number of guests': {'tag': 'li', 'class': 'l7n4lsf dir dir-ltr', 'order': -1},
    'more description': {'tag': 'span', 'class': 'll4r2nl dir dir-ltr'},
   'amenities1': {'tag': 'div', 'class': 'iikjzje i10xc1ab dir dir-ltr', 'order': -1},#order
    'rating':{'tag': 'span', 'class':'_17p6nbba'}

}

def extract_image_urls(soup):
    print("inside image function")
    #parsed_html = BeautifulSoup(soup)
    new_soup=soup.find_all('li',{'class':'_145ocfuw'})
    #print(new_soup)
    list1=[]
    for i in new_soup:
        parsed_html = BeautifulSoup(i)
        for source in parsed_html.body.find_all('source'):
            print('source image',source['srcset'])
            list1.append(source['srcset'])  
    return list1

def extract_listings(page_url, attempts=10):
    """Extracts all listings from a given page"""
    #print("inside listings")
    listings_max = 0
    listings_out = [BeautifulSoup('', features='html.parser')]
    for idx in range(attempts):
        try:
            answer = requests.get(page_url, timeout=5)
            content = answer.content
            soup = BeautifulSoup(content, features='html.parser')
            listings = soup.findAll("div", {"class": "c4mnd7m dir dir-ltr"})
        except:
            # if no response - return a list with an empty soup
            listings = [BeautifulSoup('', features='html.parser')]

        if len(listings) == 20:
            listings_out = listings
            break

        if len(listings) >= listings_max:
            listings_max = len(listings)
            listings_out = listings
    #print("cameout listings")
    return listings_out

def extract_element_data(soup, params):
    """Extracts data from a specified HTML element"""
    #print("inside element data")
    # 1. Find the right tag
    if 'class' in params:
        
        elements_found = soup.find_all(params['tag'], params['class'])
    else:
        elements_found = soup.find_all(params['tag'])
        
    # 2. Extract text from these tags
    if 'get' in params:
        element_texts = [el.get(params['get']) for el in elements_found]
        #print("inside if",element_texts)
    else:
        element_texts = [el.get_text() for el in elements_found]
        #print("inside else",element_texts)
        
    # 3. Select a particular text or concatenate all of them
    tag_order = params.get('order', 0)
    if tag_order == -1:
        output = '**__**'.join(element_texts)
    else:
        output = element_texts[tag_order]
    #print("output",output)
    #print("came out element data")
    return output


def extract_listing_features(soup, rules):
    """Extracts all features from the listing"""
    features_dict = {}
    for feature in rules:
        try:
            features_dict[feature] = extract_element_data(soup, rules[feature])
            #print(feature, features_dict[feature])
        except:
            features_dict[feature] = 'empty'
    #print(features_dict)
    return features_dict

def extract_house_rules_data(soup, params):
    house_rules3 = soup.find_all('div', 'sahkfss dir dir-ltr')
    #print("house_rules3",house_rules3)
    #print("inside amenities")
    House_rules_list = []
    house_dict={}
    for Hrule in house_rules3:
        #print("Hrule",Hrule)
        tags = Hrule.find_all('div')
        for i in tags:
            House_rules_list.append(i.get_text())
        
    house_dict['all_rules'] = House_rules_list
    #print("cameout of amenities")  
    #print("all house rules",House_rules_list)
    return House_rules_list
    
def extract_soup_js(listing_url, waiting_time=[20, 1]):
    """Extracts HTML from JS pages: open, wait, click, wait, extract"""
    #print("inside soup_js function")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--blink-settings=imagesEnabled=false')
    driver = webdriver.Chrome(PATH,options=options)

    # if the URL is not valid - return an empty soup
    try:
        #print("inside timeout")
        driver.get(listing_url)
    except:
        print(f"Wrong URL: {listing_url}")
        return BeautifulSoup('', features='html.parser')
    
    # waiting for an element on the bottom of the page to load ("More places to stay")
    try:
        myElem = WebDriverWait(driver, waiting_time[0]).until(EC.presence_of_element_located((By.CLASS_NAME, 'i1o80ipj dir dir-ltr')))
    except:
        pass

    # click cookie policy
    try:
        driver.find_element_by_xpath("/html/body/div[6]/div/div/div[1]/section/footer/div[2]/button").click()
    except:
        pass
    # alternative click cookie policy
    try:
        element = driver.find_element_by_xpath("//*[@data-testid='main-cookies-banner-container']")
        element.find_element_by_xpath("//button[@data-testid='accept-btn']").click()
    except:
        pass

    # looking for price details
    price_dropdown = 0
    try:
        element = driver.find_element_by_class_name('_gby1jkw')
        price_dropdown = 1
    except:
        pass

    # if the element is present - click on it
    if price_dropdown == 1:
        for i in range(10): # 10 attempts to scroll to the price button
            try:
                actions = ActionChains(driver)
                driver.execute_script("arguments[0].scrollIntoView(true);", element);
                actions.move_to_element_with_offset(element, 5, 5)
                actions.click().perform()
                break
            except:
                pass
        
    # looking for amenities
    driver.execute_script("window.scrollTo(0, 0);")
    try:
        #print("amenities soup")
        driver.find_element_by_class_name('b65jmrv bgpdp7p v7aged4 dir dir-ltr').click()
    except:
        pass # amenities button not found

    time.sleep(waiting_time[1])

    detail_page = driver.page_source

    driver.quit()
    #print("outside soup_js function")

    return BeautifulSoup(detail_page, features='html.parser')


def scrape_detail_page(base_features):
    """Scrapes the detail page and merges the result with basic features"""
    
    detailed_url = 'https://www.airbnb.com' + base_features['url']
    #print("detailed url",detailed_url)
    soup_detail = extract_soup_js(detailed_url)
    #print(soup_detail)
    features_detailed = extract_listing_features(soup_detail, RULES_DETAIL_PAGE)
    features_amenities = extract_amenities_main(detailed_url)
    features_rental_data=extract_rental_data(detailed_url)
    features_host_about=extract_host_about(detailed_url)
    features_image_urls=extract_image_urls(detailed_url)
    #extract_additional_features(detailed_url)
    #features_images = extract_image_urls(soup_detail)
    #features_amenities, features_image_urls, features_rental_data, features_host_about = extract_selenium_features(detailed_url)
    features_detailed['rental_data'] = features_rental_data
    features_detailed['all_amenities'] = features_amenities
    features_detailed['image_urls'] = features_image_urls
    features_detailed['host_about'] = features_host_about
    
    #features_detailed['all_images'] = features_images
    features_all = {**base_features, **features_detailed}
    #print(features_all)
    return features_all


def extract_selenium_features(url):
    """
    return image_urls, all_amenities, rental_data
    """
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(PATH, options=options)
    driver.get(url)
    image_urls = []
    amenities = []
    try:    
        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[1]/div/div/div/div/div[1]/main/div/div[1]/div[1]/div[2]/div/div/div/div/div/div/div/div[2]/button"))).click()
        elements = WebDriverWait(driver, 80).until(EC.visibility_of_all_elements_located((By.XPATH, "//img[contains(@class,'_6tbg2q')]")))
        for el in elements:
            image_urls.append(el.get_attribute('data-original-uri'))
        driver.get(url)
    except Exception as e:
        print("images didnot come:", url)
        driver.get(url)
        
    try:
        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[1]/div/div/div/div/div[1]/main/div/div[1]/div[3]/div/div[1]/div/div[6]/div/div[2]/section/div[4]/button"))).click()
        for el in WebDriverWait(driver, 80).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div._11jhslp"))):
            amenities.append(el.text.strip())
        driver.get(url)
    except Exception as e:
        print("amentities didnot come:", url)
        driver.get(url)
        
    try:
        rental_data = ''
        data = WebDriverWait(driver, 40).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div._cv5qq4")))
        rental_data = data[0].text.strip()
        driver.get(url)
    except Exception as e:
        print("rental data didnot come:", url)
        driver.get(url)
    try:
        data = WebDriverWait(driver, 30).until(EC.visibility_of_all_elements_located((By.XPATH, "//div[contains(@data-plugin-in-point-id,'HOST_PROFILE_DEFAULT')]")))
        host_about = data[0].text.strip()
    except Exception as e:
        print(e)
#         try:
#             if WebDriverWait(driver, 100).until(EC.visibility_of_all_elements_located((By.XPATH, "//div[contains(@data-plugin-in-point-id,'HOST_PROFILE_DEFAULT')]"))):
#                 host_about = "host data is there"
#         except:    
        host_about = "host data is not there"
        
    return amenities, image_urls, rental_data, host_about


def extract_host_about(url):
     #print("inside amenities")
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(PATH)
    driver.get(url)
    host_about=''
    try:
        data = WebDriverWait(driver, 30).until(EC.visibility_of_all_elements_located((By.XPATH, "//div[contains(@data-plugin-in-point-id,'HOST_PROFILE_DEFAULT')]")))
        host_about = data[0].text.strip()
    except Exception as e:
        print(e)  
        host_about = "host data is not there"
    return(host_about)


def extract_rental_data(url):
     #print("inside amenities")
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(PATH)
    driver.get(url)
    rental_data=''
    try:
        data=WebDriverWait(driver, 40).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div._cv5qq4")))
        rental_data=data[0].text.strip()
    except:
        print("rental_data not available")
    return(rental_data)
    
def extract_image_urls(url):
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(PATH)
    driver.get(url)
    image_urls = []
    try:    
        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[1]/div/div/div/div/div[1]/main/div/div[1]/div[1]/div[2]/div/div/div/div/div/div/div/div[2]/button"))).click()
        elements = WebDriverWait(driver, 80).until(EC.visibility_of_all_elements_located((By.XPATH, "//img[contains(@class,'_6tbg2q')]")))
        for el in elements:
            image_urls.append(el.get_attribute('data-original-uri'))
    except Exception as e:
        print("images didnot come:", url)
    return image_urls

def extract_amenities(soup):
    amenities = soup.find_all('div', {'class': '_aujnou'})
    #print("inside amenities")
    amenities_dict = {}
    for amenity in amenities:
        header = amenity.find('div', {'class': '_1crk6cd'}).get_text()
        values = amenity.find_all('div', {'class': '_1dotkqq'})
        values = [v.find(text=True) for v in values]
        
        amenities_dict['amenity_' + header] = values
    #print("cameout of amenities")   
    return json.dumps(amenities_dict)


def extract_amenities_main(url):
    #print("inside amenities")
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(PATH, options=options)
    driver.get(url)
    amenities = []
    try:
        #print("inside try")
        WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[1]/div/div/div/div/div[1]/main/div/div[1]/div[3]/div/div[1]/div/div[6]/div/div[2]/section/div[4]/button"))).click()
        for el in WebDriverWait(driver, 70).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div._11jhslp"))):
            amenities.append(el.text.strip())
    except:
        print(url)
        #amenities.append()
    return(amenities)


def getting_all_features_for_a_house(listing):
    """
    scraping  for each page
    """
    features = extract_listing_features(listing, RULES_SEARCH_PAGE)
    features['sp_url'] = page
    result = scrape_detail_page(features)
    return result   
