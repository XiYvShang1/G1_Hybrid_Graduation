import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from common.path_config import PROJECT_ROOT

import time
import mujoco.viewer
import mujoco
import numpy as np
import yaml
import os
from common.ctrlcomp import *
from FSM.FSM import *
from common.utils import get_gravity_orientation
from common.joystick import JoyStick, JoystickButton
from omegaconf import DictConfig
import hydra
import glfw


def pd_control(target_q, q, kp, target_dq, dq, kd):
    """Calculates torques from position commands"""
    return (target_q - q) * kp + (target_dq - dq) * kd


@hydra.main(version_base=None, config_path="config", config_name="mujoco")
def main(cfg: DictConfig):
    xml_path = os.path.join(PROJECT_ROOT, cfg.xml_path)
    simulation_dt = cfg.simulation_dt
    control_decimation = cfg.control_decimation
    tau_limit = np.array(cfg.tau_limit)

    m = mujoco.MjModel.from_xml_path(xml_path)
    d = mujoco.MjData(m)
    m.opt.timestep = simulation_dt
    mj_per_step_duration = simulation_dt * control_decimation
    num_joints = m.nu
    display_num_joints = cfg.get("display_num_joints", num_joints)
    print("[\u7cfb\u7edf] RoboMimicDeploy_G1 MuJoCo \u6f14\u793a\u542f\u52a8\u4e2d...")
    print(f"[\u7cfb\u7edf] \u673a\u5668\u4eba\u5173\u8282\u6570: {display_num_joints}")
    if display_num_joints != num_joints:
        print(f"[\u7cfb\u7edf] MuJoCo \u5e95\u5c42 actuator \u6570: {num_joints}")
    policy_output_action = np.zeros(num_joints, dtype=np.float32)
    kps = np.zeros(num_joints, dtype=np.float32)
    kds = np.zeros(num_joints, dtype=np.float32)

    state_cmd = StateAndCmd(num_joints)
    policy_output = PolicyOutput(num_joints)
    FSM_controller = FSM(state_cmd, policy_output)

    joystick = JoyStick()
    Running = True

    if joystick.keyboard_mode:
        print("[\u952e\u76d8\u63a7\u5236] \u5df2\u542f\u7528\u952e\u76d8\u6a21\u5f0f\uff0c\u7cfb\u7edf\u5c06\u81ea\u52a8\u8fdb\u5165 LOCO \u4fdd\u6301\u5e73\u8861\u3002")
        print("[\u952e\u76d8\u63a7\u5236] \u8bf7\u5148\u7528\u9f20\u6807\u70b9\u51fb MuJoCo \u7a97\u53e3\uff0c\u518d\u6309\u952e\u63a7\u5236\u3002")
        print("[\u952e\u76d8\u63a7\u5236] \u6309\u952e: Enter=\u9ed8\u8ba4\u59ff\u6001, .=\u963b\u5c3c\u4fdd\u62a4, 1=\u884c\u8d70, 2=\u821e\u8e48, 3=\u6b66\u672f, 4=\u8e22\u817f, 5=ASAP, 6=KungFu2, 7=\u7ad9\u8d77")
        print("[\u952e\u76d8\u63a7\u5236] \u901f\u5ea6: =/+ \u6216\u5c0f\u952e\u76d8+ \u524d\u8fdb\u52a0\u901f, - \u6216\u5c0f\u952e\u76d8- \u540e\u9000/\u51cf\u901f, Backspace \u6216\u5c0f\u952e\u76d8* \u901f\u5ea6\u6e05\u96f6")
        print("[\u952e\u76d8\u63a7\u5236] \u9000\u51fa: 0 \u6216\u5c0f\u952e\u76d80")

        state_cmd.q = d.qpos[7:].copy()
        state_cmd.dq = d.qvel[6:].copy()
        state_cmd.gravity_ori = get_gravity_orientation(d.qpos[3:7]).copy()
        state_cmd.ang_vel = d.qvel[3:6].copy()
        state_cmd.vel_cmd[:] = 0.0
        FSM_controller.cur_policy = FSM_controller.loco_policy
        FSM_controller.cur_policy.enter()
        FSM_controller.cur_policy.run()
        policy_output_action = policy_output.actions.copy()
        kps = policy_output.kps.copy()
        kds = policy_output.kds.copy()
        print("[\u6a21\u5f0f] \u5df2\u81ea\u52a8\u8fdb\u5165 LOCO \u5e73\u8861\u6a21\u5f0f\u3002")

    keyboard_vel = np.zeros(3, dtype=np.float32)
    keyboard_step = 0.15
    keyboard_decay = 0.96

    def keyboard_key_callback(keycode: int):
        nonlocal Running, keyboard_vel

        if not joystick.keyboard_mode:
            return

        if keycode in (glfw.KEY_KP_0, glfw.KEY_0):
            Running = False
            return
        if keycode in (glfw.KEY_KP_ENTER, glfw.KEY_ENTER):
            state_cmd.skill_cmd = FSMCommand.POS_RESET
            return
        if keycode in (glfw.KEY_KP_DECIMAL, glfw.KEY_PERIOD):
            state_cmd.skill_cmd = FSMCommand.PASSIVE
            return

        if keycode in (glfw.KEY_KP_1, glfw.KEY_1):
            state_cmd.skill_cmd = FSMCommand.LOCO
            return
        if keycode in (glfw.KEY_KP_2, glfw.KEY_2):
            state_cmd.skill_cmd = FSMCommand.SKILL_1
            return
        if keycode in (glfw.KEY_KP_3, glfw.KEY_3):
            state_cmd.skill_cmd = FSMCommand.SKILL_2
            return
        if keycode in (glfw.KEY_KP_4, glfw.KEY_4):
            state_cmd.skill_cmd = FSMCommand.SKILL_3
            return
        if keycode in (glfw.KEY_KP_5, glfw.KEY_5):
            state_cmd.skill_cmd = FSMCommand.SKILL_5
            return
        if keycode in (glfw.KEY_KP_6, glfw.KEY_6):
            state_cmd.skill_cmd = FSMCommand.SKILL_4
            return
        if keycode in (glfw.KEY_KP_7, glfw.KEY_7):
            state_cmd.skill_cmd = FSMCommand.STAND_UP
            return

        if keycode in (glfw.KEY_KP_ADD, glfw.KEY_EQUAL):
            keyboard_vel[0] += keyboard_step
        elif keycode in (glfw.KEY_KP_SUBTRACT, glfw.KEY_MINUS):
            keyboard_vel[0] -= keyboard_step
        elif keycode in (glfw.KEY_KP_MULTIPLY, glfw.KEY_BACKSPACE):
            keyboard_vel[:] = 0.0

        keyboard_vel = np.clip(keyboard_vel, -1.0, 1.0)

    with mujoco.viewer.launch_passive(m, d, key_callback=keyboard_key_callback) as viewer:
        while viewer.is_running() and Running:
            try:
                if joystick.keyboard_mode:
                    keyboard_vel *= keyboard_decay
                    keyboard_vel[np.abs(keyboard_vel) < 0.01] = 0.0
                    state_cmd.vel_cmd[0] = keyboard_vel[0]
                    state_cmd.vel_cmd[1] = keyboard_vel[1]
                    state_cmd.vel_cmd[2] = keyboard_vel[2]
                else:
                    if joystick.is_button_pressed(JoystickButton.SELECT):
                        Running = False

                    joystick.update()
                    if joystick.is_button_released(JoystickButton.L1) and joystick.is_button_pressed(JoystickButton.R1):
                        state_cmd.skill_cmd = FSMCommand.PASSIVE
                    if joystick.is_button_released(JoystickButton.START):
                        state_cmd.skill_cmd = FSMCommand.POS_RESET

                    if joystick.is_button_released(JoystickButton.X) and joystick.is_button_pressed(JoystickButton.L1):
                        state_cmd.skill_cmd = FSMCommand.STAND_UP

                    if joystick.is_button_released(JoystickButton.A) and joystick.is_button_pressed(JoystickButton.R1):
                        state_cmd.skill_cmd = FSMCommand.LOCO
                    elif joystick.is_button_released(JoystickButton.X) and joystick.is_button_pressed(JoystickButton.R1):
                        state_cmd.skill_cmd = FSMCommand.SKILL_1
                    elif joystick.is_button_released(JoystickButton.Y) and joystick.is_button_pressed(JoystickButton.R1):
                        state_cmd.skill_cmd = FSMCommand.SKILL_2
                    elif joystick.is_button_released(JoystickButton.B) and joystick.is_button_pressed(JoystickButton.R1):
                        state_cmd.skill_cmd = FSMCommand.SKILL_3
                    elif joystick.is_button_released(JoystickButton.Y) and joystick.is_button_pressed(JoystickButton.L1):
                        state_cmd.skill_cmd = FSMCommand.SKILL_4
                    elif joystick.is_button_released(JoystickButton.A) and joystick.is_button_pressed(JoystickButton.L1):
                        state_cmd.skill_cmd = FSMCommand.SKILL_5

                    state_cmd.vel_cmd[0] = -joystick.get_axis_value(1)
                    state_cmd.vel_cmd[1] = -joystick.get_axis_value(0)
                    state_cmd.vel_cmd[2] = -joystick.get_axis_value(3)

                step_start = time.time()
                tau = pd_control(policy_output_action, d.qpos[7:], kps, np.zeros_like(kps), d.qvel[6:], kds)
                tau = np.clip(tau, -tau_limit, tau_limit)
                d.ctrl[:] = tau
                mujoco.mj_step(m, d)
                FSM_controller.sim_counter += 1

                if FSM_controller.sim_counter % control_decimation == 0:
                    qj = d.qpos[7:]
                    dqj = d.qvel[6:]
                    quat = d.qpos[3:7]
                    omega = d.qvel[3:6]
                    gravity_orientation = get_gravity_orientation(quat)

                    state_cmd.q = qj.copy()
                    state_cmd.dq = dqj.copy()
                    state_cmd.gravity_ori = gravity_orientation.copy()
                    state_cmd.ang_vel = omega.copy()

                    FSM_controller.run()
                    policy_output_action = policy_output.actions.copy()
                    kps = policy_output.kps.copy()
                    kds = policy_output.kds.copy()

                viewer.sync()
                time_until_next_step = m.opt.timestep - (time.time() - step_start)
                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)
            except ValueError as e:
                print(str(e))


if __name__ == "__main__":
    main()
