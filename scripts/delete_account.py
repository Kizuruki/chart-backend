import requests
import yaml

id = ""

url = "https://sono_api.untitledcharts.com/accounts/{id}/"

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

headers = {config["server"]["auth-header"]: config["server"]["auth"]}

requests.delete(url, headers=headers)
