#!/usr/bin/env python3
"""
Monday.com Board Creator
========================
יוצר בורד חדש במאנדיי ומגדיר עמודות לפי Export מ-Fillout או הגדרה ידנית.

שימוש:
    python monday_board_creator.py --token YOUR_API_TOKEN --name "שם הבורד" --fillout form_export.json
    python monday_board_creator.py --token YOUR_API_TOKEN --name "שם הבורד" --manual
"""

import json
import time
import argparse
import sys
from typing import Any

try:
    import requests
except ImportError:
    print("חסר: pip install requests")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# מיפוי סוגי שדות Fillout → סוגי עמודות Monday.com
# ──────────────────────────────────────────────────────────────────────────────

FILLOUT_TO_MONDAY: dict[str, str] = {
    # טקסט
    "ShortAnswer":       "text",
    "LongAnswer":        "long_text",
    "Email":             "email",
    "PhoneNumber":       "phone",
    "Link":              "link",
    "URLInput":          "link",

    # מספרים
    "NumberInput":       "numeric",
    "CurrencyInput":     "numeric",
    "Rating":            "rating",

    # תאריך / שעה
    "DatePicker":        "date",
    "TimePicker":        "hour",
    "DateTimePicker":    "date",

    # בחירה ← כאן ההבחנה החשובה:
    # בחירה בודדת  → Status  (color)
    "Dropdown":          "color",       # Single-select בממשק Fillout
    "MultipleChoice":    "color",       # Radio-style = בחירה אחת
    "YesNo":             "color",

    # בחירה מרובה → Dropdown ב-Monday (!)
    "MultiSelect":       "dropdown",    # Checkbox-style = ריבוי בחירות
    "Checkboxes":        "dropdown",

    # קבצים / תמונות
    "FileUpload":        "file",
    "ImagePicker":       "file",

    # כללי
    "Signature":         "text",
    "Address":           "location",
}

# סוגים שיש להם אפשרויות (labels)
TYPES_WITH_OPTIONS = {"color", "dropdown"}

