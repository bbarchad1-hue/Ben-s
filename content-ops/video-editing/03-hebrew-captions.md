# כתוביות בעברית: תמלול, SRT, רילס, QA

עודכן: 29.9.2026

## ההחלטות

1. **מנוע תמלול:** `ivrit-ai/whisper-large-v3-turbo-ct2` דרך faster-whisper, מקומי (או RunPod serverless). הכי מדויק בעברית מבין המודלים הפתוחים: 6.2% שגיאה לעומת 8.5% ל-Whisper turbo המקורי (Interspeech 2025). מדידה עצמאית על רילס: 95.3% דיוק מילים. מתמודד טוב עם שמות כלים באנגלית בתוך עברית. **חובה `language="he"`**, זיהוי השפה של המודל נפגע באימון.
2. **חלופת SaaS:** ElevenLabs Scribe v2, 0.22 דולר לשעת אודיו, עם זמני מילים. Deepgram ו-AssemblyAI הוסיפו עברית ב-2026, בלי מדידות עצמאיות עדיין.
3. **סרטונים ארוכים ווובינרים:** SRT עם עוגני RTL, הגהה ב-Subtitle Edit, העלאה ליוטיוב כקובץ. יוטיוב מציג RTL נכון.
4. **רילס עם הדגשת מילה:** לא Submagic, לא Captions.ai (RTL שבור), לא Veed (אין RTL), ולא אפקט `\k` של libass (באג פתוח). כן: HTML/CSS לתמונות שקופות ואז ffmpeg overlay (הדגם של hebrew-reel-maker), או ASS עם אירוע Dialogue נפרד לכל מילה מודגשת.
5. **לא לגעת:** Descript (אין עברית). Premiere Speech to Text (אין עברית). Final Cut Transcribe (אנגלית בלבד). Resolve auto-captions (אין עברית).
6. **תוכנות עריכה, אם צריך:** Premiere עם תוסף ישראלי (Kaps, Subin, Subli, RoboCaps, SubAI, SmartCaptions) ו-Text Engine "South Asian and Middle Eastern" בהגדרות ה-Caption track. Resolve Studio עם hebsub-resolve (חינמי).

## פונטים

פונט אחד שמכיל גם עברית וגם לטינית, כדי ש-"ChatGPT" לא ייפול ל-fallback במשקל אחר. כולם Google Fonts, OFL:

| פונט | הערה |
|---|---|
| **Heebo** | ברירת המחדל. Roboto בלטינית, עודד עזר בעברית. כל המשקלים |
| **Secular One** | כותרות ומילה מודגשת. משקל יחיד |
| Assistant | קריא, x-height גדול |
| Rubik | מעוגל, לרילס "כבדים" |
| Noto Sans Hebrew | ניטרלי, variable |

## 1. תמלול

```bash
pip install faster-whisper python-bidi pysubs2
```

```python
# transcribe.py
from faster_whisper import WhisperModel
import json, sys

model = WhisperModel("ivrit-ai/whisper-large-v3-turbo-ct2",
                     device="cuda", compute_type="float16")   # CPU: device="cpu", compute_type="int8"
segments, info = model.transcribe(
    sys.argv[1],
    language="he",
    beam_size=5,
    word_timestamps=True,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=300, threshold=0.4),
    condition_on_previous_text=False,
    initial_prompt="ChatGPT, Claude, Gemini, Copilot, Base44, Make, Zapier, n8n, Monday, NotebookLM",
)
out = [{"start": s.start, "end": s.end, "text": s.text.strip(),
        "words": [{"w": w.word, "s": w.start, "e": w.end} for w in (s.words or [])]}
       for s in segments]
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
```

