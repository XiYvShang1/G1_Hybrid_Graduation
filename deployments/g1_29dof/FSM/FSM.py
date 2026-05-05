from common.path_config import PROJECT_ROOT

from policy.passive.PassiveMode import PassiveMode
from policy.fixedpose.FixedPose import FixedPose
from policy.loco_mode.LocoMode import LocoMode
from policy.kungfu.KungFu import KungFu
from policy.dance.Dance import Dance
from policy.asap.asap import ASAP
from policy.host.host import HOST
from policy.skill_cooldown.SkillCooldown import SkillCooldown
from policy.skill_cast.SkillCast import SkillCast
from policy.kick.Kick import Kick
from policy.kungfu2.KungFu2 import KungFu2
from FSM.FSMState import *
import time
from common.ctrlcomp import *
from enum import Enum, unique

@unique
class FSMMode(Enum):
    CHANGE = 1
    NORMAL = 2

STATE_LABELS = {
    FSMStateName.PASSIVE: "PASSIVE",
    FSMStateName.FIXEDPOSE: "FIXED_POSE",
    FSMStateName.LOCOMODE: "LOCO",
    FSMStateName.SKILL_Dance: "DANCE",
    FSMStateName.SKILL_KungFu: "KUNGFU",
    FSMStateName.SKILL_KICK: "KICK",
    FSMStateName.SKILL_KungFu2: "KUNGFU2",
    FSMStateName.SKILL_ASAP: "ASAP",
    FSMStateName.SKILL_COOLDOWN: "COOLDOWN",
    FSMStateName.SKILL_CAST: "CAST",
    FSMStateName.STANDMODE: "STAND",
    FSMStateName.INVALID: "INVALID",
}

DEMO_STATES = {
    FSMStateName.SKILL_Dance,
    FSMStateName.SKILL_KungFu,
    FSMStateName.SKILL_KICK,
    FSMStateName.SKILL_KungFu2,
    FSMStateName.SKILL_ASAP,
}


class FSM:
    def __init__(self, state_cmd: StateAndCmd, policy_output: PolicyOutput):
        self.state_cmd = state_cmd
        self.policy_output = policy_output
        self.cur_policy: FSMState
        self.next_policy: FSMState
        self.sim_counter = 0
        self.FSMmode = FSMMode.NORMAL

        self.passive_mode = PassiveMode(state_cmd, policy_output)
        self.fixed_pose_1 = FixedPose(state_cmd, policy_output)
        self.loco_policy = LocoMode(state_cmd, policy_output)
        self.kungfu_policy = KungFu(state_cmd, policy_output)
        self.dance_policy = Dance(state_cmd, policy_output)
        self.skill_cooldown_policy = SkillCooldown(state_cmd, policy_output)
        self.skill_cast_policy = SkillCast(state_cmd, policy_output)
        self.kick_policy = Kick(state_cmd, policy_output)
        self.kungfu2_policy = KungFu2(state_cmd, policy_output)
        self.asap_policy = ASAP(state_cmd, policy_output)
        self.host_policy = HOST(state_cmd, policy_output)

        print("[\u7cfb\u7edf] \u7b56\u7565\u5df2\u52a0\u8f7d: \u884c\u8d70\u3001\u821e\u8e48\u3001\u6b66\u672f\u3001\u8e22\u817f\u3001ASAP\u3001KungFu2\u3001\u7ad9\u8d77")

        self.cur_policy = self.passive_mode
        print(f"[\u6a21\u5f0f] \u5f53\u524d\u6a21\u5f0f: {STATE_LABELS[self.cur_policy.name]}")

    def run(self):
        start_time = time.time()
        if self.FSMmode == FSMMode.NORMAL:
            self.cur_policy.run()
            nextPolicyName = self.cur_policy.checkChange()

            if nextPolicyName != self.cur_policy.name:
                from_state = self.cur_policy.name
                self.FSMmode = FSMMode.CHANGE
                self.cur_policy.exit()
                self.get_next_policy(nextPolicyName)
                to_state = self.cur_policy.name
                self._announce_transition(from_state, to_state)

        elif self.FSMmode == FSMMode.CHANGE:
            self.cur_policy.enter()
            self.sim_counter = 0
            self.FSMmode = FSMMode.NORMAL
            self.cur_policy.run()

        end_time = time.time()

    def absoluteWait(self, control_dt, start_time):
        end_time = time.time()
        delta_time = end_time - start_time
        if delta_time < control_dt:
            time.sleep(control_dt - delta_time)
        else:
            print("inference time beyond control horzion!!!")

    def _announce_transition(self, from_state: FSMStateName, to_state: FSMStateName):
        from_label = STATE_LABELS.get(from_state, str(from_state))
        to_label = STATE_LABELS.get(to_state, str(to_state))

        if from_state in DEMO_STATES and to_state == FSMStateName.SKILL_COOLDOWN:
            print(f"[\u6f14\u793a] {from_label} \u52a8\u4f5c\u5df2\u5b8c\u6210\uff0c\u8fdb\u5165\u51b7\u5374\u5e76\u51c6\u5907\u8fd4\u56de LOCO\u3002")
        elif from_state == FSMStateName.SKILL_COOLDOWN and to_state == FSMStateName.LOCOMODE:
            print("[\u6a21\u5f0f] \u51b7\u5374\u5b8c\u6210\uff0c\u5df2\u8fd4\u56de LOCO\u3002")
        elif to_state == FSMStateName.PASSIVE:
            print(f"[\u5b89\u5168] {from_label} -> \u963b\u5c3c\u4fdd\u62a4")
        elif to_state == FSMStateName.FIXEDPOSE:
            print(f"[\u6a21\u5f0f] {from_label} -> \u9ed8\u8ba4\u59ff\u6001")
        else:
            print(f"[\u6a21\u5f0f] {from_label} -> {to_label}")

    def get_next_policy(self, policy_name: FSMStateName):
        if policy_name == FSMStateName.PASSIVE:
            self.cur_policy = self.passive_mode
        elif policy_name == FSMStateName.FIXEDPOSE:
            self.cur_policy = self.fixed_pose_1
        elif policy_name == FSMStateName.LOCOMODE:
            self.cur_policy = self.loco_policy
        elif policy_name == FSMStateName.SKILL_KungFu:
            self.cur_policy = self.kungfu_policy
        elif policy_name == FSMStateName.SKILL_Dance:
            self.cur_policy = self.dance_policy
        elif policy_name == FSMStateName.SKILL_COOLDOWN:
            self.cur_policy = self.skill_cooldown_policy
        elif policy_name == FSMStateName.SKILL_CAST:
            self.cur_policy = self.skill_cast_policy
        elif policy_name == FSMStateName.SKILL_KICK:
            self.cur_policy = self.kick_policy
        elif policy_name == FSMStateName.SKILL_KungFu2:
            self.cur_policy = self.kungfu2_policy
        elif policy_name == FSMStateName.SKILL_ASAP:
            self.cur_policy = self.asap_policy
        elif policy_name == FSMStateName.STANDMODE:
            self.cur_policy = self.host_policy
