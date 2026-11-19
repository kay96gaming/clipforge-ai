"""Transcript -> ranked, non-overlapping clip candidates. Local heuristics, no cloud.

Clips start at a sentence start and end at a sentence end. If fewer suitable non-overlapping
segments exist than requested, fewer clips are returned (never padded or duplicated).
"""
import re
from dataclasses import dataclass, field

END_PUNCT = (".", "?", "!", "…", "。", "؟", "۔")
HOOK_WORDS = {"secret", "mistake", "never", "always", "nobody", "everyone", "truth", "why", "how", "stop", "biggest",
              "worst", "best", "actually", "surprising", "shocking", "problem", "lesson", "learned", "wrong", "myth"}
EMOTION_WORDS = {"love", "hate", "afraid", "scared", "angry", "amazing", "incredible", "crazy", "insane", "terrible",
                 "unbelievable", "wow", "laugh", "cry", "hurt", "proud", "regret", "dream"}
EDU_WORDS = {"because", "means", "example", "step", "first", "second", "third", "reason", "rule", "key", "tip",
             "framework", "strategy", "learn", "understand"}
STORY_WORDS = ("when i", "one day", "i remember", "years ago", "story", "back then", "i was")
FILLER_START = ("and ", "but ", "so ", "because ", "which ", "or ")


@dataclass
class Sentence:
    start: float
    end: float
    text: str


@dataclass
class Clip:
    start: float
    end: float
    text: str
    score: float
    reason: str
    title: str
    hook: str
    hashtags: list = field(default_factory=list)

    @property
    def duration(self):
        return self.end - self.start

    def as_dict(self):
        return {"start": self.start, "end": self.end, "duration": self.duration, "text": self.text,
                "score": self.score, "reason": self.reason, "title": self.title, "hook": self.hook,
                "hashtags": self.hashtags}


def sentences_from_words(words, max_gap=1.0):
    out, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > max_gap:
            out.append(cur); cur = []
        cur.append(w)
        if w["word"].endswith(END_PUNCT):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [Sentence(c[0]["start"], c[-1]["end"], " ".join(x["word"] for x in c)) for c in out]


def first_sentence(text: str) -> str:
    m = re.match(r".*?[.?!…]", text.strip())
    return m.group(0) if m else text[:120]


def score_text(text: str, duration: float):
    t = text.lower()
    toks = set(re.findall(r"[\w']+", t))
    first = first_sentence(text)
    s, why = 30.0, []
    if "?" in first:
        s += 10; why.append("opens with a question")
    h = len(toks & HOOK_WORDS)
    if h:
        s += min(18, h * 6); why.append("strong hook words")
    if re.search(r"\d", first):
        s += 5; why.append("specific numbers")
    e = len(toks & EMOTION_WORDS)
    if e or text.count("!"):
        s += min(14, e * 5 + text.count("!") * 2); why.append("emotional language")
    ed = len(toks & EDU_WORDS)
    if ed:
        s += min(12, ed * 3); why.append("educational explanation")
    if any(p in t for p in STORY_WORDS):
        s += 8; why.append("storytelling")
    if text.count("?") >= 2:
        s += 4; why.append("Q&A exchange")
    wps = len(text.split()) / max(duration, 1)
    if wps < 1.2:
        s -= 12; why.append("slow pacing (penalty)")
    elif 2.0 <= wps <= 3.6:
        s += 6
    if t.startswith(FILLER_START):
        s -= 8
    return max(0.0, min(100.0, s)), why or ["balanced standalone segment"]


def make_title(text: str, n=9) -> str:
    w = first_sentence(text).strip(" .!…").split()
    t = " ".join(w[:n]) + ("…" if len(w) > n else "")
    return t[:1].upper() + t[1:]


def make_hashtags(text: str, k=4):
    stop = set("the a an and or but to of in on for with that this it is are was were be you i we they he she at as by from "
               "have has had not so if then than just like really very about what which who when how why can will would "
               "there their these those because people think going".split())
    freq = {}
    for w in re.findall(r"[A-Za-z]{5,}", text.lower()):
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    return ["#" + w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:k]] + ["#shorts"]


def candidates(sents, min_s, max_s, target):
    out = []
    for i in range(len(sents)):
        best = None
        for j in range(i, len(sents)):
            dur = sents[j].end - sents[i].start
            if dur > max_s:
                break
            if dur < min_s:
                continue
            if best is None or abs(dur - target) < abs(best[2] - target):
                best = (i, j, dur)
        if best:
            i, j, dur = best
            text = " ".join(x.text for x in sents[i:j + 1])
            sc, why = score_text(text, dur)
            out.append(Clip(sents[i].start, sents[j].end, text, sc, "; ".join(why), make_title(text),
                            first_sentence(text).strip(), make_hashtags(text)))
    return out


def select_clips(words, count, target_seconds, min_seconds=None, max_seconds=None, exclude=()):
    min_s = min_seconds or target_seconds * 0.6
    max_s = max_seconds or target_seconds * 1.3
    cands = sorted(candidates(sentences_from_words(words), min_s, max_s, target_seconds), key=lambda c: -c.score)
    chosen, taken = [], list(exclude)
    for c in cands:
        if len(chosen) >= count:
            break
        if all(c.end <= a or c.start >= b for a, b in taken):
            chosen.append(c); taken.append((c.start, c.end))
    return sorted(chosen, key=lambda c: c.start)
