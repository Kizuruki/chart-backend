import requests
import yaml

id = ""
action = "ban"  # ban or unban
delete = 1  # 1 for True, 0 for False, only applies on Ban

url = f"http://127.0.0.1:39000/api/accounts/{id}/moderation/{action}/"

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

headers = {config["server"]["auth-header"]: config["server"]["auth"]}

resp = requests.patch(url, headers=headers, params={"delete": delete})
print(resp.status_code, resp.content)
