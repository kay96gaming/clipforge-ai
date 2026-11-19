"""Smart reframing: face-position analysis (OpenCV Haar cascade) + ffmpeg filter graph construction."""
import statistics

ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def parse_aspect(spec: str):
    if spec in ASPECTS:
        return ASPECTS[spec]
    if "x" in spec.lower():  # custom WxH
        w, h = spec.lower().split("x")
        return int(w) // 2 * 2, int(h) // 2 * 2
    a, b = spec.split(":")  # custom ratio -> 1080 short side
    a, b = float(a), float(b)
    return (1080, int(1080 * b / a) // 2 * 2) if a <= b else (int(1080 * a / b) // 2 * 2, 1080)


def face_center_x(path, start, end, samples=10):
    """Median normalised (0..1) x-centre of the largest face over sampled frames. 0.5 if none found."""
    try:
        import cv2
    except ImportError:
        return 0.5
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cas.empty():  # cascade data missing in this OpenCV build -> centre crop instead of crashing
        import logging
        logging.getLogger("clipforge").warning("Face cascade not found; using centre crop")
        return 0.5
    cap = cv2.VideoCapture(path)
    xs = []
    try:
        for i in range(samples):
            cap.set(cv2.CAP_PROP_POS_MSEC, (start + (end - start) * (i + 0.5) / samples) * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            sc = 480 / w if w > 480 else 1.0
            small = cv2.cvtColor(cv2.resize(frame, None, fx=sc, fy=sc), cv2.COLOR_BGR2GRAY)
            faces = cas.detectMultiScale(small, 1.2, 5, minSize=(40, 40))
            if len(faces):
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                xs.append((x + fw / 2) / small.shape[1])
    finally:
        cap.release()
    return statistics.median(xs) if xs else 0.5


def build_filter(src_w, src_h, out_w, out_h, mode="crop", center_x=0.5, manual_x=None):
    """Return an ffmpeg -vf/-filter_complex string. mode: crop | blur | fit."""
    if mode == "blur":
        return (f"split[a][b];[a]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},"
                f"boxblur=24:6[bg];[b]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    if mode == "fit":
        return (f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black")
    target = out_w / out_h
    if src_w / src_h > target:  # source wider: crop horizontally, follow face
        cw, ch = int(src_h * target) // 2 * 2, src_h
        cx = manual_x if manual_x is not None else center_x
        x = int(min(max(cx * src_w - cw / 2, 0), src_w - cw))
        return f"crop={cw}:{ch}:{x}:0,scale={out_w}:{out_h}"
    cw, ch = src_w, int(src_w / target) // 2 * 2
    return f"crop={cw}:{ch}:0:{(src_h - ch) // 2},scale={out_w}:{out_h}"
