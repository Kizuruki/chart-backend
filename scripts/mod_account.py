import requests
import yaml

id = ""
type = "mod"  # or unmod

url = "https://sono_api.untitledcharts.com/accounts/{id}/{type}/"

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

headers = {config["server"]["auth-header"]: config["server"]["auth"]}

requests.patch(url, headers=headers)
