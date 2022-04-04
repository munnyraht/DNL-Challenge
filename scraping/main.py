from email.mime import base
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import os


base_url ='https://www.urparts.com/'
url = 'index.cfm/page/catalogue'
# print(str(datetime.now()))


host=os.environ.get('DB_HOST')
database=os.environ.get('DB_NAME')
username=os.environ.get('DB_USERNAME')
password=os.environ.get('DB_PASSWORD')
port= int(os.environ.get('DB_PORT',5432))

#create connection to db
conn = psycopg2.connect(host=host, database=database, user=username, password=password, port=port)

cursor = conn.cursor()

# create tables
cursor.execute('''
        CREATE TABLE IF NOT EXISTS manufacturers(
        
            id SERIAL PRIMARY KEY,
            manufacturer VARCHAR ( 100 ) UNIQUE NOT NULL,
            decription TEXT,
            created_at TIMESTAMP NOT NULL 
        );

        CREATE TABLE IF NOT EXISTS categories(
        id SERIAL PRIMARY KEY,
        manufacturer_id INT,
        category CHAR(100),
        created_at TIMESTAMP NOT NULL,
        CONSTRAINT fk_manufacturer
        FOREIGN KEY(manufacturer_id) 
        REFERENCES manufacturers(id)
    );

        CREATE TABLE IF NOT EXISTS models(
        id SERIAL PRIMARY KEY,
        category_id INT,
        models CHAR(100),
        created_at TIMESTAMP NOT NULL,
        CONSTRAINT fk_category
        FOREIGN KEY(category_id) 
        REFERENCES categories(id)

    ); 

        CREATE TABLE  IF NOT EXISTS parts(
        id SERIAL PRIMARY KEY,
        part_number CHAR(100),
        part_category character varying,
        model_id INT,
        created_at TIMESTAMP NOT NULL,
        CONSTRAINT fk_model
        FOREIGN KEY(model_id) 
        REFERENCES models(id)

    ); 
    ''')

conn.commit()

def get_contentWrapWide_links(url):
    '''

        Returns a dictionary of names and link of the url source with div tag and id "contentWrapWide"
            INPUT (str): a valid http url 
            OUTPUT(dict): field name ad key and link and value
    
    '''
    link_dict= {}
    content = requests.get(url).content
    soup = BeautifulSoup(content, 'html.parser')  
    links = soup.find('div', attrs={"id":"contentWrapWide"}).findAll('a')
    for link in links:
        link_dict[link.text.strip()] = link.get('href')
    return link_dict

def get_allcatalogue_links(url,catalogue):
    '''
        Returns a dictionary of names and link of the url source with div tag and class "catalogue" variable
        INPUT (str): a valid http url 
              (str): the calogue name to be fetched
        OUTPUT(dict): field name ad key and link and value
    
    '''
    if catalogue == 'models':
        div_class = 'allmodels'
    elif catalogue == 'section':
        div_class = 'modelSections'
    else:
        div_class = 'allparts'
    link_dict= {}
    content = requests.get(url).content
    soup = BeautifulSoup(content, 'html.parser')  
    links = soup.find('div', attrs={"class":div_class}).findAll('a')
    for link in links:
        link_dict[link.text.strip()] = link.get('href')
    return link_dict


def insert_part_values(parts):
    '''
        Return process parts dictionary and insert the part number and categories into the db
        INPUT (dict): a dictionary of part name and links 
              
        OUTPUT None
    
    '''
    parts_values = []
    for part,link in parts.items():
        try:
            number = part.split(' - ')[0]
            category = part.split(' - ')[1]
        except IndexError:
            category = None
        parts_values.append((model_id,number,category,str(datetime.now())))
    args = ','.join(cursor.mogrify("(%s,%s,%s,%s)", i).decode('utf-8')
                for i in parts_values)
    cursor.execute("INSERT INTO parts (model_id,part_number,part_category,created_at) VALUES " + (args) + ";")

# get manucturers links
makes = get_contentWrapWide_links(base_url+url)


values = [(k,str(datetime.now())) for k,v in makes.items()]


args = ','.join(cursor.mogrify("(%s,%s)", i).decode('utf-8')
            for i in values)

cursor.execute("INSERT INTO manufacturers (manufacturer , created_at) VALUES " + (args) + " ON CONFLICT (manufacturer) DO NOTHING;")
conn.commit()

for make,link in makes.items():

    # get manufacturer category names and links
    categories = get_contentWrapWide_links(base_url+link)
    cursor.execute(f"SELECT id FROM manufacturers WHERE manufacturer = '{make}'")
    row = cursor.fetchall()
    make_id = row[0][0]
    category_values = [(make_id,category,str(datetime.now())) for category,cat_link in categories.items()]
    args = ','.join(cursor.mogrify("(%s,%s,%s)", i).decode('utf-8')
            for i in category_values)
    cursor.execute("INSERT INTO categories (manufacturer_id, category,created_at) VALUES " + (args) + ";")

    for category,cat_link in categories.items():
        # get category model names and links
        models = get_allcatalogue_links(base_url+cat_link,'models')
        if not models:
            break
        cursor.execute(f"SELECT id FROM categories WHERE category = '{category}' and manufacturer_id = '{make_id}'")
        row = cursor.fetchall()
        category_id = row[0][0]
        model_values = [(category_id,model,str(datetime.now())) for model,model_link in models.items()]
        args = ','.join(cursor.mogrify("(%s,%s,%s)", i).decode('utf-8')
                for i in model_values)
        cursor.execute("INSERT INTO models (category_id,models,created_at) VALUES " + (args) + ";")
        
        for model,model_link in models.items():
            cursor.execute(f"SELECT id FROM models WHERE models = '{model}' and category_id = '{category_id}'")
            row = cursor.fetchall()
            model_id = row[0][0]
            try:
                parts = get_allcatalogue_links(base_url+model_link, 'parts')
                if parts:
                    insert_part_values(parts)
                
            except AttributeError:
                try:
                    sections = get_allcatalogue_links(base_url+model_link, 'section')
                    for section,section_link in sections.items():
                        parts = get_allcatalogue_links(base_url+section_link, 'parts')
                        if parts:
                            insert_part_values(parts)
                except Exception as e:
                    pass
                        
            except Exception as e:
                pass
conn.commit()