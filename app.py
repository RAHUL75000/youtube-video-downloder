from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp, os, uuid, threading

app = Flask(__name__)

# Store progress info
progress_data = {}

def progress_hook(d):
    video_id = d['info_dict'].get('id', 'unknown')
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%')
        progress_data[video_id] = percent
    elif d['status'] == 'finished':
        progress_data[video_id] = "100%"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()
    video_url = data.get("video_url")

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
        return jsonify({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "id": info.get("id"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/process_url", methods=["POST"])
def process_url():
    data = request.get_json()
    video_url = data.get("video_url")
    fmt = data.get("format", "best")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        save_path = "videos"
        os.makedirs(save_path, exist_ok=True)

        filename = str(uuid.uuid4())
        filepath = os.path.join(save_path, filename + ".%(ext)s")

        # Choose format
        if fmt == "mp3":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": filepath,
                "progress_hooks": [progress_hook],
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        elif fmt == "720p":
            ydl_opts = {
                "format": "bestvideo[height<=720]+bestaudio/best",
                "outtmpl": filepath,
                "progress_hooks": [progress_hook],
            }
        elif fmt == "1080p":
            ydl_opts = {
                "format": "bestvideo[height<=1080]+bestaudio/best",
                "outtmpl": filepath,
                "progress_hooks": [progress_hook],
            }
        else:  # best
            ydl_opts = {
                "format": "best",
                "outtmpl": filepath,
                "progress_hooks": [progress_hook],
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            ext = info.get("ext", "mp4")
            final_file = os.path.join(save_path, filename + "." + ext)

        return send_file(final_file, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/progress/<video_id>")
def get_progress(video_id):
    return jsonify({"progress": progress_data.get(video_id, "0.0%")})

if __name__ == "__main__":
    app.run(debug=True, port=5500)
