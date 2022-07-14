from pyglet.window import key

from ahriman.activities import Activity


class OverLayerActivity(Activity):
    def __init__(self, window, bg_activity):
        super().__init__(window)
        self.bg_activity = bg_activity

    def resume(self):
        self.delete_self()
        self.window.force_activity(self.bg_activity)

    def on_key_press(self, KEY, _MOD):
        if KEY == key.ESCAPE:
            self.resume()

    def event_handler(self, event):
        self.resume()
        self.bg_activity.event_handler(event)

    def draw(self):
        if self.bg_activity is not None:
            self.bg_activity.draw()

    def update(self, dt, bg=False):
        if self.bg_activity is not None:
            self.bg_activity.update(dt, bg=True)

    def delete_self(self):
        pass

    def delete(self):
        self.bg_activity.delete()
        self.delete_self()
