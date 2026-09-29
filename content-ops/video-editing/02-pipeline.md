# התהליך הקבוע: Claude Code מריץ סקריפטים

עודכן: 29.9.2026

## ההחלטה

**המנוע הוא Claude Code שמריץ ffmpeg, auto-editor ו-Python בתיקיית פרויקט.** קלוד מחליט (JSON), הסקריפטים חותכים בצורה דטרמיניסטית, ותוכנת העריכה משמשת רק לביקורת ולתיקון. לא תוסף בתוך תוכנת עריכה, ולא CapCut.

למה:
- דטרמיניסטי, ניתן לבדיקה, בלי תלות ב-GUI, עובד עם כל שפה.
- Premiere: אין תמלול בעברית, החיבור לקלוד קהילתי ומבוסס ExtendScript שהתמיכה בו מסתיימת. CapCut: פורמט סגור בהנדסה לאחור.
- DaVinci Resolve Studio 21.1 (295 דולר חד-פעמי) הוא שולחן הביקורת: יש בו שרת MCP מובנה לקלוד (File > Setup AI Assistants), ייבוא FCPXML/OTIO, Smart Reframe כגיבוי, Voice Isolation. הגרסה החינמית איבדה את Python scripting ב-21.1.

## הסטאק

| כלי | תפקיד | עלות |
|---|---|---|
| Claude Code (Pro/Max) | מתזמר: מריץ סקריפטים, בוחר קטעים, כותב פרקים ותיאורים, מתקן לפי הערות | במנוי הקיים |
| ffmpeg עם VideoToolbox | חיתוך, stack, זום, loudnorm, צריבת כתוביות | 0 |
| auto-editor | הורדת שתיקות, ייצוא ל-Resolve | 0 |
| ivrit.ai whisper-large-v3-turbo-ct2 (faster-whisper) | תמלול עברי ברמת מילה. ראו 03-hebrew-captions.md | 0 מקומי, או סנטים ב-RunPod |
| OpenTimelineIO + FCPXML | פורמט הביניים של הטיימליין | 0 |
| DaVinci Resolve Studio 21.1 | ביקורת, תיקונים, MCP מובנה | 295 דולר חד-פעמי |
| video-use (fork, browser-use) | שלד מוכן: תמלול, EDL, רינדור, בדיקה עצמית. חוסך שבוע פיתוח | 0 |
| MediaPipe / auto-vertical-reframe | face-tracking, רק כגיבוי להקלטות ישנות | 0 |
| Remotion או HyperFrames (אופציונלי) | כותרות, הוק, lower-thirds בקוד | 0 ליחיד |
| Claude API לבחירה אוטומטית (אופציונלי) | כ-0.30 דולר לסרטון ארוך | לפי שימוש |

## מבנה תיקיות לכל סרטון

```
~/Video/YYYY-MM-DD_topic/
  00_src/       raw: cam.mp4 + screen.mp4 (או raw.mp4), zoom/*.mp4
  01_norm/      cfr.mp4, proxy_1080.mp4, audio16k.wav
  02_asr/       words.json, segments.srt
  03_edit/      keep.json, long.otio, long.fcpxml, timemap.json
  04_llm/       transcript_for_llm.md, selection.json, selection.validated.json
  05_subs/      long.he.srt, reel01.he.ass ...
  06_render/    long_final.mp4, medium01.mp4, reel01.mp4, tt01..tt12.mp4
  07_review/    review.html, contact_sheets/*.png
  08_publish/   chapters.txt, descriptions.md, *.mp4
  CLAUDE.md     כללי הפרויקט: ספים, קואורדינטות layout, פונט, יעד LUFS, כללי עברית
```

## השלבים

`run.py <folder>` מריץ את כל השלבים ועוצר רק בשלב הביקורת.

### 0. קליטה ונרמול

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate,avg_frame_rate -of csv=p=0 00_src/raw.mp4
# אם VFR: המרה ל-CFR + סנכרון אודיו
ffmpeg -i 00_src/raw.mp4 -fps_mode cfr -r 30 -af aresample=async=1000:first_pts=0 \
  -c:v h264_videotoolbox -b:v 16M -c:a aac -b:a 192k 01_norm/cfr.mp4
