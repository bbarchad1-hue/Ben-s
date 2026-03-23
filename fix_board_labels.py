#!/usr/bin/env python3
"""
מגדיר לייבלים לעמודות קיימות בבורד מאנדיי
===========================================
משתמש ב-change_column_metadata (לא change_column_value)
— אין צורך בפריט זמני.

הרצה:
    python fix_board_labels.py
"""

import json
import time
import sys

try:
    import requests
except ImportError:
    print("חסר חבילה. הרץ: pip install requests")
    sys.exit(1)


API_URL  = "https://api.monday.com/v2"
BOARD_ID = "5093548430"

# לכל עמודה: כותרת, סוג (status / dropdown), אפשרויות
# status   → { "0": "opt0", "1": "opt1", ... }   (index 5 שמור ל-Done)
# dropdown → { "labels": ["opt1", "opt2", ...] }
COLUMNS_WITH_OPTIONS = [
    {
        "title": "עורך האינטייק",
        "type":  "dropdown",
        "options": [
            "אילת", "רן", "עמית", "סבסטיאן", "יערה", "שי",
            "חן שטרס", "סיון", "מג'ד", "רוני קטבי", "טארק",
            "איתן שרבר", "מיכל", "נטלי", "נט", "אלינה", "שיר",
        ],
    },
    {
        "title": "זיקה לנכס",
        "type":  "status",
        "options": ["שכירות", "אחר", "בעלות", "דיור ציבורי", "בעלים שמתגורר בנכס"],
    },
    {
        "title": "סטטוס תעסוקתי",
        "type":  "status",
        "options": ["עובד", "עצמאי", "מובטל", "פנסיונר", "לא עובד", "אחר", "נכות ביטוח לאומי"],
    },
    {
        "title": "מספר חדרי שינה בדירה המקורית",
        "type":  "dropdown",
        "options": ["1", "2", "2.5", "3", "4", "5", "6", "7", "8", "9", "-"],
    },
    {
        "title": "סיווג הבניין",
        "type":  "status",
        "options": ["ירוק", "כתום", "אדום", "לא ידוע"],
    },
    {
        "title": "סטטוס שיפוץ",
        "type":  "status",
        "options": ["לא התחיל", "בתהליך", "הושלם", "שכירות (לא רלוונטי)", "הבניין נהרס"],
    },
    {
        "title": "גורם מבצע של השיפוץ",
        "type":  "status",
        "options": ["עמיגור", "פרטי", "טרם נקבע", "אין צורך בשיפוץ", "שכירות (לא רלוונטי)", "בניין נהרס"],
    },
    {
        "title": "תחום שיפוץ נדרש",
        "type":  "dropdown",
        "options": ["מסגרת וחלונות", "קירות, בנייה, ריצוף טייח וצבע", "אינסטלציה", "חשמל", "נגרות", "אין צורך"],
    },
    {
        "title": "האם צריך לברר מה מצב הריהוט בנכס?",
        "type":  "status",
        "options": ["כן, צריך ללכת לברר", "אין צורך, היו כבר בנכס", "אין צורך, הבניין הרוס לחלוטין"],
    },
    {
        "title": "איזה ציוד נדרש לכניסה לדירה החלופית?",
        "type":  "status",
        "options": ["ציוד חלקי", "פריטים בודדים", "ציוד מלא"],
    },
    {
        "title": "האם הוגשה תביעה לקרן הפיצויים (מס רכוש)?",
        "type":  "status",
        "options": ["כן", "לא"],
    },
    {
        "title": "מקום מגורים נוכחי",
        "type":  "status",
        "options": ['בי"ח', "במלון", "השכיר דירה", "אצל בני משפחה", "אחר"],
    },
    {
        "title": "מה מתוך האפשרויות מקובל מבחינת מיגון בדירה החדשה?",
        "type":  "dropdown",
        "options": [
            "ממד חובה", "ממק (מרחב מוגן קומתי)", "מקלט בבניין",
            "מקלט בקרבת הבניין", "חדר מדרגות", "היעדר מיגון",
            "עדיפות לממד", "אין צורך מיוחד",
        ],
    },
    {"title": "בעלות על דירה נוספת", "type": "status", "options": ["כן", "לא"]},
    {"title": "קצבת זקנה",            "type": "status", "options": ["כן", "לא"]},
    {"title": "השלמת הכנסה",          "type": "status", "options": ["כן", "לא"]},
    {"title": "קצבת השלמה לנכות",     "type": "status", "options": ["כן", "לא"]},
    {"title": 'מקבל סיוע בשכ"ד',     "type": "status", "options": ["כן", "לא"]},
]


