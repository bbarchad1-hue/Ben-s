#!/usr/bin/env python3
"""
יוצר בורד אינטייק במאנדיי - מותאם אישית לפורם PEOPLE
===================================================
הרצה:
    python create_intake_board.py

הסקריפט ישאל אותך על הטוקן ושם הבורד, ואז ייצור את כל העמודות אוטומטית.
"""

import json
import time
import sys

try:
    import requests
except ImportError:
    print("חסר חבילה. הרץ: pip install requests")
    sys.exit(1)


# ─── Workspace קבוע ───────────────────────────────────────────────────────────
WORKSPACE_ID = 6037106


# ─── כל העמודות לפי סדר הדפים בפורם ─────────────────────────────────────────
#
#  monday_type:
#    "text"       = טקסט קצר
#    "long_text"  = טקסט ארוך
#    "numeric"    = מספר
#    "date"       = תאריך
#    "phone"      = טלפון
#    "boolean"    = צ'קבוקס
#    "color"      = Status  (בחירה בודדת)   ← MultipleChoice ב-Fillout
#    "dropdown"   = Dropdown (בחירה מרובה) ← MultiSelect / Checkboxes ב-Fillout
#
COLUMNS = [
    # ── דף 1: טופס מילוי אינטייק ─────────────────────────────────────────────
    {
        "title": "שם המפונים",
        "type": "text",
        "options": [],
    },
    {
        "title": "תאריך אינטייק",
        "type": "date",
        "options": [],
    },
    {
        "title": "עורך האינטייק",
        "type": "dropdown",   # MultiSelect → בחירה מרובה
        "options": [
            "אילת", "רן", "עמית", "סבסטיאן", "יערה", "שי",
            "חן שטרס", "סיון", "מג'ד", "רוני קטבי", "טארק",
            "איתן שרבר", "מיכל", "נטלי", "נט", "אלינה", "שיר",
        ],
    },
    {
        "title": "חתם על ויתור סודיות",
        "type": "boolean",
        "options": [],
    },

    # ── דף 2: פרטי קשר ────────────────────────────────────────────────────────
    {
        "title": "מספר הטלפון",
        "type": "phone",
        "options": [],
    },
    {
        "title": "האם יש לערוך תיאום מלא מול המפונה?",
        "type": "boolean",
        "options": [],
    },
    {
        "title": "איש קשר נוסף",
        "type": "text",
        "options": [],
    },
    {
        "title": "טלפון איש קשר נוסף",
        "type": "phone",
        "options": [],
    },

    # ── דף 3: פרטים אישיים ───────────────────────────────────────────────────
    {
        "title": "זיקה לנכס",
        "type": "color",   # Status → בחירה בודדת
        "options": ["שכירות", "אחר", "בעלות", "דיור ציבורי", "בעלים שמתגורר בנכס"],
    },
    {
        "title": "תאריך לידה",
        "type": "date",
        "options": [],
    },
    {
        "title": "סטטוס משפחתי",
        "type": "text",
        "options": [],
    },
    {
        "title": "תיאור מצב בריאות, תפקוד פיזי, נפשי נוכחי",
        "type": "text",
        "options": [],
    },
    {
        "title": "סטטוס תעסוקתי",
        "type": "color",   # Status → בחירה בודדת
        "options": ["עובד", "עצמאי", "מובטל", "פנסיונר", "לא עובד", "אחר", "נכות ביטוח לאומי"],
    },
    {
        "title": "פירוט בנוגע לסטטוס התעסוקתי",
        "type": "text",
        "options": [],
    },
    {
        "title": "מיקום העבודה",
        "type": "text",
        "options": [],
    },
    {
        "title": "מקורות הכנסה ותמיכה כלכלית",
        "type": "long_text",
        "options": [],
    },
    {
        "title": "כמה חודשים יכול לשלם?",
        "type": "numeric",
        "options": [],
    },

    # ── דף 4: פרטי דיור מקוריים ──────────────────────────────────────────────
    {
        "title": "כתובת מקורית",
        "type": "text",
        "options": [],
    },
    {
        "title": "מספר דירה מקורית",
        "type": "numeric",
        "options": [],
    },
    {
        "title": 'גודל דירה מקורית במ"ר',
        "type": "numeric",
        "options": [],
    },
    {
        "title": "מספר חדרי שינה בדירה המקורית",
        "type": "dropdown",   # MultiSelect → בחירה מרובה
        "options": ["1", "2", "2.5", "3", "4", "5", "6", "7", "8", "9", "-"],
    },
    {
        "title": "גובה דמי השכירות בדירה שנפגעה",
        "type": "numeric",
        "options": [],
    },
    {
        "title": "סיווג הבניין",
        "type": "color",   # Status → בחירה בודדת
        "options": ["ירוק", "כתום", "אדום", "לא ידוע"],
    },
    {
        "title": "תיאור מצב הנכס",
        "type": "long_text",
        "options": [],
    },
    {
        "title": "סטטוס שיפוץ",
        "type": "color",   # Status → בחירה בודדת
        "options": ["לא התחיל", "בתהליך", "הושלם", "שכירות (לא רלוונטי)", "הבניין נהרס"],
    },
    {
        "title": "גורם מבצע של השיפוץ",
        "type": "color",   # Status → בחירה בודדת
        "options": ["עמיגור", "פרטי", "טרם נקבע", "אין צורך בשיפוץ", "שכירות (לא רלוונטי)", "בניין נהרס"],
    },
    {
        "title": "פירוט",
        "type": "text",
        "options": [],
    },
    {
        "title": "תחום שיפוץ נדרש",
        "type": "dropdown",   # Checkboxes → בחירה מרובה
        "options": ["מסגרת וחלונות", "קירות, בנייה, ריצוף טייח וצבע", "אינסטלציה", "חשמל", "נגרות", "אין צורך"],
    },

    # ── דף 5: פגיעות רכוש ────────────────────────────────────────────────────
    {
        "title": "האם צריך לברר מה מצב הריהוט בנכס?",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן, צריך ללכת לברר", "אין צורך, היו כבר בנכס", "אין צורך, הבניין הרוס לחלוטין"],
    },
    {
        "title": "איזה ציוד נדרש לכניסה לדירה החלופית?",
        "type": "color",   # Status → בחירה בודדת
        "options": ["ציוד חלקי", "פריטים בודדים", "ציוד מלא"],
    },
    {
        "title": "פירוט בנוגע לציוד הנדרש",
        "type": "long_text",
        "options": [],
    },
    {
        "title": "האם הוגשה תביעה לקרן הפיצויים (מס רכוש)?",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },
    {
        "title": "מספר פנייה לקרן הפיצויים (תכולה)",
        "type": "numeric",
        "options": [],
    },
    {
        "title": "מספר פנייה לקרן פיצויים (מבנה - בעלי דירות)",
        "type": "text",
        "options": [],
    },
    {
        "title": "תיאור מילולי של סטטוס הפנייה לקרן הפיצויים",
        "type": "text",
        "options": [],
    },

    # ── דף 6: מצב מגורים ─────────────────────────────────────────────────────
    {
        "title": "מקום מגורים נוכחי",
        "type": "color",   # Status → בחירה בודדת
        "options": ['בי"ח', "במלון", "השכיר דירה", "אצל בני משפחה", "אחר"],
    },
    {
        "title": "תאריך יציאה מהמלון - לפי מס רכוש",
        "type": "date",
        "options": [],
    },
    {
        "title": "אם קיים פתרון דיור חלופי - מהו?",
        "type": "long_text",
        "options": [],
    },
    {
        "title": "מתי מתחיל פתרון הדיור?",
        "type": "date",
        "options": [],
    },

    # ── דף 7: דיירים נוספים ──────────────────────────────────────────────────
    {
        "title": "כמות נפשות לדירה החלופית",
        "type": "text",
        "options": [],
    },
    {
        "title": "מה מתוך האפשרויות מקובל מבחינת מיגון בדירה החדשה?",
        "type": "dropdown",   # MultiSelect → בחירה מרובה
        "options": [
            "ממד חובה",
            "ממק (מרחב מוגן קומתי)",
            "מקלט בבניין",
            "מקלט בקרבת הבניין",
            "חדר מדרגות",
            "היעדר מיגון",
            "עדיפות לממד",
            "אין צורך מיוחד",
        ],
    },
    {
        "title": "מספר חדרים בדירה החדשה (כולל סלון)",
        "type": "numeric",
        "options": [],
    },
    {
        "title": "האם נדרשת נגישות בדירה / בבניין?",
        "type": "text",
        "options": [],
    },
    {
        "title": 'סכום שנקבע ממס רכוש לשכ"ד',
        "type": "numeric",
        "options": [],
    },
    {
        "title": "שכר דירה מקסימלי בדירה החדשה",
        "type": "numeric",
        "options": [],
    },
    {
        "title": "אזורים רלוונטים למגורים בבית שמש",
        "type": "text",
        "options": [],
    },
    {
        "title": "ערים רלוונטיות למעבר",
        "type": "text",
        "options": [],
    },

    # ── דף 8: שאלות כלכליות ──────────────────────────────────────────────────
    {
        "title": "בעלות על דירה נוספת",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },
    {
        "title": "קצבת זקנה",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },
    {
        "title": "השלמת הכנסה",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },
    {
        "title": "קצבת השלמה לנכות",
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },
    {
        "title": 'מקבל סיוע בשכ"ד',
        "type": "color",   # Status → בחירה בודדת
        "options": ["כן", "לא"],
    },

    # ── דף 9: הערות ──────────────────────────────────────────────────────────
    {
        "title": "הערות עורכת האינטייק",
        "type": "long_text",
        "options": [],
    },
]