- `initial_prompt` הוא מילון שמות הכלים. לעדכן כשנכנס כלי חדש.
- VAD מוסיף ריפוד של 400ms לפני כל מבע. כרטיס ראשון עלול להתחיל לפני הדיבור. לבדוק.
- Apple Silicon: `device="cpu", compute_type="int8"`, כ-5x מזמן אמת. RunPod A4000: כ-95 שניות לשעת אודיו, פחות מסנט.
- "דעה שנייה": להריץ גם Whisper turbo המקורי ולהגיה רק מילים שבהן שני המודלים לא מסכימים. מילה בהסכמה שגויה ב-1.5% מהמקרים, מילה במחלוקת ב-48.6%.

## 2. SRT עם עוגני RTL

הטכניקה של hebsub-resolve: RLM (U+200F) בתחילת כל שורה ולפני פיסוק סופי, LRI/PDI (U+2066/U+2069) סביב מילים באנגלית.

```python
# make_srt.py
import json, re, sys
RLM, LRI, PDI = "‏", "⁦", "⁩"
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9.+#'-]*")
TRAIL = re.compile(r"([.,!?;:…]+)$")

def rtl_fix(line):
    line = LATIN.sub(lambda m: f"{LRI}{m.group(0)}{PDI}", line)
    line = TRAIL.sub(lambda m: RLM + m.group(1), line)
    return RLM + line

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s%1)*1000):03}"

def chunk(words, max_chars=42, max_dur=6.0):
    cur, out = [], []
    for w in words:
        cand = " ".join(x["w"].strip() for x in cur + [w])
        if cur and (len(cand) > max_chars*2 or w["e"] - cur[0]["s"] > max_dur):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out

def two_lines(text, max_chars=42):
    if len(text) <= max_chars: return [text]
    ws = text.split(); best = None
    for i in range(1, len(ws)):
        a, b = " ".join(ws[:i]), " ".join(ws[i:])
        if len(a) <= max_chars and len(b) <= max_chars:
            if best is None or abs(len(a)-len(b)) < abs(len(best[0])-len(best[1])): best = (a, b)
    return list(best) if best else [text]

segs = json.load(open(sys.argv[1]))
words = [w for s in segs for w in s["words"]]
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for i, c in enumerate(chunk(words), 1):
        text = " ".join(w["w"].strip() for w in c)
        lines = [rtl_fix(l) for l in two_lines(text)]
        f.write(f"{i}\n{ts(c[0]['s'])} --> {ts(c[-1]['e'])}\n" + "\n".join(lines) + "\n\n")
```

- UTF-8, זמנים עולים בלי חפיפות, עד 42 תווים לשורה, 2 שורות.
- ל-Premiere: Caption track > Track Settings > Text Engine > South Asian and Middle Eastern.
- ל-Resolve: Resolve זורק את שקט הפתיחה בייבוא SRT. להוסיף "timing card" ב-00:00:00,000 ולמחוק אחרי הצמדה.
- לא להריץ `bidi.get_display()` על הטקסט לפני libass. libass מריץ FriBidi בעצמו, והתוצאה היפוך כפול.
- להימנע מ-`drawtext` של ffmpeg לעברית. אין בו bidi מלא.

## 3. צריבה רגילה (16:9) עם libass

```bash
ffmpeg -y -i input.mp4 \
  -vf "subtitles=subs.srt:fontsdir=./fonts:shaping=complex:force_style='FontName=Heebo,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0.5,Alignment=2,MarginV=40,Encoding=-1'" \
  -c:v libx264 -crf 18 -preset medium -c:a copy -movflags +faststart output.mp4
```

- `Encoding=-1` מחזיר זיהוי כיוון אוטומטי לפסקה. בלי זה פיסוק סופי בורח לצד ימין.
- `shaping=complex` דורש HarfBuzz. חובה לעברית.
- צבעים בפורמט `&HAABBGGRR`.

## 4. רילס 9:16 עם הדגשת מילה, ASS בלי `\k`

