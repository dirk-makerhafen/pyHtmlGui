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
        for i in range(10):
            self.add_ball()

    def set_visible(self, visible):
        # overwrite set_visible to start animation if element gets visible
        super().set_visible(visible)
        if visible is True and self._t is None:
            self._t = threading.Thread(target=self._loop, daemon=True)
            self._t.start()

    def add_ball(self):
        self.balls.append(BallView(self.subject, self))
        if self.is_visible:
            self.update()

    def remove_ball(self):
        if any(self.balls):
            del self.balls[0]
            if self.is_visible:
                self.update()

    def _loop(self):
        while self.is_visible:
            for ball in self.balls:
                ball.move()
            time.sleep(1 / 60)
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
