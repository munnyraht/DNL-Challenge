from fastapi import FastAPI
import psycopg2
import os
import json

app = FastAPI()

host=os.environ.get('DB_HOST')
database=os.environ.get('DB_NAME')
username=os.environ.get('DB_USERNAME')
password=os.environ.get('DB_PASSWORD')
port=os.environ.get('DB_PORT','5432')

# engine = create_engine(f'postgresql://{username}:{password}@{host}:{port}/{database}', echo=False)
conn = psycopg2.connect(host=host, database=database, user=username, password=password, port=port)

cursor = conn.cursor()

@app.get("/parts")
def models(manufacturer,category,model):
    cursor.execute(f"SELECT id FROM manufacturers WHERE manufacturer = '{manufacturer}'")
    row = cursor.fetchall()
    try:
        manufacturer_id = row[0][0]
        cursor.execute(f"SELECT id FROM categories WHERE category = '{category}' and manufacturer_id = '{manufacturer_id}'")
        category_id = cursor.fetchall()[0][0]
        cursor.execute(f"SELECT id FROM models WHERE models = '{model}' and category_id = {category_id}")
        model_id = cursor.fetchall()[0][0]

        cursor.execute(f"SELECT id,part_number,part_category FROM parts WHERE model_id = '{model_id}' ")
        rows = cursor.fetchall()
        if rows:
            result = []
            for row in rows:
                result.append({"id": row[0], "category": row[1]})
            final_result =  {   
                
                "manufacturer": {
                    "id": manufacturer_id,
                    "name": manufacturer
                    },
                "category":{
                    "id": category_id,
                    "name": category
                    },
                "model":{
                    "id":model_id,
                    "name": model
                },
                "parts" : result
                
            }
            return final_result
        else:
            return {'message':'No record Found'}
    except IndexError:
        return {'message':'No record Found'}