# ─── GraphQL queries ──────────────────────────────────────────────────────────

GET_COLS_QUERY = """
query ($boardId: [ID!]) {
    boards(ids: $boardId) {
        columns { id title type }
    }
}
"""

# change_column_metadata: מגדיר הגדרות עמודה (לא ערך על פריט)
# $val: String! — מחרוזת JSON
SET_LABELS_MUTATION = """
mutation ($board: ID!, $col: String!, $val: String!) {
    change_column_metadata(
        board_id: $board,
        column_id: $col,
        column_property: labels,
        value: $val
    ) { id }
}
"""


# ─── API helper ───────────────────────────────────────────────────────────────

def monday(token: str, query: str, variables: dict = None) -> dict:
    headers = {
        "Authorization": token,
        "Content-Type":  "application/json",
        "API-Version":   "2023-10",
    }
    body = {"query": query}
    if variables:
        body["variables"] = variables

    resp = requests.post(API_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def build_status_value(options: list[str]) -> str:
    """
    Status: { "0": "opt0", "1": "opt1", ... }
    index 5 שמור ל-Done המובנה — מדלגים.
    מחזיר מחרוזת JSON.
    """
    labels: dict[str, str] = {}
    idx = 0
    for opt in options:
        if idx == 5:
            idx += 1   # דלג על Done
        labels[str(idx)] = opt
        idx += 1
    return json.dumps(labels, ensure_ascii=False)


def build_dropdown_value(options: list[str]) -> str:
    """
    Dropdown: { "labels": ["opt1", "opt2", ...] }
    מחזיר מחרוזת JSON.
    """
    return json.dumps({"labels": options}, ensure_ascii=False)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    from getpass import getpass

    print("=" * 55)
    print("  תיקון לייבלים בבורד קיים במאנדיי")
    print(f"  Board ID: {BOARD_ID}")
    print("=" * 55)

    token = getpass("\nהכנס API Token של מאנדיי: ").strip()
    if not token:
        print("לא הוזן טוקן. יציאה.")
        sys.exit(1)

    # ── שלב 1: קרא עמודות קיימות ──────────────────────────────────────────────
    print("\n── קורא עמודות קיימות ──")
    try:
        res      = monday(token, GET_COLS_QUERY, {"boardId": [BOARD_ID]})
        existing = res["boards"][0]["columns"]
    except Exception as e:
        print(f"✗ שגיאה בקריאת עמודות: {e}")
        sys.exit(1)

    by_title = {c["title"]: c for c in existing}
    print(f"  נמצאו {len(existing)} עמודות")

    # ── שלב 2: הגדר לייבלים ───────────────────────────────────────────────────
    print(f"\n── מגדיר לייבלים ל-{len(COLUMNS_WITH_OPTIONS)} עמודות ──")
    errors = []

    for col_def in COLUMNS_WITH_OPTIONS:
        title   = col_def["title"]
        ctype   = col_def["type"]    # "status" | "dropdown"
        options = col_def["options"]

        col = by_title.get(title)
        if not col:
            msg = f"עמודה לא נמצאה: '{title}'"
            print(f"  ✗ {msg}")
            errors.append(msg)
            continue

        col_id = col["id"]
        print(f"  ⟳ {title}  ({ctype}, {len(options)} אפשרויות)")

        try:
            if ctype == "status":
                val = build_status_value(options)
            else:  # dropdown
                val = build_dropdown_value(options)

            monday(token, SET_LABELS_MUTATION, {
                "board": BOARD_ID,
                "col":   col_id,
                "val":   val,
            })

            preview = ", ".join(options[:4])
            suffix  = ", ..." if len(options) > 4 else ""
            print(f"     ✓  {preview}{suffix}")
            time.sleep(0.4)

        except Exception as e:
            msg = f"{title}: {e}"
            print(f"     ✗  {e}")
            errors.append(msg)
            time.sleep(0.5)

    # ── סיכום ─────────────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    if errors:
        print(f"⚠  הושלם עם {len(errors)} שגיאות:")
        for err in errors:
            print(f"   • {err}")
    else:
        print("✓  כל הלייבלים הוגדרו בהצלחה!")
    print(f"\n  קישור: https://monday.com/boards/{BOARD_ID}")
    print("=" * 55)


if __name__ == "__main__":
    main()
