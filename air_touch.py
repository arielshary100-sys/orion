"""
Air Touch - שליטה במחשב בתנועות יד דרך המצלמה.

מסך בית עם אפליקציות (Google, YouTube, Shorts). צובטים (אגודל + אצבע מורה) כדי לפתוח.
אחרי שנפתח אתר, היד שולטת בעכבר האמיתי של המחשב:
  * אצבע מורה      -> מזיזה את העכבר
  * צביטה          -> לחיצה
  * יד מהר למעלה   -> הסרטון הבא ב-Shorts / גלילה למטה
  * יד מהר למטה    -> הסרטון הקודם / גלילה למעלה
  * כף יד פתוחה 1.5 שניות -> חזרה למסך הבית
מקשים בחלון המצלמה: H = מסך בית, S = מצב Shorts דולק/כבוי, P = השהיית שליטה, Q / Esc = יציאה.
"""

import math
import time
import webbrowser
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
import pyautogui

pyautogui.FAILSAFE = False  # the finger can reach screen corners; quit with Q/Esc instead
pyautogui.PAUSE = 0

# ---------------- tuning ----------------
PINCH_ON = 0.33          # thumb-index distance / hand size to start a pinch
PINCH_OFF = 0.55         # ...and to release it (hysteresis)
SWIPE_DIST = 0.17        # wrist travel (fraction of frame height) that counts as a swipe
SWIPE_WINDOW = 0.28      # seconds the travel must happen within
SWIPE_COOLDOWN = 0.8
PALM_HOLD = 1.5          # seconds of open palm to go home
MARGIN_X, MARGIN_Y = 0.12, 0.10   # camera edges ignored so the screen edges are reachable
SMOOTH_FREE, SMOOTH_PINCH = 0.45, 0.20

HOME_W, HOME_H = 1280, 720
APPS = [
    ("Google", "https://www.google.com", (244, 133, 66), False),
    ("YouTube", "https://www.youtube.com", (51, 0, 255), False),
    ("Shorts", "https://www.youtube.com/shorts", (60, 40, 230), True),
    ("Mouse", None, (40, 160, 90), False),
]
WIN = "Air Touch"


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y


def is_open_palm(lm):
    return all(finger_up(lm, t, p) for t, p in ((8, 6), (12, 10), (16, 14), (20, 18))) \
        and dist(lm[4], lm[5]) > dist(lm[0], lm[9]) * 0.6


