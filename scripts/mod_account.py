import requests
import yaml

id = ""
type = "mod"  # or unmod

url = f"http://127.0.0.1:39000/api/accounts/{id}/{type}/"

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

headers = {config["server"]["auth-header"]: config["server"]["auth"]}

resp = requests.patch(url, headers=headers)
print(resp.status_code, resp.content)
