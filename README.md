# Monday Board Creator

סקריפט Python ליצירת בורדים ב-Monday.com מ-Export של Fillout או הגדרה ידנית.

## התקנה

```bash
pip install requests
```

## שימוש

### 1. מ-Export של Fillout

```bash
python monday_board_creator.py \
  --token "your_api_token_here" \
  --name "שם הבורד שלי" \
  --fillout form_export.json
```

### 2. הגדרה ידנית (שאלות בשורת הפקודה)

```bash
python monday_board_creator.py \
  --token "your_api_token_here" \
  --name "שם הבורד שלי" \
  --manual
```

### 3. תצוגה מקדימה (בלי ליצור בפועל)

```bash
python monday_board_creator.py \
  --token "your_api_token_here" \
  --name "שם הבורד" \
  --fillout form_export.json \
  --preview
```

## פרמטרים

| פרמטר | תיאור |
|-------|-------|
| `--token` | Monday.com API Token (חובה) |
| `--name` | שם הבורד החדש (חובה) |
| `--fillout FILE` | נתיב לקובץ JSON של Fillout |
| `--manual` | הגדרת עמודות ידנית |
| `--kind` | `public` / `private` / `share` (ברירת מחדל: public) |
| `--preview` | הצגת תצוגה מקדימה בלי יצירה |

## איך לקבל API Token ממאנדיי

1. היכנס למאנדיי → לחץ על התמונה שלך (פינה שמאל תחתון)
2. **Developers** → **My Access Tokens**
3. לחץ **Show** → העתק את הטוקן

## מיפוי סוגי שדות Fillout → Monday.com

| סוג ב-Fillout | סוג ב-Monday | הערה |
|--------------|-------------|------|
| `MultipleChoice` | **Status** | בחירה **בודדת** |
| `Dropdown` | **Status** | בחירה **בודדת** |
| `YesNo` | **Status** | כן/לא |
| `MultiSelect` | **Dropdown** | בחירה **מרובה** |
| `Checkboxes` | **Dropdown** | בחירה **מרובה** |
| `ShortAnswer` | Text | |
| `LongAnswer` | Long Text | |
| `Email` | Email | |
| `PhoneNumber` | Phone | |
| `NumberInput` | Number | |
| `DatePicker` | Date | |

## פורמט קובץ Fillout

הסקריפט מזהה אוטומטית מספר פורמטים:

```json
{
  "questions": [
    {
      "name": "שם השאלה",
      "type": "MultipleChoice",
      "options": ["אפשרות 1", "אפשרות 2", "אפשרות 3"]
    }
  ]
}
```

## דוגמה לקובץ

ראה `fillout_example.json` — דוגמה מלאה עם כל סוגי השדות.
