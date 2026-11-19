"""Faster-Whisper transcription with word timestamps. Runs locally (model downloads once on first use)."""
from typing import Callable


def pick_device(pref: str = "auto"):
    if pref == "cpu":
        return "cpu", "int8"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    if pref == "cuda":
        raise RuntimeError("CUDA requested but no usable NVIDIA GPU was found.")
    return "cpu", "int8"


def transcribe(path: str, model_size="small", language="en", device="auto",
               progress: Callable[[float], None] | None = None, cancelled: Callable[[], bool] = lambda: False):
    """Returns words: [{start, end, word}]."""
    from faster_whisper import WhisperModel
    dev, ctype = pick_device(device)
    model = WhisperModel(model_size, device=dev, compute_type=ctype)
    lang = None if language in (None, "auto") else language
    segs, info = model.transcribe(path, language=lang, word_timestamps=True, vad_filter=True)
    words = []
    for s in segs:
        if cancelled():
            raise InterruptedError("Cancelled")
        for w in (s.words or []):
            words.append({"start": float(w.start), "end": float(w.end), "word": w.word.strip()})
        if progress and info.duration:
            progress(min(1.0, s.end / info.duration))
    return words
