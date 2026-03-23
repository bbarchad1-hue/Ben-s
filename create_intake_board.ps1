# ============================================================
#  יצירת בורד אינטייק PEOPLE במאנדיי - PowerShell
#  הרצה: לחץ ימני על הקובץ → "Run with PowerShell"
#  או בטרמינל: .\create_intake_board.ps1
# ============================================================

$API_URL     = "https://api.monday.com/v2"
$WORKSPACE_ID = 6037106

# ── פונקציה לשליחת בקשות GraphQL ────────────────────────────
function Invoke-Monday {
    param(
        [string]$Token,
        [string]$Query,
        [hashtable]$Variables = @{}
    )
    $body = @{ query = $Query; variables = $Variables } | ConvertTo-Json -Depth 10
    $headers = @{
        "Authorization" = $Token
        "Content-Type"  = "application/json"
        "API-Version"   = "2023-10"
    }
    try {
        $resp = Invoke-RestMethod -Uri $API_URL -Method POST -Headers $headers -Body $body -Encoding UTF8
        if ($resp.errors) { throw ($resp.errors | ConvertTo-Json) }
        return $resp.data
    } catch {
        throw "שגיאת API: $_"
    }
}

# ── כל עמודות הבורד (לפי סדר הדפים בפורם) ──────────────────
#  type: "color"    = Status  (בחירה בודדת)
#  type: "dropdown" = Dropdown (בחירה מרובה)
$COLUMNS = @(
    # דף 1 - פתיח
    @{ title="שם המפונים";                                      type="text";     options=@() }
    @{ title="תאריך אינטייק";                                   type="date";     options=@() }
    @{ title="עורך האינטייק";                                   type="dropdown"; options=@("אילת","רן","עמית","סבסטיאן","יערה","שי","חן שטרס","סיון","מג'ד","רוני קטבי","טארק","איתן שרבר","מיכל","נטלי","נט","אלינה","שיר") }
    @{ title="חתם על ויתור סודיות";                             type="boolean";  options=@() }

    # דף 2 - פרטי קשר
    @{ title="מספר הטלפון";                                     type="phone";    options=@() }
    @{ title="האם יש לערוך תיאום מלא מול המפונה?";             type="boolean";  options=@() }
    @{ title="איש קשר נוסף";                                    type="text";     options=@() }
    @{ title="טלפון איש קשר נוסף";                              type="phone";    options=@() }

    # דף 3 - פרטים אישיים
    @{ title="זיקה לנכס";                                       type="color";    options=@("שכירות","אחר","בעלות","דיור ציבורי","בעלים שמתגורר בנכס") }
    @{ title="תאריך לידה";                                      type="date";     options=@() }
    @{ title="סטטוס משפחתי";                                    type="text";     options=@() }
    @{ title="תיאור מצב בריאות, תפקוד פיזי, נפשי נוכחי";      type="text";     options=@() }
    @{ title="סטטוס תעסוקתי";                                   type="color";    options=@("עובד","עצמאי","מובטל","פנסיונר","לא עובד","אחר","נכות ביטוח לאומי") }
    @{ title="פירוט בנוגע לסטטוס התעסוקתי";                    type="text";     options=@() }
    @{ title="מיקום העבודה";                                    type="text";     options=@() }
    @{ title="מקורות הכנסה ותמיכה כלכלית";                     type="long_text";options=@() }
    @{ title="כמה חודשים יכול לשלם?";                          type="numeric";  options=@() }

    # דף 4 - פרטי דיור מקוריים
    @{ title="כתובת מקורית";                                    type="text";     options=@() }
    @{ title="מספר דירה מקורית";                                type="numeric";  options=@() }
    @{ title='גודל דירה מקורית במ"ר';                          type="numeric";  options=@() }
    @{ title="מספר חדרי שינה בדירה המקורית";                   type="dropdown"; options=@("1","2","2.5","3","4","5","6","7","8","9","-") }
    @{ title="גובה דמי השכירות בדירה שנפגעה";                  type="numeric";  options=@() }
    @{ title="סיווג הבניין";                                    type="color";    options=@("ירוק","כתום","אדום","לא ידוע") }
    @{ title="תיאור מצב הנכס";                                  type="long_text";options=@() }
    @{ title="סטטוס שיפוץ";                                     type="color";    options=@("לא התחיל","בתהליך","הושלם","שכירות (לא רלוונטי)","הבניין נהרס") }
    @{ title="גורם מבצע של השיפוץ";                             type="color";    options=@("עמיגור","פרטי","טרם נקבע","אין צורך בשיפוץ","שכירות (לא רלוונטי)","בניין נהרס") }
    @{ title="פירוט";                                           type="text";     options=@() }
    @{ title="תחום שיפוץ נדרש";                                 type="dropdown"; options=@("מסגרת וחלונות","קירות, בנייה, ריצוף טייח וצבע","אינסטלציה","חשמל","נגרות","אין צורך") }

    # דף 5 - פגיעות רכוש
    @{ title="האם צריך לברר מה מצב הריהוט בנכס?";             type="color";    options=@("כן, צריך ללכת לברר","אין צורך, היו כבר בנכס","אין צורך, הבניין הרוס לחלוטין") }
    @{ title="איזה ציוד נדרש לכניסה לדירה החלופית?";           type="color";    options=@("ציוד חלקי","פריטים בודדים","ציוד מלא") }
    @{ title="פירוט בנוגע לציוד הנדרש";                        type="long_text";options=@() }
    @{ title="האם הוגשה תביעה לקרן הפיצויים (מס רכוש)?";      type="color";    options=@("כן","לא") }
    @{ title="מספר פנייה לקרן הפיצויים (תכולה)";               type="numeric";  options=@() }
    @{ title="מספר פנייה לקרן פיצויים (מבנה - בעלי דירות)";   type="text";     options=@() }
    @{ title="תיאור מילולי של סטטוס הפנייה לקרן הפיצויים";    type="text";     options=@() }

    # דף 6 - מצב מגורים
    @{ title="מקום מגורים נוכחי";                              type="color";    options=@('בי"ח',"במלון","השכיר דירה","אצל בני משפחה","אחר") }
    @{ title="תאריך יציאה מהמלון - לפי מס רכוש";              type="date";     options=@() }
    @{ title="אם קיים פתרון דיור חלופי - מהו?";               type="long_text";options=@() }
    @{ title="מתי מתחיל פתרון הדיור?";                         type="date";     options=@() }

    # דף 7 - דיירים נוספים
    @{ title="כמות נפשות לדירה החלופית";                       type="text";     options=@() }
    @{ title="מה מתוך האפשרויות מקובל מבחינת מיגון בדירה החדשה?"; type="dropdown"; options=@("ממד חובה","ממק (מרחב מוגן קומתי)","מקלט בבניין","מקלט בקרבת הבניין","חדר מדרגות","היעדר מיגון","עדיפות לממד","אין צורך מיוחד") }
    @{ title="מספר חדרים בדירה החדשה (כולל סלון)";             type="numeric";  options=@() }
    @{ title="האם נדרשת נגישות בדירה / בבניין?";               type="text";     options=@() }
    @{ title='סכום שנקבע ממס רכוש לשכ"ד';                     type="numeric";  options=@() }
    @{ title="שכר דירה מקסימלי בדירה החדשה";                   type="numeric";  options=@() }
    @{ title="אזורים רלוונטים למגורים בבית שמש";               type="text";     options=@() }
    @{ title="ערים רלוונטיות למעבר";                            type="text";     options=@() }

    # דף 8 - שאלות כלכליות
    @{ title="בעלות על דירה נוספת";                             type="color";    options=@("כן","לא") }
    @{ title="קצבת זקנה";                                       type="color";    options=@("כן","לא") }
    @{ title="השלמת הכנסה";                                     type="color";    options=@("כן","לא") }
    @{ title="קצבת השלמה לנכות";                                type="color";    options=@("כן","לא") }
    @{ title='מקבל סיוע בשכ"ד';                                type="color";    options=@("כן","לא") }

    # דף 9 - הערות
    @{ title="הערות עורכת האינטייק";                            type="long_text";options=@() }
)