ffmpeg -i 01_norm/cfr.mp4 -vn -ac 1 -ar 16000 01_norm/audio16k.wav
```

הקלטות מסך וזום הן לעיתים VFR. בלי המרה ל-CFR האודיו נסחף, ובקליפים ארוכים זה מצטבר מהר.

### 1. תמלול

קלט: `audio16k.wav`. פלט: `words.json` עם מילה, התחלה, סוף, confidence. הפירוט והקוד ב-[03-hebrew-captions.md](03-hebrew-captions.md).

### 2. Rough cut לסרטון הארוך

אפשרות א, מהירה, לפי אודיו (שבועות 1–2):

```bash
auto-editor 01_norm/cfr.mp4 --edit audio:-30dB --margin 0.2s,0.3s --export resolve -o 03_edit/long_resolve.xml
auto-editor 01_norm/cfr.mp4 --edit audio:-30dB --margin 0.2s,0.3s -o 06_render/long_rough.mp4
```

ערך ה-dB וה-margin מכוילים על הקלטה אמיתית בשבוע הראשון.

אפשרות ב, לפי תמלול (משבוע 3): `make_keep.py` בונה `keep.json` מפערים בין מילים, חותך גם false starts ומשאיר את ה-take האחרון. כותב `timemap.json` (מיפוי זמן מקור לזמן פלט) ו-`long.otio`.

כללים:
- חיתוך רק בתוך שקט אמיתי: לבדוק RMS של האודיו סביב חותמת הזמן, לא לסמוך על timestamp בלבד. Whisper מדויק לכ-500 אלפיות שנייה.
- padding: 0.15 שנ' לפני, 0.25 אחרי. לכייל.
- fade אודיו של 30 אלפיות שנייה בכל חיתוך.
- בסרטון הארוך לא חותכים נשימות קצרות.

### 3. פרקים וכתוביות לסרטון הארוך

- קלוד בוחר פרקים לפי מזהי משפטים. הסקריפט ממיר לזמן **אחרי החיתוך** לפי `timemap.json`.
- ולידציה לכללי יוטיוב: הפרק הראשון ב-00:00, לפחות 3 פרקים, כל אחד 10 שניות לפחות, כותרת עד 50 תווים. כלל אחד שנשבר ויוטיוב מתעלם מכל הרשימה בשקט.
- SRT מועלה ליוטיוב כקובץ. לא צורבים כתוביות בסרטון הארוך.

### 4. בחירת קטעים על ידי קלוד

העיקרון: קלוד לא מחשב זמנים. התמלול ממוספר לפי משפטים (S0001...), קלוד מחזיר מזהים בלבד, והסקריפט ממפה לזמני מילים.

קלט (`transcript_for_llm.md`):

```
# video: 2026-10-13_long | duration 01:12:40 | speaker: בן
S0001 [00:00:03.2–00:00:07.9] ...
S0002 [00:00:08.1–00:00:14.6] ...
## pauses>1.2s: after S0017 (2.4s), after S0044 (1.9s)
## on-screen: S0120–S0188 screen share
```

פרומפט:

```
You are a senior short-form editor for a Hebrew-language educational creator.
Input: a numbered Hebrew transcript (sentence IDs with source timestamps).
Task:
1. Pick exactly 2 REELS (35–60s) and at least 10 TIKTOK cuts (20–60s).
   Each must be SELF-CONTAINED: no "כמו שאמרתי קודם", no unresolved pronouns
   pointing outside the clip, starts on a hook sentence, ends on a completed
   thought, no mid-sentence start/end. Prefer segments marked "קליפ".
2. Pick 2 MEDIUM cuts (7–15 min) of 1–4 contiguous sections forming a
   standalone lesson; give a Hebrew title.
3. Produce YouTube CHAPTERS (first at S0001, >=3, each >=10s, Hebrew titles <=50 chars).
4. For every clip: 1–3 zoom moments (sentence IDs), a Hebrew hook title (<=7 words),
   layout ("stack" if screen share is referenced, else "speaker").
