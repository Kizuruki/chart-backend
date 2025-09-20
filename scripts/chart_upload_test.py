# WARNING: THIS ISN'T IN requirements.txt
import requests, json

url = "http://127.0.0.1:39000/api/charts/upload/"

chart_data = {
    "rating": 10,
    "title": "Cool Level",
    "artists": "Cool Artist",
    "tags": ["test", "test2"],
    "includes_background": False,
    "includes_preview": False,
}
with open("assets/level.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    if data.get("description"):
        chart_data["description"] = data["description"]
    chart_data["title"] = data["title"]
    chart_data["artists"] = data["artists"]
    chart_data["rating"] = data["rating"]
    chart_data["author"] = data["author"]

form_data = {"data": json.dumps(chart_data)}

files = {
    "jacket_image": ("jacket.png", open("assets/jacket.png", "rb"), "image/png"),
    "chart_file": ("chart.sus", open("assets/level.data", "rb"), "application/gzip"),
    "audio_file": ("audio.mp3", open("assets/music.mp3", "rb"), "audio/mpeg"),
}

# Optional files
try:
    files["preview_file"] = (
        "preview.mp3",
        open("assets/music_pre.mp3", "rb"),
        "audio/mpeg",
    )
    chart_data["includes_preview"] = True
except FileNotFoundError:
    print("Skipping preview_file: not found.")

try:
    files["background_image"] = (
        "background.png",
        open("assets/stage.png", "rb"),
        "image/png",
    )
    chart_data["includes_background"] = True
except FileNotFoundError:
    print("Skipping background_image: not found.")

response = requests.post(
    url,
    data=form_data,
    files=files,
    headers={
        "authorization": "eyJpZCI6ICJlMWJhNDFhNi1hMDQzLTQ5MTktYTQ2Ni05YTZkMWVkZWExMTMiLCAidXNlcl9pZCI6ICIxMTIwNjZiZWI0YjdhNDlkZTNlNGNlNjRlMmQ1YWRiZmJmNWNmZjZkM2RmMTI2YjVkYTg3NDhmNzZhZTZjNzg5IiwgInR5cGUiOiAiZ2FtZSJ9.f06deb0a5181b98bdcd960760d823f5556ff625b0917330b8b28d286ff8d0006"
    },
)

print("Status code:", response.status_code)
try:
    print("Response:", response.json())
except Exception:
    print("Raw response:", response.text)