# ── קלט מהמשתמש ─────────────────────────────────────────────
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "   יצירת בורד אינטייק PEOPLE במאנדיי" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

$secureToken = Read-Host "הכנס API Token של מאנדיי" -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
)

if (-not $token) { Write-Host "לא הוזן טוקן. יציאה."; exit }

$boardName = Read-Host "שם הבורד החדש"
if (-not $boardName) { Write-Host "לא הוזן שם. יציאה."; exit }

# ── בדיקת חיבור ─────────────────────────────────────────────
Write-Host ""
Write-Host "── בדיקת חיבור ──" -ForegroundColor Yellow
try {
    $me = Invoke-Monday -Token $token -Query "{ me { name email } }"
    Write-Host "  ✓ מחובר כ: $($me.me.name) ($($me.me.email))" -ForegroundColor Green
} catch {
    Write-Host "  ✗ שגיאה: $_" -ForegroundColor Red
    Write-Host "  בדוק שהטוקן תקין ויש חיבור לאינטרנט."
    exit
}

Write-Host ""
Write-Host "  Workspace ID : $WORKSPACE_ID"
Write-Host "  שם הבורד    : $boardName"
Write-Host "  מספר עמודות : $($COLUMNS.Count)"
Write-Host ""

$confirm = Read-Host "ליצור את הבורד? [y/N]"
if ($confirm -notmatch "^(y|yes|כן|ן)$") { Write-Host "בוטל."; exit }