Rules: the 2 reels never overlap; TikTok cuts may overlap reels only with a different hook.
Prefer: concrete tips, numbers, strong opinions, stories with payoff.
Avoid: logistics, Q&A without the question audible.
Return ONLY JSON matching the schema.
```

סכימת JSON: `video_id`, `chapters[{start_id,title_he}]`, `reels[]`, `tiktoks[]`, `medium_cuts[{id,title_he,sections[{start_id,end_id}]}]`. כל clip: `id, start_id, end_id, hook_he, why, layout (speaker|stack), zoom_ids[], score, context_risk (none|low|high)`.

ולידציה (`validate_clips.py`):
- מיפוי: `start = first_word.start − 0.15`, `end = last_word.end + 0.25`.
- משך 35–60 שנ' לרילס. חריגה = בקשת תיקון לקלוד עם השגיאה.
- אין חפיפה בין שני הרילס. כפילויות בין טיקטוק לרילס מסוננות.
- `context_risk == high` מסומן לביקורת אנושית. קלוד בודק מחדש על טקסט הקטע בלבד: "האם צופה חדש יבין?"

### 5. רינדור הסרטון הארוך

```bash
ffmpeg -f concat -safe 0 -i 03_edit/concat.txt -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:v hevc_videotoolbox -b:v 20M -tag:v hvc1 06_render/long_final.mp4
```

- punch-in מתחלף של 10–15% על כל קטע שני, כדי להסתיר jump cuts.
- לאודנס: -14 עד -16 LUFS.

### 6. רילס וטיקטוק, 1080×1920, layout מוערם

```bash
ffmpeg -ss $IN -to $OUT -i 00_src/screen.mp4 -ss $IN -to $OUT -i 00_src/cam.mp4 -filter_complex \
 "[0:v]crop=ih*9/8:ih:$X_SCREEN:0,scale=1080:960[top]; \
  [1:v]crop=ih*9/8:ih:$X_FACE:0,scale=1080:960[bot]; \
  [top][bot]vstack=inputs=2,ass=05_subs/reel01.he.ass:fontsdir=./fonts:shaping=complex[v]" \
 -map "[v]" -map 1:a -af loudnorm=I=-14:TP=-1.5 -c:v h264_videotoolbox -b:v 10M 06_render/reel01.mp4
