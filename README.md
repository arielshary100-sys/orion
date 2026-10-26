# Air Touch ✋

שליטה במחשב בתנועות יד דרך המצלמה: מסך בית עם Google, YouTube ו-Shorts, "נגיעה" באוויר בצביטה, ומעבר בין סרטוני Shorts בתנועת יד למעלה ולמטה.

## מחוות

| מחווה | מה קורה |
|---|---|
| הזזת האצבע המורה | מזיזה את הסמן / העכבר |
| צביטה (אגודל + אצבע מורה) | לחיצה |
| יד מהר למעלה | הסרטון הבא ב-Shorts (באתרים אחרים: גלילה למטה) |
| יד מהר למטה | הסרטון הקודם (גלילה למעלה) |
| כף יד פתוחה 1.5 שניות | חזרה למסך הבית |

## גרסת פייתון (מחשב)

גרסה זו שולטת בעכבר האמיתי של המחשב, כך שהיא עובדת על האתרים האמיתיים של Google ו-YouTube.

דרוש Python 3.9 עד 3.12 ומצלמת רשת.

```bash
git clone https://github.com/arielshary100-sys/orion.git
cd orion
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python air_touch.py
```

מקשים בחלון המצלמה: `H` מסך בית · `S` מצב Shorts · `P` השהיה · `Q` או `Esc` יציאה.

**Mac:** בפעם הראשונה צריך לאשר ל-Terminal גישה למצלמה, ובנוסף ב-System Settings → Privacy & Security → Accessibility לאשר לו שליטה בעכבר.

## גרסת דפדפן (iPad / טלפון)

הקובץ `index.html` הוא גרסת HTML שרצה בדפדפן, כולל ב-iPad. היא דורשת https, ולכן הכי נוח להפעיל אותה דרך GitHub Pages:
Settings → Pages → Branch: `main`, Folder: `/ (root)`. הכתובת תהיה `https://arielshary100-sys.github.io/orion/`.

בגרסת הדפדפן Google ו-YouTube נפתחים בלשונית חדשה, ואת השליטה בתנועות יש בתוך האפליקציה: מקלדת חיפוש באוויר, פיד Shorts (אפשר להדביק קישורים) וציור באוויר.

## איך זה עובד

זיהוי היד נעשה עם [MediaPipe Hands](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker), שמחזיר 21 נקודות על כף היד בכל פריים. הצביטה מזוהה לפי המרחק בין קצה האגודל לקצה האצבע המורה ביחס לגודל היד, והחלקה מזוהה לפי מהירות התזוזה של שורש כף היד.
