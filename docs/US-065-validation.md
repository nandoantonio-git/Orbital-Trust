# US-065 Validation

Python dependency install command:

```bash
python3 -m pip install -r iot/requirements.txt -r requirements-dev.txt
```

Validated runtime:

```text
python3 --version -> Python 3.11.15
mediapipe==0.10.18
opencv-python==4.11.0.86
numpy==1.26.4
fastapi==0.136.3
uvicorn==0.48.0
```

Checks:

```text
from mediapipe.tasks.python import vision -> OK
python3 -m pip check -> No broken requirements found
dependency duplicate check -> OK
MPLCONFIGDIR=/tmp/matplotlib-cache bash scripts/gate.sh iot/demo_video.py -> 155 passed, 1 warning
MPLCONFIGDIR=/tmp/matplotlib-cache bash scripts/gate.sh api/main.py -> 155 passed, 1 warning
npx tsc --noEmit -> OK
```

Environment note:

```text
The Linux validation container needed libgl1 and libglib2.0-0 for opencv-python.
An old local opencv-python-headless==4.13.0.92 package was removed because it was
not declared by the project and conflicted with the NumPy version resolved for
MediaPipe on Python 3.11.
```
