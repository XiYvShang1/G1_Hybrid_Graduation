from common.path_config import PROJECT_ROOT

from FSM.FSMState import FSMStateName, FSMState
from common.ctrlcomp import StateAndCmd, PolicyOutput
import numpy as np
import yaml
from common.utils import FSMCommand
import os

class FixedPose(FSMState):
    def __init__(self, state_cmd:StateAndCmd, policy_output:PolicyOutput):
        super().__init__()
        self.state_cmd = state_cmd
        self.policy_output = policy_output
        self.name = FSMStateName.FIXEDPOSE
        self.name_str = "fixed_pose"
        self.alpha = 0.
        self.cur_step = 0

        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "config", "FixedPose.yaml")
        with open(config_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            self.kds = np.array(config["kds"], dtype=np.float32)
            self.kps = np.array(config["kps"], dtype=np.float32)
            self.default_angles = np.array(config["default_angles"], dtype=np.float32)
            self.joint2motor_idx = np.array(config["joint2motor_idx"], dtype=np.int32)
            self.control_dt = config["control_dt"]

    def enter(self):
        print("[\u6a21\u5f0f] \u9ed8\u8ba4\u59ff\u6001: \u6b63\u5728\u56de\u5230\u521d\u59cb\u7ad9\u7acb\u59ff\u6001\u3002")
        self.total_time = 2.0
        self.num_step = int(self.total_time / self.control_dt)
        self.dof_size = len(self.joint2motor_idx)
        self.init_dof_pos = np.zeros(self.dof_size, dtype=np.float32)
        self.alpha = 0.
        self.cur_step = 0
        for i in range(self.dof_size):
            self.init_dof_pos[i] = self.state_cmd.q[self.joint2motor_idx[i]]

    def run(self):
        self.cur_step += 1
        self.alpha = min(self.cur_step / self.num_step, 1.0)
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            target_pos = self.default_angles[j]
            self.policy_output.actions[motor_idx] = self.init_dof_pos[j] * (1 - self.alpha) + target_pos * self.alpha
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]

    def exit(self):
        for j in range(self.dof_size):
            motor_idx = self.joint2motor_idx[j]
            self.policy_output.actions[motor_idx] = self.default_angles[j]
            self.policy_output.kps[motor_idx] = self.kps[j]
            self.policy_output.kds[motor_idx] = self.kds[j]

    def checkChange(self):
        cmd = self.state_cmd.skill_cmd

        if cmd == FSMCommand.PASSIVE:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.PASSIVE

        if self.cur_step < self.num_step:
            return FSMStateName.FIXEDPOSE

        if cmd == FSMCommand.LOCO:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.LOCOMODE
        elif cmd == FSMCommand.STAND_UP:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.STANDMODE
        elif cmd == FSMCommand.SKILL_1:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.SKILL_Dance
        elif cmd == FSMCommand.SKILL_2:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.SKILL_KungFu
        elif cmd == FSMCommand.SKILL_3:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.SKILL_KICK
        elif cmd == FSMCommand.SKILL_4:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.SKILL_KungFu2
        elif cmd == FSMCommand.SKILL_5:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.SKILL_ASAP
        else:
            self.state_cmd.skill_cmd = FSMCommand.INVALID
            return FSMStateName.FIXEDPOSE
