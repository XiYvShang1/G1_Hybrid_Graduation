import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.absolute()))

import os
import time

import hydra
import mujoco
import numpy as np
import viser
from viser import uplot
from omegaconf import DictConfig

from common.ctrlcomp import FSMCommand, PolicyOutput, StateAndCmd
from common.path_config import PROJECT_ROOT
from common.utils import get_gravity_orientation
from FSM.FSM import FSM, STATE_LABELS


STATE_GRAPH = """```text
LOCO -> Dance / KungFu / Kick / ASAP / KungFu2
Skill -> Cooldown -> LOCO
Safety: Passive / Default Pose / StandUp
```"""


def print_render_backend_info():
    """Print render-related environment so demo machines can be checked quickly."""
    mujoco_gl = os.environ.get("MUJOCO_GL", "<unset>")
    adapter = os.environ.get("MESA_D3D12_DEFAULT_ADAPTER_NAME", "<unset>")
    glx_vendor = os.environ.get("__GLX_VENDOR_LIBRARY_NAME", "<unset>")
    print(f"[渲染] MUJOCO_GL={mujoco_gl}")
    print(f"[渲染] MESA_D3D12_DEFAULT_ADAPTER_NAME={adapter}")
    print(f"[渲染] __GLX_VENDOR_LIBRARY_NAME={glx_vendor}")


def geom_color(name: str | None) -> tuple[int, int, int]:
    """按身体区域给 mesh 上色，避免浏览器里只有单调灰白模型。"""
    name = name or ""
    if "torso" in name or "pelvis" in name or "waist" in name:
        return (62, 86, 110)
    if "left" in name and ("shoulder" in name or "elbow" in name or "wrist" in name or "hand" in name):
        return (47, 132, 212)
    if "right" in name and ("shoulder" in name or "elbow" in name or "wrist" in name or "hand" in name):
        return (224, 104, 67)
    if "hip" in name or "knee" in name or "ankle" in name:
        return (70, 166, 119)
    if "head" in name:
        return (34, 38, 42)
    return (202, 188, 146)


def body_or_geom_name(model: mujoco.MjModel, geom_id: int) -> str:
    """优先使用 body 名称给视觉分区，geom 名称为空时也能正确着色。"""
    geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or ""
    body_id = int(model.geom_bodyid[geom_id])
    body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id) or ""
    return f"{body_name} {geom_name}".lower()


class LivePlotPanel:
    """Viser uPlot 没有原地改数据接口，因此定期重建小图表。"""

    def __init__(self, server: viser.ViserServer, capacity: int = 180):
        self.server = server
        self.capacity = capacity
        self.t: list[float] = []
        self.q0: list[float] = []
        self.q0_des: list[float] = []
        self.action_norm: list[float] = []
        self.tau_norm: list[float] = []
        self.vel_x: list[float] = []
        self.vel_yaw: list[float] = []
        self.q_plot = None
        self.norm_plot = None
        self.cmd_plot = None

    def append(
        self,
        timestamp: float,
        q: np.ndarray,
        q_des: np.ndarray,
        tau: np.ndarray,
        vel_cmd: np.ndarray,
    ):
        self.t.append(timestamp)
        self.q0.append(float(q[0]))
        self.q0_des.append(float(q_des[0]))
        self.action_norm.append(float(np.linalg.norm(q_des)))
        self.tau_norm.append(float(np.linalg.norm(tau)))
        self.vel_x.append(float(vel_cmd[0]))
        self.vel_yaw.append(float(vel_cmd[2]))

        for values in (
            self.t,
            self.q0,
            self.q0_des,
            self.action_norm,
            self.tau_norm,
            self.vel_x,
            self.vel_yaw,
        ):
            del values[:-self.capacity]

    def redraw(self):
        if len(self.t) < 2:
            return
        for handle in (self.q_plot, self.norm_plot, self.cmd_plot):
            if handle is not None:
                handle.remove()

        x = np.asarray(self.t, dtype=np.float32)
        self.q_plot = self.server.gui.add_uplot(
            (x, np.asarray(self.q0), np.asarray(self.q0_des)),
            (
                {"label": "t"},
                {"label": "q[0]", "stroke": "#2f80ed", "width": 2},
                {"label": "q_des[0]", "stroke": "#eb5757", "width": 2},
            ),
            title="Joint Tracking",
            aspect=1.8,
        )
        self.norm_plot = self.server.gui.add_uplot(
            (x, np.asarray(self.action_norm), np.asarray(self.tau_norm)),
            (
                {"label": "t"},
                {"label": "|q_des|", "stroke": "#9b51e0", "width": 2},
                {"label": "|tau|", "stroke": "#f2c94c", "width": 2},
            ),
            title="Policy Output",
            aspect=1.8,
        )
        self.cmd_plot = self.server.gui.add_uplot(
            (x, np.asarray(self.vel_x), np.asarray(self.vel_yaw)),
            (
                {"label": "t"},
                {"label": "vx", "stroke": "#27ae60", "width": 2},
                {"label": "yaw", "stroke": "#f2994a", "width": 2},
            ),
            title="Command",
            aspect=1.8,
        )


