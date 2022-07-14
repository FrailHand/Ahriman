from math import floor
from time import time

import numpy


class Animator:
    def __init__(self, value, setter, frequency=60):
        self.setter = setter
        self.type = type(value)
        self._value = numpy.array(value)
        self.active = False
        self.on_end = None

        self.trajectory = []
        self.freq = frequency
        self.current_time = None

    @property
    def value(self):
        return self.type(self._value)

    @value.setter
    def value(self, value):
        self.active = False
        self._value = numpy.array(value)
        self.type = type(value)
        self.setter(value)

    def update(self):
        if self.active:
            temp = floor(time() * self.freq)
            if temp != self.current_time:
                delta = int(temp - self.current_time)
                self.current_time = temp

                for _ in range(delta):
                    next_value = self.trajectory.pop(0)
                    self._value = next_value
                    out_value = self.type(next_value)
                    self.setter(out_value)
                    if len(self.trajectory) == 0:
                        self.active = False
                        if self.on_end is not None:
                            self.on_end()
                        break

        return self.active

    def set_path(self, trajectory):
        self.current_time = floor(time() * self.freq)
        self.trajectory = list(trajectory)
        self.active = True

    def parabolic(self, total_duration, transition_duration, target, relative=False, start=None, on_end=None):
        if start is None:
            start = self._value
        target = numpy.array(target)
        if relative:
            if len(self.trajectory) > 0:
                target = self.trajectory[-1] + target
            else:
                target = start + target

        delta = target - start

        duration = total_duration - 2 * transition_duration
        if duration < 0:
            duration = 0

        acceleration = delta / (duration * transition_duration + transition_duration ** 2)

        time_vector = numpy.arange(0, transition_duration, 1 / self.freq)[:, None]

        transition = acceleration * (numpy.power(time_vector, 2)) / 2

        linear_start = start + transition[-1]
        linear_stop = target - transition[-1]
        linear_steps = int(floor(duration * self.freq))

        linear_path = [numpy.linspace(linear_start[dim], linear_stop[dim], linear_steps)[:, None] for dim in
                       range(len(start))]
        linear_trajectory = numpy.concatenate(linear_path, axis=-1)

        start_transition = start + transition
        end_transition = target - transition[::-1]

        trajectory = numpy.concatenate((start_transition, linear_trajectory, end_transition), axis=0)
        self.set_path(trajectory)
        self.on_end = on_end