# ── יצירת בורד ──────────────────────────────────────────────
Write-Host ""
Write-Host "── יוצר בורד ──" -ForegroundColor Yellow

$createBoardQ = @"
mutation (`$name: String!, `$wsId: Int!) {
    create_board(board_name: `$name, board_kind: public, workspace_id: `$wsId) { id }
}
"@

try {
    $result = Invoke-Monday -Token $token -Query $createBoardQ -Variables @{ name=$boardName; wsId=$WORKSPACE_ID }
    $boardId = $result.create_board.id
    Write-Host "  ✓ בורד נוצר — ID: $boardId" -ForegroundColor Green
} catch {
    Write-Host "  ✗ שגיאה ביצירת בורד: $_" -ForegroundColor Red
    exit
}

Start-Sleep -Milliseconds 800

# ── יצירת עמודות ────────────────────────────────────────────
Write-Host ""
Write-Host "── יוצר $($COLUMNS.Count) עמודות ──" -ForegroundColor Yellow

$createColQ = @"
mutation (`$board: ID!, `$title: String!, `$type: ColumnType!) {
    create_column(board_id: `$board, title: `$title, column_type: `$type) { id }
}
"@

$setLabelsQ = @"
mutation (`$board: ID!, `$col: String!, `$val: String!) {
    change_column_metadata(board_id: `$board, column_id: `$col, column_property: labels, value: `$val) { id }
}
"@

$errors = @()
$i = 0

foreach ($col in $COLUMNS) {
    $i++
    $typeLabel = switch ($col.type) {
        "color"    { "Status (בחירה בודדת)" }
        "dropdown" { "Dropdown (בחירה מרובה)" }
        default    { $col.type }
    }
    Write-Host "  [$("{0:D2}" -f $i)/$($COLUMNS.Count)] $($col.title)  →  $typeLabel"

    try {
        # יצירת עמודה
        $colResult = Invoke-Monday -Token $token -Query $createColQ -Variables @{
            board = "$boardId"
            title = $col.title
            type  = $col.type
        }
        $colId = $colResult.create_column.id
        Start-Sleep -Milliseconds 350

        # טעינת אפשרויות
        if ($col.options.Count -gt 0) {
            if ($col.type -eq "color") {
                # Status: { "0": "opt", "1": "opt", ... } — דולג על index 5
                $labels = @{}
                $idx = 0
                foreach ($opt in $col.options) {
                    if ($idx -eq 5) { $idx++ }
                    $labels["$idx"] = $opt
                    $idx++
                }
                $val = $labels | ConvertTo-Json -Compress
            } elseif ($col.type -eq "dropdown") {
                # Dropdown: { "labels": ["opt1", "opt2", ...] }
                $val = @{ labels = $col.options } | ConvertTo-Json -Compress
            }

            Invoke-Monday -Token $token -Query $setLabelsQ -Variables @{
                board = "$boardId"
                col   = $colId
                val   = $val
            } | Out-Null

            Write-Host "       ↳ $($col.options -join ', ')" -ForegroundColor DarkGray
            Start-Sleep -Milliseconds 300
        }
    } catch {
        $msg = "שגיאה בעמודה '$($col.title)': $_"
        Write-Host "       ✗ $msg" -ForegroundColor Red
        $errors += $msg
        Start-Sleep -Milliseconds 500
    }
}

# ── סיכום ───────────────────────────────────────────────────
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
if ($errors.Count -gt 0) {
    Write-Host "⚠  הושלם עם $($errors.Count) שגיאות:" -ForegroundColor Yellow
    $errors | ForEach-Object { Write-Host "   • $_" -ForegroundColor Red }
} else {
    Write-Host "✓  הכל הושלם ללא שגיאות!" -ForegroundColor Green
}
Write-Host ""
Write-Host "  שם הבורד : $boardName"
Write-Host "  Board ID  : $boardId"
Write-Host "  קישור     : https://monday.com/boards/$boardId"
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "לחץ Enter לסגירה..."
Read-Host | Out-Null
