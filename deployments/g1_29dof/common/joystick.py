from common.path_config import PROJECT_ROOT

import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import pygame
except ModuleNotFoundError:
    pygame = None
from enum import IntEnum, unique


@unique
class JoystickButton(IntEnum):
    A = 0
    B = 1
    X = 2
    Y = 3
    L1 = 4
    R1 = 5
    SELECT = 6
    START = 7
    L3 = 8
    R3 = 9
    HOME = 10
    UP = 11
    DOWN = 12
    LEFT = 13
    RIGHT = 14


class JoyStick:
    def __init__(self):
        self.keyboard_mode = False
        if pygame is None:
            self.keyboard_mode = True
            self.joystick = None
            self.button_count = max([b.value for b in JoystickButton]) + 1
            self.axis_count = 4
            self.hat_count = 0
            print("[手柄] 未安装 pygame，已切换到 MuJoCo 键盘控制模式。")
            print("[手柄] 如需 Xbox/手柄输入，请安装 pygame；仅键盘演示不需要。")
            self._init_state_buffers()
            return

        pygame.init()
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()

        if joystick_count == 0:
            self.keyboard_mode = True
            self.joystick = None
            self.button_count = max([b.value for b in JoystickButton]) + 1
            self.axis_count = 4
            self.hat_count = 0
            print("[\u624b\u67c4] \u672a\u68c0\u6d4b\u5230\u624b\u67c4\uff0c\u5df2\u5207\u6362\u5230\u952e\u76d8\u6a21\u5f0f\u3002")
            print("[\u624b\u67c4] \u952e\u76d8\u8f93\u5165\u7531 MuJoCo \u7a97\u53e3\u56de\u8c03\u63a5\u7ba1\uff0c\u8bf7\u53c2\u8003\u542f\u52a8\u65e5\u5fd7\u4e2d\u7684\u6309\u952e\u8bf4\u660e\u3002")
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.button_count = self.joystick.get_numbuttons()
            self.axis_count = self.joystick.get_numaxes()
            self.hat_count = self.joystick.get_numhats()

        self._init_state_buffers()

    def _init_state_buffers(self):
        self.button_states = [False] * self.button_count
        self.button_pressed = [False] * self.button_count
        self.button_released = [False] * self.button_count
        self.axis_states = [0.0] * self.axis_count
        self.hat_states = [(0, 0)] * self.hat_count

    def update(self):
        """update joystick/keyboard state"""
        self.button_released = [False] * self.button_count

        if pygame is None:
            return

        pygame.event.pump()

        if self.keyboard_mode:
            keys = pygame.key.get_pressed()

            button_map = {
                JoystickButton.A: pygame.K_KP1,
                JoystickButton.B: pygame.K_KP3,
                JoystickButton.X: pygame.K_KP5,
                JoystickButton.Y: pygame.K_KP_MINUS,
                JoystickButton.L1: pygame.K_KP_PLUS,
                JoystickButton.R1: pygame.K_KP_PERIOD,
                JoystickButton.SELECT: pygame.K_KP0,
                JoystickButton.START: pygame.K_KP_ENTER,
            }

            current_states = [False] * self.button_count
            for btn, key in button_map.items():
                current_states[btn.value] = bool(keys[key])

            for i in range(self.button_count):
                if self.button_states[i] and not current_states[i]:
                    self.button_released[i] = True
                self.button_states[i] = current_states[i]

            axis = [0.0] * self.axis_count
            axis[0] = (1.0 if keys[pygame.K_KP6] else 0.0) - (1.0 if keys[pygame.K_KP4] else 0.0)
            axis[1] = (1.0 if keys[pygame.K_KP2] else 0.0) - (1.0 if keys[pygame.K_KP8] else 0.0)
            axis[3] = (1.0 if keys[pygame.K_KP9] else 0.0) - (1.0 if keys[pygame.K_KP7] else 0.0)
            self.axis_states = axis
            return

        for i in range(self.button_count):
            current_state = self.joystick.get_button(i) == 1
            if self.button_states[i] and not current_state:
                self.button_released[i] = True
            self.button_states[i] = current_state

        for i in range(self.axis_count):
            self.axis_states[i] = self.joystick.get_axis(i)

        for i in range(self.hat_count):
            self.hat_states[i] = self.joystick.get_hat(i)

    def is_button_pressed(self, button_id):
        if 0 <= button_id < self.button_count:
            return self.button_states[button_id]
        return False

    def is_button_released(self, button_id):
        if 0 <= button_id < self.button_count:
            return self.button_released[button_id]
        return False

    def get_axis_value(self, axis_id):
        if 0 <= axis_id < self.axis_count:
            return self.axis_states[axis_id]
        return 0.0

    def get_hat_direction(self, hat_id=0):
        if 0 <= hat_id < self.hat_count:
            return self.hat_states[hat_id]
        return (0, 0)