def pd_control(target_q, q, kp, target_dq, dq, kd):
    """用关节位置目标和 PD 增益计算 MuJoCo actuator torque。"""
    return (target_q - q) * kp + (target_dq - dq) * kd


def mat_to_wxyz(mat: np.ndarray) -> np.ndarray:
    """把 MuJoCo 的 3x3 旋转矩阵转换成 Viser 使用的 wxyz 四元数。"""
    rot = np.asarray(mat, dtype=np.float64).reshape(3, 3)
    trace = np.trace(rot)
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        return np.array(
            [
                0.25 * s,
                (rot[2, 1] - rot[1, 2]) / s,
                (rot[0, 2] - rot[2, 0]) / s,
                (rot[1, 0] - rot[0, 1]) / s,
            ]
        )

    axis = int(np.argmax(np.diag(rot)))
    if axis == 0:
        s = np.sqrt(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2]) * 2.0
        quat = np.array(
            [
                (rot[2, 1] - rot[1, 2]) / s,
                0.25 * s,
                (rot[0, 1] + rot[1, 0]) / s,
                (rot[0, 2] + rot[2, 0]) / s,
            ]
        )
    elif axis == 1:
        s = np.sqrt(1.0 + rot[1, 1] - rot[0, 0] - rot[2, 2]) * 2.0
        quat = np.array(
            [
                (rot[0, 2] - rot[2, 0]) / s,
                (rot[0, 1] + rot[1, 0]) / s,
                0.25 * s,
                (rot[1, 2] + rot[2, 1]) / s,
            ]
        )
    else:
        s = np.sqrt(1.0 + rot[2, 2] - rot[0, 0] - rot[1, 1]) * 2.0
        quat = np.array(
            [
                (rot[1, 0] - rot[0, 1]) / s,
                (rot[0, 2] + rot[2, 0]) / s,
                (rot[1, 2] + rot[2, 1]) / s,
                0.25 * s,
            ]
        )
    return quat / np.linalg.norm(quat)


