from flask import Flask, render_template, request, url_for
import os

from openai import OpenAI
client = OpenAI()

import rockset
from rockset import *
from rockset.models import *

# i'm so pretty, oh so pretty
from pprint import pprint

# doing time capture the easy but wrong way
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()  # This loads the variables from .env

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
# @app.route('/')
def index():
    # print(os.getcwd())
    if request.method == 'POST':
        # Extract data from form fields
        # print("post done")
        inputs = get_inputs()

        search_query_embedding = get_openai_embedding(inputs, client)
        rockset_key = os.environ.get('ROCKSET_API_KEY')
        region = Regions.usw2a1
        records_list = get_rs_results(inputs, region, rockset_key, search_query_embedding)

        folder_path = 'static'
        for record in records_list:
            # Extract the identifier from the URL
            identifier = record["image_url"].split('/')[-1].split('_')[0]
            file_found = None
            for file in os.listdir(folder_path):
                if file.startswith(identifier):
                    file_found = file
                    break
            if file_found:
                # Overwrite the record["image_url"] with the path to the local file
                record["image_url"] = file_found
                # print(f"Matched file: {file_found}")
            else:
                print("No matching file found.")

        # Render index.html with results
        return render_template('index.html', records_list=records_list)

    # print("still get done")
    # If method is GET, just render the form
    return render_template('index.html')

def get_inputs():
    search_query = request.form.get('search_query')
    min_price = request.form.get('min_price')
    max_price = request.form.get('max_price')
    brand = request.form.get('brand')
    # limit = request.form.get('limit')

    return {
        "search_query": search_query, 
        "min_price": min_price, 
        "max_price": max_price, 
        "brand": brand, 
        # "limit": limit
    }

# function for getting openai embedding, returns embedding (array of floats)
def get_openai_embedding(inputs, client):
    # openai.organization = org
    # openai.api_key = api_key

    openai_start = (datetime.now())
    response = client.embeddings.create(
        input=inputs["search_query"], 
        model="text-embedding-ada-002"
        )
    search_query_embedding = response.data[0].embedding 
    openai_end = (datetime.now())
    elapsed_time = openai_end - openai_start

    # print("\nOpenAI Elapsed time: " + str(elapsed_time.total_seconds()))
    # print("Embedding for \"space wars\" looks like " + str(search_query_embedding)[0:100] + "...")

    return search_query_embedding

def get_rs_results(inputs, region, rockset_key, search_query_embedding):
    print("\nRunning Rockset Queries...")
    
    # Create an instance of the Rockset client
    rs = RocksetClient(api_key=rockset_key, host=region)

    rockset_start = (datetime.now())
    # api_response = rs.QueryLambdas.execute_query_lambda_by_tag(
    #     workspace="Demo",
    #     query_lambda="all_imgs",
    #     tag="latest"
    # )

    # print("\nVector Search result:")
    # for record in api_response["results"]:
        
    #     pprint(record["image_ur1"])
        
    # Execute Query Lambda By Version
    rockset_start = (datetime.now())
    api_response = rs.QueryLambdas.execute_query_lambda_by_tag(
        workspace="confluent_webinar",
        query_lambda="find_related_games_vs",
        tag="latest",
        parameters=[
            {
                "name": "embedding",
                "type": "array",
                "value": str(search_query_embedding)
            },
            {
                "name": "min_price",
                "type": "float",
                "value": inputs["min_price"]
            },
            {
                "name": "max_price",
                "type": "float",
                "value": inputs["max_price"]
            },
            {
                "name": "brand",
                "type": "string",
                "value": inputs["brand"]
            }
            # {
            #     "name": "limit",
            #     "type": "int",
            #     "value": inputs["limit"]
            # }
        ]
    )
    rockset_end = (datetime.now())
    elapsed_time = rockset_end - rockset_start
    # print("\nVector Search Elapsed time: " + str(elapsed_time.total_seconds()))

    # print("\nVector Search result:")
    # for record in api_response["results"]:
        # print(f"{record['title']}, {record['image_ur1']}, {record['brand']}, {record['estimated_price']}, {record['description']}")

    records_list = []
    
    for record in api_response["results"]:
        record_data = {
            "title": record['title'],
            "image_url": record['image_ur1'],
            "brand": record['brand'],
            "estimated_price": record['estimated_price'],
            "description": record['description']
        }
        records_list.append(record_data)

    
    # now let's do the full text search approach
    # we'll split the search query text into the first two terms
    # (term1, term2) = inputs["search_query"].split()

    # rockset_start = (datetime.now())
    # api_response = rs.QueryLambdas.execute_query_lambda_by_tag(
    #     workspace="confluent_webinar",
    #     query_lambda="find_related_games_fts",
    #     tag="latest",
    #     parameters=[
    #         {
    #             "name": "term1",
    #             "type": "string",
    #             "value": str(term1)
    #         },
    #         {
    #             "name": "term2",
    #             "type": "string",
    #             "value": str(term2)
    #         },
    #         {
    #             "name": "min_price",
    #             "type": "float",
    #             "value": inputs["min_price"]
    #         },
    #         {
    #             "name": "max_price",
    #             "type": "float",
    #             "value": inputs["max_price"]
    #         },
    #         {
    #             "name": "brand",
    #             "type": "string",
    #             "value": inputs["brand"]
    #         },
    #         {
    #             "name": "limit",
    #             "type": "int",
    #             "value": inputs["limit"]
    #         }
    #     ]
    # )
    # rockset_end = (datetime.now())
    # elapsed_time = rockset_end - rockset_start
    # print("\nFTS Elapsed time: " + str(elapsed_time.total_seconds()))

    # print("\nFTS result:")
    # for record in api_response["results"]:
        # pprint(record["title"])

    return records_list
    

if __name__ == '__main__':
    app.run(debug=False)