class AirTouch:
    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()
        self.mode = "home"          # "home" (launcher) or "control" (real mouse)
        self.shorts = False         # swipes send arrow keys instead of scrolling
        self.paused = False
        self.pinching = False
        self.cx = self.cy = 0.5     # smoothed cursor, normalized 0..1
        self.wrist = deque()
        self.last_swipe = 0.0
        self.palm_since = None
        self.flash = ("", 0.0)
        self.tiles = self._layout_tiles()

    # ---------- launcher ----------
    def _layout_tiles(self):
        size, gap = 200, 60
        total = len(APPS) * size + (len(APPS) - 1) * gap
        x0, y0 = (HOME_W - total) // 2, 300
        return [(x0 + i * (size + gap), y0, size, size) for i in range(len(APPS))]

    def tile_at(self, x, y):
        for i, (tx, ty, w, h) in enumerate(self.tiles):
            if tx <= x <= tx + w and ty <= y <= ty + h:
                return i
        return None

    def open_app(self, i):
        name, url, _, shorts = APPS[i]
        self.shorts = shorts
        if url:
            webbrowser.open(url)
        self.mode = "control"
        self.say(f"{name} - hand controls the mouse")
        cv2.resizeWindow(WIN, 360, 270)
        cv2.moveWindow(WIN, 20, self.screen_h - 330)

    def go_home(self):
        self.mode = "home"
        self.shorts = False
        cv2.resizeWindow(WIN, HOME_W, HOME_H)
        cv2.moveWindow(WIN, 40, 40)
        self.say("Home")

    def say(self, text):
        self.flash = (text, time.time())

    # ---------- gestures ----------
    def handle(self, lm):
        now = time.time()
        size = dist(lm[0], lm[9]) or 0.1
        ratio = dist(lm[4], lm[8]) / size
        pinch = ratio < (PINCH_OFF if self.pinching else PINCH_ON)
        pinch_started = pinch and not self.pinching
        self.pinching = pinch

        # cursor from the index fingertip, mirrored
        nx = np.clip(((1 - lm[8].x) - MARGIN_X) / (1 - 2 * MARGIN_X), 0, 1)
        ny = np.clip((lm[8].y - MARGIN_Y) / (1 - 2 * MARGIN_Y - 0.1), 0, 1)
        k = SMOOTH_PINCH if pinch else SMOOTH_FREE
        self.cx += (nx - self.cx) * k
        self.cy += (ny - self.cy) * k

        # open palm held -> home
        if self.mode == "control" and is_open_palm(lm) and not pinch:
            self.palm_since = self.palm_since or now
            if now - self.palm_since > PALM_HOLD:
                self.palm_since = None
                self.go_home()
                return
        else:
            self.palm_since = None

        if self.mode == "home":
            if pinch_started:
                i = self.tile_at(self.cx * HOME_W, self.cy * HOME_H)
                if i is not None:
                    self.open_app(i)
            return

        if self.paused:
            return

        pyautogui.moveTo(self.cx * self.screen_w, self.cy * self.screen_h)
        if pinch_started:
            pyautogui.click()

        # swipe on the wrist
        self.wrist.append((now, lm[0].y))
        while self.wrist and now - self.wrist[0][0] > SWIPE_WINDOW:
            self.wrist.popleft()
        if not pinch and len(self.wrist) > 3 and now - self.last_swipe > SWIPE_COOLDOWN:
            dy = self.wrist[-1][1] - self.wrist[0][1]
            if abs(dy) > SWIPE_DIST:
                self.last_swipe = now
                self.wrist.clear()
                up = dy < 0
                if self.shorts:
                    pyautogui.press("down" if up else "up")
                else:
                    pyautogui.scroll(-600 if up else 600)
                self.say("Next" if up else "Previous")

    # ---------- drawing ----------
    def draw_home(self, cam):
        bg = cv2.resize(cam, (HOME_W, HOME_H))
        bg = (bg * 0.25).astype(np.uint8)
        cv2.putText(bg, time.strftime("%H:%M"), (HOME_W // 2 - 150, 200),
                    cv2.FONT_HERSHEY_DUPLEX, 3.5, (240, 240, 240), 4, cv2.LINE_AA)
        hover = self.tile_at(self.cx * HOME_W, self.cy * HOME_H)
        for i, ((tx, ty, w, h), (name, _, color, _)) in enumerate(zip(self.tiles, APPS)):
            grow = 12 if i == hover else 0
            cv2.rectangle(bg, (tx - grow, ty - grow), (tx + w + grow, ty + h + grow), color, -1)
            if i == hover:
                cv2.rectangle(bg, (tx - grow - 6, ty - grow - 6), (tx + w + grow + 6, ty + h + grow + 6),
                              (240, 201, 76), 4)
            (tw, _), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_DUPLEX, 1.1, 2)
            cv2.putText(bg, name, (tx + (w - tw) // 2, ty + h + 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1.1, (240, 240, 240), 2, cv2.LINE_AA)
        cv2.putText(bg, "Point with your index finger - pinch to open",
                    (HOME_W // 2 - 360, HOME_H - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (180, 180, 180), 2, cv2.LINE_AA)
        p = (int(self.cx * HOME_W), int(self.cy * HOME_H))
        col = (143, 93, 255) if self.pinching else (240, 201, 76)
        cv2.circle(bg, p, 14 if self.pinching else 24, col, -1 if self.pinching else 4, cv2.LINE_AA)
        return bg

    def overlay_status(self, img):
        text, t = self.flash
        if text and time.time() - t < 1.2:
            cv2.putText(img, text, (20, 50), cv2.FONT_HERSHEY_DUPLEX, 1.2, (91, 227, 155), 3, cv2.LINE_AA)
        if self.mode == "control":
            tag = ("PAUSED" if self.paused else "SHORTS" if self.shorts else "MOUSE")
            cv2.putText(img, tag, (20, img.shape[0] - 25), cv2.FONT_HERSHEY_DUPLEX, 1.2,
                        (240, 201, 76), 3, cv2.LINE_AA)
            if self.palm_since:
                frac = min(1, (time.time() - self.palm_since) / PALM_HOLD)
                cv2.ellipse(img, (img.shape[1] - 60, 60), (35, 35), -90, 0, 360 * frac,
                            (91, 227, 155), 8)

    # ---------- main loop ----------
    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        if not cap.isOpened():
            raise SystemExit("Camera not found. Check that no other app is using it.")
        cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN, HOME_W, HOME_H)
        cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

        draw = mp.solutions.drawing_utils
        hands_mod = mp.solutions.hands
        with hands_mod.Hands(max_num_hands=1, model_complexity=1,
                             min_detection_confidence=0.6, min_tracking_confidence=0.5) as hands:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)  # mirror for display
                res = hands.process(cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB))
                if res.multi_hand_landmarks:
                    lm = res.multi_hand_landmarks[0].landmark
                    self.handle(lm)
                    shown = res.multi_hand_landmarks[0]
                    # draw on the mirrored preview
                    mirrored = type(shown)()
                    mirrored.CopyFrom(shown)
                    for p in mirrored.landmark:
                        p.x = 1 - p.x
                    draw.draw_landmarks(frame, mirrored, hands_mod.HAND_CONNECTIONS)
                else:
                    self.pinching = False
                    self.palm_since = None

                img = self.draw_home(frame) if self.mode == "home" else frame
                self.overlay_status(img)
                cv2.imshow(WIN, img)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("h"):
                    self.go_home()
                if key == ord("s"):
                    self.shorts = not self.shorts
                    self.say("Shorts mode " + ("on" if self.shorts else "off"))
                if key == ord("p"):
                    self.paused = not self.paused
                    self.say("Paused" if self.paused else "Resumed")
                if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                    break
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    AirTouch().run()
