# WARNING: THIS ISN'T IN requirements.txt
import requests, json

url = "http://localhost:39000/api/charts/84adfd40c9504f4ca69347978f870023/edit/"

"""
class ChartEditData(BaseModel):
    author: Optional[str] = None
    rating: Optional[int] = None
    title: Optional[str] = None
    artists: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []

    # files
    includes_background: Optional[bool] = False
    includes_preview: Optional[bool] = False
    delete_background: Optional[bool] = False
    delete_preview: Optional[bool] = False
    includes_audio: Optional[bool] = False
    includes_jacket: Optional[bool] = False
    includes_chart: Optional[bool] = False
"""
chart_data = {
    "rating": 10,
    "title": "Cool Level",
    "artists": "Cool Artist",
    "tags": ["test3", "test4"],
    "includes_background": True,
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
except FileNotFoundError:
    print("Skipping preview_file: not found.")

try:
    files["background_image"] = (
        "background.png",
        open("assets/stage.png", "rb"),
        "image/png",
    )
except FileNotFoundError:
    print("Skipping background_image: not found.")

response = requests.patch(
    url,
    data=form_data,
    files=files,
    headers={
        "authorization": "eyJpZCI6ICI0YTllNzVmMi1jMGM5LTRlYTgtOTYyZC03MWQ5NWUwNzgwMmUiLCAidXNlcl9pZCI6ICIxMTIwNjZiZWI0YjdhNDlkZTNlNGNlNjRlMmQ1YWRiZmJmNWNmZjZkM2RmMTI2YjVkYTg3NDhmNzZhZTZjNzg5IiwgInR5cGUiOiAiZ2FtZSJ9.18dcb8cc1a1ecdb9603688c98e964e72b8e839d021884a3b59f419bda1c3b639"
    },
)

print("Status code:", response.status_code)
try:
    print("Response:", response.json())
except Exception:
    print("Raw response:", response.text)