```

- מסך למעלה 1080×960, דובר למטה 1080×960. `X_FACE` קבוע כשהמצלמה במרכז.
- זומים ב-`zoom_ids` עם `zoompan` או `scale`+`crop`.
- Safe zone: טקסט לא ב-320px התחתונים ולא ב-120px הימניים (UI של טיקטוק). המקום הטבעי לכתוביות הוא התפר בין המסך לדובר.
- face-tracking (MediaPipe) רק כשההקלטה משולבת ואין קובץ מצלמה נפרד.

### 7. קטעים בינוניים

concat של ה-sections מ-`medium_cuts`, אותו טיפול כמו הארוך: punch-in, fades, loudnorm, SRT ופרקים משלהם, פתיח חדש של 5 שניות.

### 8. וובינרים (clarity pass)

- CFR, ניקוי רעש (`arnndn` או Voice Isolation ב-Studio), `loudnorm`.
- חיתוך: 5 הדקות של "נחכה לכולם", בדיקות סאונד, תקלות שיתוף מסך, שקט בזמן סקרים, Q&A לא רלוונטי.
- פתיח ערוך: 10–15 שניות של רגע השיא, ואז כרטיס של 15–20 שניות (שם, דובר, מה מקבלים).
- Q&A כפרק נפרד, כל שאלה כטקסט על המסך.
- העלאה תוך 48 שעות. 71% מצפיות ה-replay קורות ב-14 הימים הראשונים.
- בנוסף: medium cut של 8–15 דקות עם המהות בלבד. הוא יקבל את רוב הצפיות.
- פרקים לפי שקפים עם PySceneDetect.

### 9. ביקורת

קלוד בונה `review.html`:
- טבלת חיתוכים עם thumbnail לפני ואחרי כל חיתוך.
- קטעים שסומנו: `context_risk`, מילים עם confidence נמוך, חיתוך באמצע מילה.
- נגני פריוויו לכל קטע קצר.

תיקונים בשפה חופשית ("הזז את reel02 שני משפטים קדימה") מתעדכנים ב-JSON ומרונדרים מחדש. לחלופין `long.fcpxml` נפתח ב-Resolve ומתוקן ידנית או דרך ה-MCP.

| תוצר | מה בודקים | יעד זמן |
|---|---|---|
| סרטון ארוך | גלילה ב-review.html, צפייה ב-2x בקטעים שסומנו, אישור פרקים | 15–20 דק' |
| 2 רילס + 10 טיקטוק | צפייה ב-2x ברצף, אישור או דחייה | 15–20 דק' |
| 2 בינוניים | התחלה, סוף, מעברים | 10 דק' כל אחד |
| וובינר | 5 דקות ראשונות, סוף, דגימת אודיו | 10 דק' |

## זמן מכונה (הערכה, סרטון מקור של 60 דק', Apple Silicon)

| שלב | הערכה |
|---|---|
| נרמול CFR | כ-7 דק' |
| תמלול מקומי (turbo) | 4–10 דק' |
| רינדור final ב-4K HEVC | כ-19 דק'. ב-1080p מהיר יותר |
| בחירה בקלוד, רילס, טיקטוק | למדוד בשבוע 1 |

## נקודות כשל

| כשל | פתרון |
|---|---|
| חיתוך באמצע מילה בעברית | חיתוך רק בשקט אמיתי לפי RMS, padding, fade 30ms, סימון מילים עם confidence נמוך |
| הזיות תמלול בשקט | `vad_filter=True`, `condition_on_previous_text=False` |
| jump cuts צורמים | punch-in מתחלף, margin נדיב, לא לחתוך נשימות בארוך |
| סחיפת אודיו | בדיקת VFR, המרה ל-CFR, "Optimize for 3rd party editor" בזום, חישוב זמנים ב-Fraction |
| קטע שלא עומד לבד | `context_risk` + בדיקה חוזרת של קלוד על טקסט הקטע בלבד |
| פרקים לא מופיעים ביוטיוב | ולידציה אוטומטית של שלושת הכללים, זמנים אחרי timemap |
| קבצי 4K גדולים | proxy 1080p לניתוח, final מהמקור עם VideoToolbox |
| כלים שנשברים (ExtendScript, Python ב-Resolve חינמי) | ffmpeg ו-OTIO הם מקור האמת. תוכנת העריכה היא שכבה שאפשר להחליף |

## תוכנית פריסה, 4 שבועות

**שבוע 1, יסודות ומדידה:** התקנת ffmpeg, auto-editor, Python venv, OTIO, faster-whisper, fork של video-use. תיקון ההקלטה ל-OBS עם שני קבצים. כתיבת CLAUDE.md. הרצת שלבים 0–2 על סרטון ישן, כיול dB ו-margin, מדידת זמני מכונה. יעד: rough cut ארוך שקלוד מייצר לבד + SRT.

**שבוע 2, סרטון ארוך מקצה לקצה:** `make_keep.py`, `timemap.json`, פרקים עם ולידציה, punch-in, fades, loudnorm, ייצוא FCPXML ל-Resolve (רכישת Studio כאן), `review.html` גרסה 1. יעד: סרטון ארוך באוויר עם ביקורת של 30 דקות לכל היותר.

**שבוע 3, רילס וטיקטוק:** פרומפט, סכימה, `validate_clips.py`, layout מוערם, זומים, צריבת ASS, בדיקת safe zone, face-tracking כגיבוי. יעד: 2 רילס + 10 טיקטוק מכל סרטון ארוך, ביקורת של 20 דקות.

**שבוע 4, בינוניים, וובינרים, ייצוב:** `medium_cuts`, clarity pass לוובינרים, PySceneDetect לפרקים, `run.py` אחד לכל השלבים. כשלים חוזרים הופכים לכללים ב-CLAUDE.md. יעד: קלוד עורך הכל, 20 דקות ביקורת לסרטון ארוך, כ-2 שעות אנושיות בשבוע.
