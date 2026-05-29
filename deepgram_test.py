from deepgram_test import DeepgramClient, LiveTranscriptionEvents
import threading
import subprocess
from urllib.parse import urljoin

DEEPGRAM_API_KEY = "fad4a764173a4be90767eaa83f389fbf7b593275"

dg = DeepgramClient(DEEPGRAM_API_KEY)

connection = dg.listen.live.v("1")

def on_message(self, result, **kwargs):
    transcript = result.channel.alternatives[0].transcript
    if transcript:
        print("🎤", transcript)

connection.on(LiveTranscriptionEvents.Transcript, on_message)

connection.start({
    "model": "nova-2",
    "language": "en-US",
    "encoding": "linear16",
    "sample_rate": 16000
})

# ffmpeg stream
ffmpeg = subprocess.Popen([
    "ffmpeg", "-loglevel", "quiet", "-i",
    urljoin("https://playerservices.streamtheworld.com",
            "/api/livestream-redirect/CSPANRADIOAAC.aac"),
    "-f", "s16le", "-ar", "16000", "-ac", "1", "-"
], stdout=subprocess.PIPE)

def stream():
    while True:
        data = ffmpeg.stdout.read(4096)
        if not data:
            break
        connection.send(data)

threading.Thread(target=stream).start()