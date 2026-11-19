"""Caption building: word grouping, SRT/VTT export, styled ASS (karaoke / emphasis) for burn-in."""
import re

STYLES = {
    "educational":  dict(font="Segoe UI", size=64, base="#FFFFFF", hi="#FFD84D", outline="#000000", ow=3, shadow=1, bold=1, upper=0, karaoke=0, bg=0, words=4),
    "hormozi":      dict(font="Impact", size=84, base="#FFFFFF", hi="#00E676", outline="#000000", ow=6, shadow=0, bold=1, upper=1, karaoke=0, bg=0, words=3),
    "mrbeast":      dict(font="Arial Black", size=90, base="#FFFFFF", hi="#FFEB3B", outline="#000000", ow=7, shadow=2, bold=1, upper=1, karaoke=0, bg=0, words=3),
    "tiktok":       dict(font="Arial", size=72, base="#FFFFFF", hi="#FF36B8", outline="#000000", ow=4, shadow=0, bold=1, upper=0, karaoke=1, bg=0, words=4),
    "neon":         dict(font="Segoe UI", size=70, base="#FF36B8", hi="#A020F0", outline="#A020F0", ow=4, shadow=2, bold=1, upper=0, karaoke=0, bg=0, words=4),
    "karaoke":      dict(font="Segoe UI", size=68, base="#FFFFFF", hi="#A020F0", outline="#000000", ow=3, shadow=1, bold=1, upper=0, karaoke=1, bg=0, words=5),
    "minimalist":   dict(font="Segoe UI", size=56, base="#FFFFFF", hi="#FFFFFF", outline="#000000", ow=2, shadow=0, bold=0, upper=0, karaoke=0, bg=0, words=6),
}
HOOKISH = {"never", "always", "secret", "money", "free", "best", "worst", "mistake", "truth", "why", "how", "stop"}


def shift_words(words, t0, t1):
    return [{**w, "start": max(0.0, w["start"] - t0), "end": max(0.0, w["end"] - t0)}
            for w in words if w["end"] > t0 and w["start"] < t1]


def group_words(words, per=4, max_gap=0.7):
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= per or w["start"] - cur[-1]["end"] > max_gap or cur[-1]["word"].endswith((".", "?", "!"))):
            groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def _ts(t, sep=","):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def to_srt(words, per=6):
    out = []
    for i, g in enumerate(group_words(words, per), 1):
        out.append(f"{i}\n{_ts(g[0]['start'])} --> {_ts(g[-1]['end'])}\n{' '.join(w['word'] for w in g)}\n")
    return "\n".join(out)


def to_vtt(words, per=6):
    out = ["WEBVTT\n"]
    for g in group_words(words, per):
        out.append(f"{_ts(g[0]['start'], '.')} --> {_ts(g[-1]['end'], '.')}\n{' '.join(w['word'] for w in g)}\n")
    return "\n".join(out)


def _c(hexcol, alpha=0):
    h = hexcol.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _ass_ts(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def to_ass(words, style_name, width, height, style_override=None):
    st = {**STYLES.get(style_name, STYLES["educational"]), **(style_override or {})}
    scale = height / 1920 if height > width else height / 1080
    size = max(24, int(st["size"] * (scale if height > width else scale * 1.0)))
    prim, sec = (_c(st["hi"]), _c(st["base"])) if st["karaoke"] else (_c(st["base"]), _c(st["hi"]))
    back = _c("#000000", int(255 * (1 - st["bg"] / 100))) if st["bg"] else _c("#000000", 255)
    border_style = 3 if st["bg"] else 1
    marg = int(height * (0.22 if height > width else 0.12))
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n"
            "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
            "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: Default,{st['font']},{size},{prim},{sec},{_c(st['outline'])},{back},{-st['bold']},0,0,0,100,100,0,0,"
            f"{border_style},{max(1, int(st['ow'] * scale * 1.5))},{st['shadow']},2,40,40,{marg},1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    lines = []
    for g in group_words(words, st["words"]):
        parts = []
        for k, w in enumerate(g):
            txt = w["word"].upper() if st["upper"] else w["word"]
            txt = txt.replace("{", "(").replace("}", ")")
            if st["karaoke"]:
                nxt = g[k + 1]["start"] if k + 1 < len(g) else w["end"]
                parts.append(f"{{\\kf{max(1, int(round((nxt - w['start']) * 100)))}}}{txt}")
            else:
                emph = len(re.sub(r"\W", "", txt)) >= 7 or re.sub(r"\W", "", txt).lower() in HOOKISH or re.search(r"\d", txt)
                parts.append(f"{{\\c{_c(st['hi'])}}}{txt}{{\\c{prim}}}" if emph else txt)
        lines.append(f"Dialogue: 0,{_ass_ts(g[0]['start'])},{_ass_ts(g[-1]['end'] + 0.05)},Default,,0,0,0,,{' '.join(parts)}")
    return head + "\n".join(lines) + "\n"