# ──────────────────────────────────────────────────────────────────────────────
# לקוח Monday.com
# ──────────────────────────────────────────────────────────────────────────────

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

    def _query(self, query: str, variables: dict | None = None, retries: int = 3) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        for attempt in range(retries):
            try:
                resp = self.session.post(self.API_URL, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                if "errors" in data:
                    raise RuntimeError(f"Monday API error: {data['errors']}")

                # Rate-limit: 60 req/min — המתן אם צריך
                complexity = data.get("data", {}).get("complexity", {})
                if isinstance(complexity, dict) and complexity.get("after", 1) < 100:
                    print("  [!] Rate-limit קרוב — ממתין 2 שניות...")
                    time.sleep(2)

                return data["data"]

            except requests.exceptions.ConnectionError:
                wait = 2 ** attempt
                print(f"  [!] בעיית רשת, מנסה שוב בעוד {wait}ש...")
                time.sleep(wait)

        raise RuntimeError("נכשל לאחר מספר ניסיונות — בדוק חיבור אינטרנט")

    # ── בורד ──────────────────────────────────────────────────────────────────

    def create_board(self, name: str, board_kind: str = "public") -> int:
        """יוצר בורד חדש ומחזיר את ה-ID שלו."""
        query = """
        mutation ($name: String!, $kind: BoardKind!) {
            create_board(board_name: $name, board_kind: $kind) {
                id
            }
        }
        """
        result = self._query(query, {"name": name, "kind": board_kind})
        board_id = int(result["create_board"]["id"])
        print(f"  ✓ בורד נוצר: '{name}' (ID: {board_id})")
        return board_id

    # ── עמודות ────────────────────────────────────────────────────────────────

    def create_column(self, board_id: int, title: str, col_type: str) -> str:
        """יוצר עמודה ומחזיר את ה-ID שלה."""
        query = """
        mutation ($board: ID!, $title: String!, $type: ColumnType!) {
            create_column(board_id: $board, title: $title, column_type: $type) {
                id
                title
                type
            }
        }
        """
        result = self._query(query, {
            "board": str(board_id),
            "title": title,
            "type": col_type,
        })
        col_id = result["create_column"]["id"]
        print(f"  ✓ עמודה '{title}' ({col_type}) → ID: {col_id}")
        return col_id

    def set_status_labels(self, board_id: int, column_id: str, options: list[str]) -> None:
        """
        מגדיר תוויות לעמודת Status (בחירה בודדת / color).
        Monday.com משתמש ב-indices מ-0 עד N; index 5 שמור ל-Done.
        """
        if not options:
            return

        # בניית dict של { "index": "label" }
        # נשמור index 5 ריק (Done) אם יש collision
        labels: dict[str, str] = {}
        idx = 0
        for opt in options:
            if idx == 5:
                idx += 1  # דלג על 5 (Done המובנה)
            labels[str(idx)] = opt
            idx += 1

        value_json = json.dumps(labels)

        query = """
        mutation ($board: ID!, $col: String!, $val: String!) {
            change_column_metadata(
                board_id: $board,
                column_id: $col,
                column_property: labels,
                value: $val
            ) {
                id
            }
        }
        """
        self._query(query, {
            "board": str(board_id),
            "col": column_id,
            "val": value_json,
        })
        print(f"    → תוויות Status הוגדרו: {options}")

    def set_dropdown_labels(self, board_id: int, column_id: str, options: list[str]) -> None:
        """
        מגדיר תוויות לעמודת Dropdown (בחירה מרובה).
        הפורמט שונה מ-Status: { "labels": ["opt1", "opt2", ...] }
        """
        if not options:
            return

        value_json = json.dumps({"labels": options})

        query = """
        mutation ($board: ID!, $col: String!, $val: String!) {
            change_column_metadata(
                board_id: $board,
                column_id: $col,
                column_property: labels,
                value: $val
            ) {
                id
            }
        }
        """
        self._query(query, {
            "board": str(board_id),
            "col": column_id,
            "val": value_json,
        })
        print(f"    → תוויות Dropdown הוגדרו: {options}")

    def set_column_options(
        self, board_id: int, column_id: str, col_type: str, options: list[str]
    ) -> None:
        """מנתב לפונקציית הטעינה הנכונה לפי סוג העמודה."""
        if col_type == "color":
            self.set_status_labels(board_id, column_id, options)
        elif col_type == "dropdown":
            self.set_dropdown_labels(board_id, column_id, options)

    def verify_token(self) -> str:
        """בודק שהטוקן תקין ומחזיר שם המשתמש."""
        query = "{ me { name email } }"
        result = self._query(query)
        name = result["me"]["name"]
        email = result["me"]["email"]
        print(f"  ✓ מחובר כ: {name} ({email})")
        return name


# ──────────────────────────────────────────────────────────────────────────────
# פרסור Fillout Export
# ──────────────────────────────────────────────────────────────────────────────

def parse_fillout_export(filepath: str) -> list[dict[str, Any]]:
    """
    מפרסר קובץ JSON של Export מ-Fillout ומחזיר רשימת עמודות:
    [{ "title": "...", "monday_type": "color", "options": ["a","b"] }, ...]

    Fillout מייצא בפורמטים שונים — הסקריפט מנסה לזהות אוטומטית.
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    columns: list[dict] = []

    # נסה לאתר את רשימת השדות בכל מבנה אפשרי
    fields: list[dict] = []
    if isinstance(data, list):
        fields = data
    elif "questions" in data:
        fields = data["questions"]
    elif "fields" in data:
        fields = data["fields"]
    elif "form" in data and "questions" in data["form"]:
        fields = data["form"]["questions"]
    elif "pages" in data:
        for page in data.get("pages", []):
            fields.extend(page.get("questions", []))
    else:
        # נסה כל מפתח שמכיל רשימה
        for key, val in data.items():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                fields = val
                print(f"  [!] זיהוי אוטומטי: שימוש בשדה '{key}'")
                break

    if not fields:
        raise ValueError("לא נמצאו שדות בקובץ ה-Export. בדוק שהקובץ תקין.")

    for field in fields:
        # שם השאלה / תווית
        title = (
            field.get("name")
            or field.get("title")
            or field.get("label")
            or field.get("text")
            or "שדה ללא שם"
        )
        title = str(title).strip()

        # סוג השדה
        field_type = (
            field.get("type")
            or field.get("fieldType")
            or field.get("inputType")
            or "ShortAnswer"
        )

        monday_type = FILLOUT_TO_MONDAY.get(field_type, "text")

        # אפשרויות (לשדות בחירה)
        options: list[str] = []
        if monday_type in TYPES_WITH_OPTIONS:
            raw_opts = (
                field.get("options")
                or field.get("choices")
                or field.get("answers")
                or field.get("values")
                or []
            )
            for opt in raw_opts:
                if isinstance(opt, str):
                    options.append(opt.strip())
                elif isinstance(opt, dict):
                    label = (
                        opt.get("label")
                        or opt.get("value")
                        or opt.get("text")
                        or opt.get("name")
                        or ""
                    )
                    if label:
                        options.append(str(label).strip())

        # דלג על שדות סיסטם (תיאור, כותרת, עמוד, וכו')
        skip_types = {"Statement", "Section", "PageBreak", "WelcomePage", "ThankYou"}
        if field_type in skip_types:
            continue

        columns.append({
            "title": title,
            "monday_type": monday_type,
            "options": options,
            "fillout_type": field_type,
        })

    return columns


# ──────────────────────────────────────────────────────────────────────────────
# מצב ידני — הגדרת עמודות אינטראקטיבית
# ──────────────────────────────────────────────────────────────────────────────

MANUAL_TYPES: dict[str, str] = {
    "1": ("טקסט קצר",     "text"),
    "2": ("טקסט ארוך",    "long_text"),
    "3": ("מספר",         "numeric"),
    "4": ("תאריך",        "date"),
    "5": ("Status (בחירה בודדת)",   "color"),
    "6": ("Dropdown (בחירה מרובה)", "dropdown"),
    "7": ("אימייל",       "email"),
    "8": ("טלפון",        "phone"),
    "9": ("קישור",        "link"),
    "10": ("קבצים",       "file"),
    "11": ("דירוג",       "rating"),
}


def prompt_columns_manually() -> list[dict]:
    """מנחה את המשתמש להגדיר עמודות ידנית בשורת הפקודה."""
    columns: list[dict] = []
    print("\n=== הגדרת עמודות ידנית ===")
    print("הכנס 'סיום' כשם עמודה כדי לסיים.\n")

    while True:
        title = input("שם עמודה: ").strip()
        if title.lower() in ("סיום", "done", "quit", "q", ""):
            break

        print("סוג עמודה:")
        for k, (label, _) in MANUAL_TYPES.items():
            print(f"  {k}. {label}")
        choice = input("בחר מספר [1]: ").strip() or "1"
        _, monday_type = MANUAL_TYPES.get(choice, ("טקסט", "text"))

        options: list[str] = []
        if monday_type in TYPES_WITH_OPTIONS:
            print("הכנס אפשרויות (שורה אחת = אפשרות אחת, שורה ריקה לסיום):")
            while True:
                opt = input("  → ").strip()
                if not opt:
                    break
                options.append(opt)

        columns.append({
            "title": title,
            "monday_type": monday_type,
            "options": options,
        })
        print()

    return columns


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def build_board(client: MondayClient, board_name: str, columns: list[dict]) -> int:
    """יוצר את הבורד ואת כל העמודות, עם delay קטן בין בקשות."""
    print(f"\n--- יוצר בורד: '{board_name}' ---")
    board_id = client.create_board(board_name)
    time.sleep(0.5)

    print(f"\n--- יוצר {len(columns)} עמודות ---")
    for col in columns:
        title       = col["title"]
        monday_type = col["monday_type"]
        options     = col.get("options", [])
        fillout     = col.get("fillout_type", "")

        tag = f" [{fillout}]" if fillout else ""
        print(f"\n• '{title}'{tag}")

        col_id = client.create_column(board_id, title, monday_type)
        time.sleep(0.3)

        if options and monday_type in TYPES_WITH_OPTIONS:
            client.set_column_options(board_id, col_id, monday_type, options)
            time.sleep(0.3)

    return board_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="יוצר בורד ב-Monday.com מ-Export של Fillout או הגדרה ידנית"
    )
    parser.add_argument("--token",   required=True,  help="Monday.com API Token")
    parser.add_argument("--name",    required=True,  help="שם הבורד החדש")
    parser.add_argument("--fillout", metavar="FILE",  help="נתיב לקובץ JSON של Fillout export")
    parser.add_argument("--manual",  action="store_true", help="הגדרת עמודות ידנית")
    parser.add_argument("--kind",    default="public",
                        choices=["public", "private", "share"],
                        help="סוג הבורד (ברירת מחדל: public)")
    parser.add_argument("--preview", action="store_true",
                        help="הצג תצוגה מקדימה של העמודות בלי ליצור בפועל")
    args = parser.parse_args()

    if not args.fillout and not args.manual:
        parser.error("חובה לציין --fillout <קובץ> או --manual")

    client = MondayClient(args.token)

    # בדיקת טוקן (לא בpreview)
    if not args.preview:
        print("\n=== בדיקת חיבור ל-Monday.com ===")
        client.verify_token()

    # הכנת עמודות
    columns: list[dict] = []
    if args.fillout:
        print(f"\n=== פרסור Fillout Export: {args.fillout} ===")
        columns = parse_fillout_export(args.fillout)
        print(f"  ✓ זוהו {len(columns)} שדות")

        # הצג סיכום
        print("\nסיכום עמודות שיווצרו:")
        for c in columns:
            kind = "Status (בחירה בודדת)" if c["monday_type"] == "color" else \
                   "Dropdown (בחירה מרובה)" if c["monday_type"] == "dropdown" else \
                   c["monday_type"]
            opts = f" | אפשרויות: {c['options']}" if c.get("options") else ""
            print(f"  • {c['title']}  →  {kind}{opts}")

    elif args.manual:
        columns = prompt_columns_manually()

    if not columns:
        print("\n[!] לא הוגדרו עמודות — יציאה.")
        sys.exit(0)

    if args.preview:
        print("\n[PREVIEW] בוצע תצוגה מקדימה בלבד — לא נוצר כלום ב-Monday.com")
        sys.exit(0)

    # אישור לפני יצירה
    print(f"\n{'─'*50}")
    print(f"עומד ליצור בורד '{args.name}' עם {len(columns)} עמודות.")
    confirm = input("להמשיך? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes", "כן", "ן"):
        print("בוטל.")
        sys.exit(0)

    # יצירה בפועל
    board_id = build_board(client, args.name, columns)

    print(f"\n{'='*50}")
    print(f"✓ הבורד נוצר בהצלחה!")
    print(f"  שם:   {args.name}")
    print(f"  ID:   {board_id}")
    print(f"  קישור: https://monday.com/boards/{board_id}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