# ─── לקוח Monday.com ──────────────────────────────────────────────────────────

class MondayClient:
    API_URL = "https://api.monday.com/v2"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token,
            "Content-Type": "application/json",
            "API-Version": "2023-10",
        })

    def _query(self, query: str, variables: dict = None, retries: int = 4) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        for attempt in range(retries):
            try:
                resp = self.session.post(self.API_URL, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if "errors" in data:
                    raise RuntimeError(f"Monday API שגיאה: {data['errors']}")
                return data["data"]
            except requests.exceptions.ConnectionError:
                wait = 2 ** attempt
                print(f"  [!] שגיאת רשת, מנסה שוב בעוד {wait} שניות...")
                time.sleep(wait)

        raise RuntimeError("נכשל לאחר מספר ניסיונות חיבור. בדוק אינטרנט וטוקן.")

    def verify_token(self) -> str:
        result = self._query("{ me { name email } }")
        name = result["me"]["name"]
        email = result["me"]["email"]
        print(f"  ✓ מחובר כ: {name} ({email})")
        return name

    def create_board(self, name: str, workspace_id: int) -> int:
        query = """
        mutation ($name: String!, $wsId: Int!) {
            create_board(
                board_name: $name,
                board_kind: public,
                workspace_id: $wsId
            ) { id }
        }
        """
        result = self._query(query, {"name": name, "wsId": workspace_id})
        board_id = int(result["create_board"]["id"])
        print(f"  ✓ בורד נוצר: '{name}' — ID: {board_id}")
        return board_id

    def create_column(self, board_id: int, title: str, col_type: str) -> str:
        query = """
        mutation ($board: ID!, $title: String!, $type: ColumnType!) {
            create_column(board_id: $board, title: $title, column_type: $type) {
                id title
            }
        }
        """
        result = self._query(query, {
            "board": str(board_id),
            "title": title,
            "type": col_type,
        })
        return result["create_column"]["id"]

    def set_status_labels(self, board_id: int, col_id: str, options: list[str]) -> None:
        """
        טוען תוויות לעמודת Status (color).
        הפורמט: { "0": "תווית0", "1": "תווית1", ... }
        index 5 שמור ל-Done — מדלגים עליו.
        """
        labels = {}
        idx = 0
        for opt in options:
            if idx == 5:
                idx += 1   # דלג על Done המובנה
            labels[str(idx)] = opt
            idx += 1

        query = """
        mutation ($board: ID!, $col: String!, $val: String!) {
            change_column_metadata(
                board_id: $board,
                column_id: $col,
                column_property: labels,
                value: $val
            ) { id }
        }
        """
        self._query(query, {
            "board": str(board_id),
            "col": col_id,
            "val": json.dumps(labels),
        })

    def set_dropdown_labels(self, board_id: int, col_id: str, options: list[str]) -> None:
        """
        טוען תוויות לעמודת Dropdown (בחירה מרובה).
        הפורמט שונה מ-Status: { "labels": ["opt1", "opt2", ...] }
        """
        query = """
        mutation ($board: ID!, $col: String!, $val: String!) {
            change_column_metadata(
                board_id: $board,
                column_id: $col,
                column_property: labels,
                value: $val
            ) { id }
        }
        """
        self._query(query, {
            "board": str(board_id),
            "col": col_id,
            "val": json.dumps({"labels": options}),
        })


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  יצירת בורד אינטייק PEOPLE במאנדיי")
    print("=" * 55)

    token = input("\nהכנס API Token של מאנדיי:\n> ").strip()
    if not token:
        print("לא הוזן טוקן. יציאה.")
        sys.exit(1)

    board_name = input("\nשם הבורד החדש:\n> ").strip()
    if not board_name:
        print("לא הוזן שם בורד. יציאה.")
        sys.exit(1)

    client = MondayClient(token)

    print("\n── בדיקת חיבור ──")
    try:
        client.verify_token()
    except Exception as e:
        print(f"\n✗ שגיאה: {e}")
        print("בדוק שהטוקן תקין ויש חיבור לאינטרנט.")
        sys.exit(1)

    print(f"\n── מידע ──")
    print(f"  Workspace ID : {WORKSPACE_ID}")
    print(f"  שם הבורד    : {board_name}")
    print(f"  מספר עמודות : {len(COLUMNS)}")

    confirm = input("\nליצור את הבורד? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes", "כן", "ן"):
        print("בוטל.")
        sys.exit(0)

    # יצירת בורד
    print("\n── יוצר בורד ──")
    try:
        board_id = client.create_board(board_name, WORKSPACE_ID)
    except Exception as e:
        print(f"✗ שגיאה ביצירת בורד: {e}")
        sys.exit(1)

    time.sleep(1)

    # יצירת עמודות
    print(f"\n── יוצר {len(COLUMNS)} עמודות ──")
    errors = []

    for i, col in enumerate(COLUMNS, 1):
        title   = col["title"]
        ctype   = col["type"]
        options = col["options"]

        type_label = (
            "Status (בחירה בודדת)"   if ctype == "color"    else
            "Dropdown (בחירה מרובה)" if ctype == "dropdown" else
            ctype
        )
        print(f"  [{i:02d}/{len(COLUMNS)}] {title}  →  {type_label}")

        try:
            col_id = client.create_column(board_id, title, ctype)
            time.sleep(0.4)

            if options:
                if ctype == "color":
                    client.set_status_labels(board_id, col_id, options)
                    print(f"         ↳ Status: {options}")
                elif ctype == "dropdown":
                    client.set_dropdown_labels(board_id, col_id, options)
                    print(f"         ↳ Dropdown: {options}")
                time.sleep(0.3)

        except Exception as e:
            msg = f"שגיאה בעמודה '{title}': {e}"
            print(f"         ✗ {msg}")
            errors.append(msg)
            time.sleep(0.5)

    # סיכום
    print(f"\n{'=' * 55}")
    if errors:
        print(f"⚠  הושלם עם {len(errors)} שגיאות:")
        for err in errors:
            print(f"   • {err}")
    else:
        print("✓  הכל הושלם ללא שגיאות!")

    print(f"\n  שם הבורד : {board_name}")
    print(f"  Board ID  : {board_id}")
    print(f"  קישור     : https://monday.com/boards/{board_id}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