```python
# make_ass.py: אירוע Dialogue לכל מילה. כל השורה לבנה, המילה הפעילה צהובה
import json, sys
RLM, LRI, PDI = "‏", "⁦", "⁩"
segs = json.load(open(sys.argv[1]))
def t(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02}:{s:05.2f}"
def isolate(w): return f"{LRI}{w}{PDI}" if w[:1].isascii() and w[:1].isalpha() else w
hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Reel,Secular One,96,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,0,2,60,60,560,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [hdr]
for s in segs:
    ws = [w for w in s["words"] if w["w"].strip()]
    for i in range(0, len(ws), 4):
        page = ws[i:i+4]
        for j, w in enumerate(page):
            txt = " ".join(("{\\c&H00FFFF&}" if k == j else "{\\c&HFFFFFF&}") + isolate(x["w"].strip())
                           for k, x in enumerate(page))
            end = page[j+1]["s"] if j+1 < len(page) else w["e"]
            lines.append(f"Dialogue: 0,{t(w['s'])},{t(end)},Reel,,0,0,0,,{RLM}{txt}\n")
open(sys.argv[2], "w", encoding="utf-8").write("".join(lines))
```

```bash
ffmpeg -y -i reel_src.mp4 -vf "ass=reel.ass:fontsdir=./fonts:shaping=complex" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -movflags +faststart reel_out.mp4
```

- `MarginV=560` מציב את הכתוביות בתפר בין המסך לדובר, מחוץ ל-UI של טיקטוק.
- 3–5 מילים לעמוד. בלי פיסוק חוץ מסימן שאלה. לא למחוק גרש וגרשיים בתוך מילים (חב"ד, נתב"ג).
- חלופה עם מלבן רקע מודגש: HTML/CSS ב-Playwright או Remotion (`createTikTokStyleCaptions`), `direction: rtl` על המכולה, `<span dir="ltr">` למילים באנגלית, ייצוא PNG שקופים ו-`overlay` ב-ffmpeg. הדפדפן עושה bidi נכון בלי מאמץ. הדגם: hebrew-reel-maker.
- זמני מילים מדויקים יותר: WhisperX עם מודל היישור `imvladikon/wav2vec2-xls-r-300m-hebrew`, או Scribe.

## 5. וובינרים

אותו צינור, בתוספת diarization: `ivrit` package ב-RunPod עם `core_engine="stable-whisper", diarize=True`, או pyannote 3.1 של ivrit.ai מקומית. "— " בתחילת שורה בהחלפת דובר. לא Google Chirp 3 (אין diarization לעברית).

## 6. עלות

| מסלול | לשעת אודיו |
|---|---|
| מקומי (CPU או GPU) | 0 |
| RunPod serverless | כסנט |
| ElevenLabs Scribe v2 | 0.22 דולר |
| Deepgram / AssemblyAI | 0.15–0.27 דולר |

עומס שבועי: 4–6 שעות אודיו. התמלול עולה סנטים בכל מסלול. הזמן הוא בהגהה, ואותה מצמצמים ל"מילים במחלוקת".

## 7. צ'קליסט QA

1. אורך שורה 32–42 תווים, עד 2 שורות, העליונה קצרה יותר או שווה.
2. פיסוק סופי בצד שמאל ויזואלית. אם קפץ ימינה, חסר RLM.
3. מילים באנגלית באותיות בסדר נכון ולא גוררות פיסוק. איות עקבי לפי מילון הכלים.
4. מספרים: "10 פקודות" לא התהפך ל-"פקודות 10". אחוזים ומטבע צמודים למספר.
5. גרש וגרשיים בתוך מילים נשארים.
6. אין ניקוד ואין תווים חריגים מהמודל.
7. אין כרטיס שמתחיל לפני הדיבור. כרטיסים סמוכים נוגעים, בלי פערים של 1–200ms. משך כרטיס 1–6 שניות.
8. אין שורות חוזרות או "תודה רבה" בשקט (הזיות).
9. UTF-8, זמנים עולים, בלי חפיפות. ביוטיוב לבדוק בנגן אחרי העלאה.
10. פונט אחד שמכסה עברית ולטינית, ו-`fontsdir` מצביע אליו.