class ViserMujocoScene:
    """把 MuJoCo robot mesh 同步到 Viser 浏览器场景。"""

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData, port: int):
        self.model = model
        self.data = data
        self.server = viser.ViserServer(port=port, label="G1 Mimic Skill")
        self.server.scene.set_up_direction("+z")
        self.server.scene.add_light_ambient("/lights/ambient", intensity=0.7)
        self.server.scene.add_light_directional(
            "/lights/key",
            color=(255, 248, 230),
            intensity=1.6,
            position=(3.0, -4.0, 5.0),
        )
        self.server.scene.add_grid(
            "/ground",
            width=12.0,
            height=12.0,
            cell_size=0.25,
            section_size=1.0,
            plane="xy",
            cell_color=(210, 210, 210),
            section_color=(145, 145, 145),
        )
        self.handles = self._add_robot_meshes()
        self.markers = self._add_body_markers()

    def _add_robot_meshes(self):
        handles = {}
        mesh_type = int(mujoco.mjtGeom.mjGEOM_MESH)
        for geom_id in range(self.model.ngeom):
            if int(self.model.geom_type[geom_id]) != mesh_type:
                continue
            mesh_id = int(self.model.geom_dataid[geom_id])
            vert_adr = int(self.model.mesh_vertadr[mesh_id])
            vert_num = int(self.model.mesh_vertnum[mesh_id])
            face_adr = int(self.model.mesh_faceadr[mesh_id])
            face_num = int(self.model.mesh_facenum[mesh_id])
            vertices = self.model.mesh_vert[vert_adr : vert_adr + vert_num].copy()
            faces = self.model.mesh_face[face_adr : face_adr + face_num].copy()
            name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
            visual_name = body_or_geom_name(self.model, geom_id)
            handle = self.server.scene.add_mesh_simple(
                f"/robot/{geom_id:03d}_{name or 'geom'}",
                vertices=vertices,
                faces=faces,
                color=geom_color(visual_name),
                flat_shading=True,
                material="standard",
                opacity=0.96,
                side="double",
                position=self.data.geom_xpos[geom_id],
                wxyz=mat_to_wxyz(self.data.geom_xmat[geom_id]),
            )
            handles[geom_id] = handle
        return handles

    def _add_body_markers(self):
        marker_specs = {
            "torso_link": (0.035, (255, 214, 102)),
            "pelvis": (0.03, (255, 214, 102)),
            "left_wrist_roll_link": (0.025, (64, 156, 255)),
            "right_wrist_roll_link": (0.025, (255, 122, 89)),
            "left_ankle_roll_link": (0.025, (76, 217, 145)),
            "right_ankle_roll_link": (0.025, (76, 217, 145)),
        }
        markers = {}
        for body_name, (radius, color) in marker_specs.items():
            body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, body_name)
            if body_id < 0:
                continue
            markers[body_id] = self.server.scene.add_icosphere(
                f"/markers/{body_name}",
                radius=radius,
                color=color,
                material="toon5",
                position=self.data.xpos[body_id],
            )
        return markers

    def update(self):
        for geom_id, handle in self.handles.items():
            handle.position = self.data.geom_xpos[geom_id]
            handle.wxyz = mat_to_wxyz(self.data.geom_xmat[geom_id])
        for body_id, handle in self.markers.items():
            handle.position = self.data.xpos[body_id]


