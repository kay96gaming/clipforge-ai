import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ai.clip_engine import select_clips, sentences_from_words
from captions import formats
from video import reframe


def fake_words(n_sent=60, wps=2.5, sent_len=12):
    words, t = [], 0.0
    for s in range(n_sent):
        for k in range(sent_len):
            end = ("?" if s % 5 == 0 else ".") if k == sent_len - 1 else ""
            w = ("Why" if k == 0 and s % 5 == 0 else "word") + str(s) + end
            words.append({"start": t, "end": t + 1 / wps - 0.05, "word": w}); t += 1 / wps
    return words


def test_clips_sentence_aligned_no_overlap():
    w = fake_words()
    clips = select_clips(w, 5, 30)
    assert 0 < len(clips) <= 5
    starts = {x["start"] for x in w}
    ends = {x["end"] for x in w if x["word"].endswith((".", "?"))}
    for c in clips:
        assert c.start in starts and c.end in ends
        assert 18 <= c.duration <= 39
    for a, b in zip(clips, clips[1:]):
        assert a.end <= b.start


def test_never_pads_to_hit_target():
    assert len(select_clips(fake_words(n_sent=6), 30, 30)) < 30


def test_caption_formats():
    w = fake_words(2)
    assert "-->" in formats.to_srt(w) and formats.to_vtt(w).startswith("WEBVTT")
    for name in formats.STYLES:
        assert "Dialogue:" in formats.to_ass(w, name, 1080, 1920)


def test_reframe_filters():
    assert reframe.parse_aspect("9:16") == (1080, 1920)
    assert reframe.parse_aspect("1080x1350") == (1080, 1350)
    f = reframe.build_filter(1920, 1080, 1080, 1920, "crop", 0.5)
    assert f.startswith("crop=606:1080:657:0")
    assert "boxblur" in reframe.build_filter(1920, 1080, 1080, 1920, "blur")
