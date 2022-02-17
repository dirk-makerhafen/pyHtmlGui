import threading
import time
from pyhtmlgui import PyHtmlView
import random


class AnimationView(PyHtmlView):
    TEMPLATE_FILE = "animationView.html"

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.balls = []
        self._t = None
        self.add_balls(20)
        self._framerate = 0

    def get_framerate(self):
        return round(self._framerate)

    def nr_of_balls(self):
        return len(self.balls)

    def set_visible(self, visible):
        # overwrite set_visible to start animation if element gets visible
        super().set_visible(visible)
        if visible is True and self._t is None:
            self._t = threading.Thread(target=self._loop, daemon=True)
            self._t.start()

    def add_balls(self, nr_of_balls = 1):
        for i in range(nr_of_balls):
            self.balls.append(BallView(self.subject, self))
        if self.is_visible:
            self.update()

    def remove_ball(self):
        if any(self.balls):
            del self.balls[0]
            if self.is_visible:
                self.update()

    def _loop(self):
        last_ts_fr = time.time()
        while self.is_visible:
            start = time.time()
            for ball in self.balls:
                ball.move()
            diff = time.time() - start
            sleep_time = (1/40) - diff # target ~40 fps
            if sleep_time > 0:
                time.sleep(sleep_time)

            now = time.time()
            diff = now - last_ts_fr
            last_ts_fr = now
            framerate = ((self._framerate*20) + (1 / diff))/21
            if round(framerate) != round(self._framerate): # prevent redrawing the animation by using js directly to display current frame rate
                js = 'document.getElementById("framerate").innerHTML = args.framerate+"";'
                self.eval_javascript(js, skip_results=True, framerate=round(framerate))
            self._framerate = framerate
        self._t = None


class BallView(PyHtmlView):
    DOM_ELEMENT = "li"
    TEMPLATE_STR = 'o'

    def __init__(self, subject, parent, **kwargs):
        super().__init__(subject, parent, **kwargs)
        self.position_x = random.randint(0, 100)
        self.position_y = random.randint(0, 100)
        self.direction_x = random.choice([-random.random()*2, random.random()*2])
        self.direction_y = random.choice([-random.random()*2, random.random()*2])
        self.color = "%s" % "".join(random.choices("456789abcdef", k=3))

    @property
    def DOM_ELEMENT_EXTRAS(self):
        return "style='color:#%s;display:block;position:absolute;left:%s%%;top:%s%%'" % (self.color, self.position_x, self.position_y)

    def move(self):
        self.position_x += self.direction_x
        if self.position_x >= 100 or self.position_x <= 0:
            self.direction_x *= -1

        self.position_y += self.direction_y
        if self.position_y >= 100 or self.position_y <= 0:
            self.direction_y *= -1

        if self.is_visible:
            # fast frontend update via direct js call
            js = 'item = document.getElementById(args.uid);'
            js += 'item.style.left = args.posx + "%";'
            js += 'item.style.top  = args.posy + "%";'
            self.eval_javascript(js, skip_results=True, uid=self.uid, posx=self.position_x, posy=self.position_y)
            # or even faster on the browser side, without eval by writing the js function in advance, see static/js/app.js
            #self.call_javascript("update_balls",[self.uid, self.position_x, self.position_y], skip_results=True)
