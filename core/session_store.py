import os

# 🔥 Shared session store
INTERVIEW_SESSIONS = {}

# ✅ Use env variables with Linux-safe fallbacks
RECORDING_BASE_PATH = os.getenv("RECORDING_BASE_PATH", "/tmp/recordings")
SEGMENT_PATH = os.path.join(RECORDING_BASE_PATH, "segments")

os.makedirs(RECORDING_BASE_PATH, exist_ok=True)
os.makedirs(SEGMENT_PATH, exist_ok=True)
# import os

# # 🔥 Shared session store
# INTERVIEW_SESSIONS = {}

# # 🔥 Paths
# RECORDING_BASE_PATH = "C:/Users/saipa/OneDrive/Desktop/Recordings"
# SEGMENT_PATH = os.path.join(RECORDING_BASE_PATH, "segments")

# os.makedirs(RECORDING_BASE_PATH, exist_ok=True)
# os.makedirs(SEGMENT_PATH, exist_ok=True)