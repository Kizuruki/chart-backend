# WARNING: THIS ISN'T IN requirements.txt
import requests, json

url = "http://localhost:39000/api/charts/visibility/"

data = {
    "chart_id": "84adfd40c9504f4ca69347978f870023",
    "status": "PUBLIC",
}

response = requests.patch(
    url,
    json=data,
    headers={
        "authorization": "eyJpZCI6ICJkYzU0MmQ0NS04YmNkLTQ1NmUtOWRmOS00MzVkYjkyOGVmY2QiLCAidXNlcl9pZCI6ICIxMTIwNjZiZWI0YjdhNDlkZTNlNGNlNjRlMmQ1YWRiZmJmNWNmZjZkM2RmMTI2YjVkYTg3NDhmNzZhZTZjNzg5IiwgInR5cGUiOiAiZ2FtZSJ9.60b8f11e5b2bf55827362b16e179c33734cc3d4d2771e235271ffeb8a23a52c6"
    },
)

print("Status code:", response.status_code)
try:
    print("Response:", response.json())
except Exception:
    print("Raw response:", response.text)