@hydra.main(version_base=None, config_path="config", config_name="mujoco")
def main(cfg: DictConfig):
    xml_path = os.path.join(PROJECT_ROOT, cfg.xml_path)
    simulation_dt = float(cfg.simulation_dt)
    control_decimation = int(cfg.control_decimation)
    render_fps = float(cfg.get("render_fps", 30.0))
    viser_port = int(cfg.get("viser_port", 8080))
    tau_limit = np.array(cfg.tau_limit)

    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    model.opt.timestep = simulation_dt
    num_joints = model.nu
    display_num_joints = cfg.get("display_num_joints", num_joints)

    print("[系统] G1 Mimic Skill Viser 演示启动中...")
    print_render_backend_info()
    print(f"[系统] 展示关节数: {display_num_joints}")
    print(f"[系统] 底层 MuJoCo actuator 数: {num_joints}")
    print(f"[系统] 控制周期: {simulation_dt * control_decimation:.4f}s")

    policy_output_action = np.zeros(num_joints, dtype=np.float32)
    kps = np.zeros(num_joints, dtype=np.float32)
    kds = np.zeros(num_joints, dtype=np.float32)
    state_cmd = StateAndCmd(num_joints)
    policy_output = PolicyOutput(num_joints)
    fsm = FSM(state_cmd, policy_output)

    state_cmd.q = data.qpos[7:].copy()
    state_cmd.dq = data.qvel[6:].copy()
    state_cmd.gravity_ori = get_gravity_orientation(data.qpos[3:7]).copy()
    state_cmd.ang_vel = data.qvel[3:6].copy()
    state_cmd.vel_cmd[:] = 0.0
    fsm.cur_policy = fsm.loco_policy
    fsm.cur_policy.enter()
    fsm.cur_policy.run()
    policy_output_action = policy_output.actions.copy()
    kps = policy_output.kps.copy()
    kds = policy_output.kds.copy()
    print("[模式] 已自动进入 LOCO 平衡模式。")

    scene = ViserMujocoScene(model, data, viser_port)
    with scene.server.gui.add_folder("Info"):
        status = scene.server.gui.add_text("当前状态", STATE_LABELS[fsm.cur_policy.name], disabled=True)
        control_hz = 1.0 / (simulation_dt * control_decimation)
        scene.server.gui.add_text("控制频率", f"{control_hz:.1f} Hz", disabled=True)
        scene.server.gui.add_text("显示频率", f"{render_fps:.1f} FPS", disabled=True)
        step_text = scene.server.gui.add_text("Step", "0", disabled=True)
        q_text = scene.server.gui.add_text("q[0] / q_des[0]", "0.000 / 0.000", disabled=True)
        tau_text = scene.server.gui.add_text("|tau|", "0.000", disabled=True)
        scene.server.gui.add_markdown(STATE_GRAPH)

    with scene.server.gui.add_folder("Command"):
        speed_x = scene.server.gui.add_slider("前进速度 x", -1.0, 1.0, 0.05, 0.0)
        speed_yaw = scene.server.gui.add_slider("转向速度 yaw", -1.0, 1.0, 0.05, 0.0)
        running = scene.server.gui.add_checkbox("运行", True)

    def bind_button(label, command):
        button = scene.server.gui.add_button(label)

        @button.on_click
        def _(_event):
            state_cmd.skill_cmd = command

    with scene.server.gui.add_folder("Mimic Skill"):
        bind_button("LOCO 平衡", FSMCommand.LOCO)
        bind_button("Dance", FSMCommand.SKILL_1)
        bind_button("KungFu", FSMCommand.SKILL_2)
        bind_button("Kick", FSMCommand.SKILL_3)
        bind_button("ASAP", FSMCommand.SKILL_5)
        bind_button("KungFu2", FSMCommand.SKILL_4)

    with scene.server.gui.add_folder("Safety"):
        bind_button("StandUp", FSMCommand.STAND_UP)
        bind_button("Passive 阻尼", FSMCommand.PASSIVE)
        bind_button("默认姿态", FSMCommand.POS_RESET)

    with scene.server.gui.add_folder("Live Curves"):
        plots = LivePlotPanel(scene.server)

    render_dt = 1.0 / max(render_fps, 1.0)
    next_render = time.time()
    start_time = time.time()
    next_plot = time.time()
    tau = np.zeros(num_joints, dtype=np.float32)
    while True:
        step_start = time.time()
        if running.value:
            state_cmd.vel_cmd[0] = float(speed_x.value)
            state_cmd.vel_cmd[1] = 0.0
            state_cmd.vel_cmd[2] = float(speed_yaw.value)

            tau = pd_control(
                policy_output_action,
                data.qpos[7:],
                kps,
                np.zeros_like(kps),
                data.qvel[6:],
                kds,
            )
            data.ctrl[:] = np.clip(tau, -tau_limit, tau_limit)
            mujoco.mj_step(model, data)
            fsm.sim_counter += 1

            if fsm.sim_counter % control_decimation == 0:
                state_cmd.q = data.qpos[7:].copy()
                state_cmd.dq = data.qvel[6:].copy()
                state_cmd.gravity_ori = get_gravity_orientation(data.qpos[3:7]).copy()
                state_cmd.ang_vel = data.qvel[3:6].copy()
                fsm.run()
                status.value = STATE_LABELS[fsm.cur_policy.name]
                policy_output_action = policy_output.actions.copy()
                kps = policy_output.kps.copy()
                kds = policy_output.kds.copy()
                plots.append(
                    time.time() - start_time,
                    data.qpos[7:].copy(),
                    policy_output_action.copy(),
                    tau.copy(),
                    state_cmd.vel_cmd.copy(),
                )

        now = time.time()
        if now >= next_render:
            scene.update()
            step_text.value = str(fsm.sim_counter)
            q_text.value = f"{data.qpos[7]:+.3f} / {policy_output_action[0]:+.3f}"
            tau_text.value = f"{np.linalg.norm(tau):.3f}"
            next_render = now + render_dt
        if now >= next_plot:
            plots.redraw()
            next_plot = now + 0.5

        sleep_time = simulation_dt - (time.time() - step_start)
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()
