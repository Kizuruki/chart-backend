# WARNING: THIS ISN'T IN requirements.txt
import requests, json

url = "http://127.0.0.1:39000/api/charts/5b5fedc93f2d4688a5d100b1eab8a6d7/visibility/"

data = {
    "status": "PUBLIC",
}

response = requests.patch(
    url,
    json=data,
    headers={
        "authorization": "eyJpZCI6ICJlMWJhNDFhNi1hMDQzLTQ5MTktYTQ2Ni05YTZkMWVkZWExMTMiLCAidXNlcl9pZCI6ICIxMTIwNjZiZWI0YjdhNDlkZTNlNGNlNjRlMmQ1YWRiZmJmNWNmZjZkM2RmMTI2YjVkYTg3NDhmNzZhZTZjNzg5IiwgInR5cGUiOiAiZ2FtZSJ9.f06deb0a5181b98bdcd960760d823f5556ff625b0917330b8b28d286ff8d0006"
    },
)

print("Status code:", response.status_code)
try:
    print("Response:", response.json())
except Exception:
    print("Raw response:", response.text)
