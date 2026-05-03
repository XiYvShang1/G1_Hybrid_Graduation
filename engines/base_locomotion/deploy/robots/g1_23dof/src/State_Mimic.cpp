#include "State_Mimic.h"
#include "unitree_articulation.h"
#include "isaaclab/envs/mdp/observations/observations.h"
#include "isaaclab/envs/mdp/actions/joint_actions.h"

static Eigen::Quaternionf init_quat;
std::shared_ptr<State_Mimic::MotionLoader_> State_Mimic::motion = nullptr;


Eigen::Quaternionf robot_quat_w(isaaclab::ManagerBasedRLEnv* env)
{
    using G1Type = unitree::BaseArticulation<LowState_t::SharedPtr>;
    G1Type* robot = dynamic_cast<G1Type*>(env->robot.get());

    auto root_quat = env->robot->data.root_quat_w;
    auto & motors = robot->lowstate->msg_.motor_state();

    Eigen::Quaternionf torso_quat = root_quat \
        * Eigen::AngleAxisf(motors[12].q(), Eigen::Vector3f::UnitZ());


//    return root_quat;
    return torso_quat;
}

Eigen::Quaternionf motion_anchor_quat_w(std::shared_ptr<State_Mimic::MotionLoader_> loader)
{
    const auto root_quat = loader->root_quaternion();
    const auto joint_pos = loader->joint_pos();
    Eigen::Quaternionf torso_quat = root_quat \
        * Eigen::AngleAxisf(joint_pos[12], Eigen::Vector3f::UnitZ());


//    return root_quat;
    return torso_quat;
}


namespace isaaclab
{
namespace mdp
{

REGISTER_OBSERVATION(motion_command)
{
    auto loader = State_Mimic::motion;
    std::vector<float> data;

    auto motion_joint_pos = loader->joint_pos();
    auto motion_joint_vel = loader->joint_vel();

    data.insert(data.end(),
                motion_joint_pos.data(),
                motion_joint_pos.data() + motion_joint_pos.size());
    data.insert(data.end(),
                motion_joint_vel.data(),
                motion_joint_vel.data() + motion_joint_vel.size());
    return data;
}

REGISTER_OBSERVATION(motion_anchor_ori_b)
{
    auto loader = State_Mimic::motion;
    std::vector<float> out;

    auto real_quat_w = robot_quat_w(env);
    auto ref_quat_w  = motion_anchor_quat_w(loader);

    auto rot_ = (init_quat * ref_quat_w).conjugate() * real_quat_w;
    auto rot = rot_.toRotationMatrix().transpose();

    Eigen::Matrix<float, 6, 1> data;
    data << rot(0, 0), rot(0, 1), rot(1, 0), rot(1, 1), rot(2, 0), rot(2, 1);
    return std::vector<float>(data.data(), data.data() + data.size());
}

}
}


State_Mimic::State_Mimic(int state_mode, std::string state_string)
: FSMState(state_mode, state_string) 
{
    auto cfg = param::config["FSM"][state_string];
    auto policy_dir = param::parser_policy_dir(cfg["policy_dir"].as<std::string>());

    auto articulation = std::make_shared<unitree::BaseArticulation<LowState_t::SharedPtr>>(FSMState::lowstate);

    std::filesystem::path motion_file = cfg["motion_file"].as<std::string>();
    if(!motion_file.is_absolute()) {
        motion_file = param::proj_dir / motion_file;
    }

    // Motion
    motion_ = std::make_shared<MotionLoader_>(motion_file.string());
    spdlog::info("Loaded motion file '{}' with duration {:.2f}s", motion_file.stem().string(), motion_->duration);
    motion = motion_;
    if(cfg["time_start"]) {
        float time_start = cfg["time_start"].as<float>();
        time_range_[0] = std::clamp(time_start, 0.0f, motion_->duration);
    } else {
        time_range_[0] = 0.0f;
    }
    if(cfg["time_end"]) {
        float time_end = cfg["time_end"].as<float>();
        time_range_[1] = std::clamp(time_end, 0.0f, motion_->duration);
    } else {
        time_range_[1] = motion_->duration;
    }
    std::string end_state = "Velocity";
    if (cfg["end_state"]) {
        end_state = cfg["end_state"].as<std::string>();
    }

    env = std::make_unique<isaaclab::ManagerBasedRLEnv>(
        YAML::LoadFile(policy_dir / "params" / "deploy.yaml"),
        articulation
    );
    env->alg = std::make_unique<isaaclab::OrtRunner>(policy_dir / "exported" / "policy.onnx");

    auto hard_limit_cfg = cfg["safety_hard_limit"];
    if (hard_limit_cfg && hard_limit_cfg["enabled"] && hard_limit_cfg["enabled"].as<bool>())
    {
        safety_hard_joint_min_ = hard_limit_cfg["min"].as<std::vector<float>>();
        safety_hard_joint_max_ = hard_limit_cfg["max"].as<std::vector<float>>();
        safety_hard_limit_enabled_ =
            !safety_hard_joint_min_.empty() &&
            safety_hard_joint_min_.size() == safety_hard_joint_max_.size();

        if (!safety_hard_limit_enabled_) {
            spdlog::warn("[SAFETY][{}] safety_hard_limit is enabled but min/max is invalid", state_string);
        } else {
            spdlog::info(
                "[SAFETY][{}] hard limit damping fallback enabled with {} joints",
                state_string,
                safety_hard_joint_min_.size()
            );
            this->registered_checks.emplace_back(
                std::make_pair(
                    [&]()->bool{ return safety_hard_limit_triggered_; },
                    FSMStringMap.right.at("Passive")
                )
            );
        }
    }

    this->registered_checks.emplace_back(
        std::make_pair(
            [&]()->bool{ return (env->episode_length * env->step_dt) > time_range_[1]; }, // time out
            FSMStringMap.right.at(end_state)
        )
    );
    this->registered_checks.emplace_back(
        std::make_pair(
            [&]()->bool{ return isaaclab::mdp::bad_orientation(env.get(), 1.0); }, // bad orientation
            FSMStringMap.right.at("Passive")
        )
    );
}

void State_Mimic::enter()
{
    safety_hard_limit_triggered_ = false;
    has_valid_action_ = false;

    // set gain
    for (int i = 0; i < env->robot->data.joint_stiffness.size(); i++)
    {
        lowcmd->msg_.motor_cmd()[i].kp() = env->robot->data.joint_stiffness[i];
        lowcmd->msg_.motor_cmd()[i].kd() = env->robot->data.joint_damping[i];
        lowcmd->msg_.motor_cmd()[i].dq() = 0;
        lowcmd->msg_.motor_cmd()[i].tau() = 0;
    }

    hold_action_.assign(env->robot->data.joint_ids_map.size(), 0.0f);
    {
        std::lock_guard<std::mutex> lock(action_mutex_);
        latest_action_.assign(env->robot->data.joint_ids_map.size(), 0.0f);
        for (size_t i = 0; i < hold_action_.size(); ++i) {
            const int motor_idx = env->robot->data.joint_ids_map[i];
            const float q = lowstate->msg_.motor_state()[motor_idx].q();
            hold_action_[i] = q;
            latest_action_[i] = q;
        }
    }

    motion = motion_; // set for specific motion
    env->reset();
    // Start policy thread
    policy_thread_running = true;
    policy_thread = std::thread([this]{
        using clock = std::chrono::high_resolution_clock;
        const std::chrono::duration<double> desiredDuration(env->step_dt);
        const auto dt = std::chrono::duration_cast<clock::duration>(desiredDuration);

        // Initialize timing
        const auto start = clock::now();
        auto sleepTill = start + dt;

        motion->reset(env->robot->data, time_range_[0]);
        auto ref_yaw = isaaclab::yawQuaternion(motion->root_quaternion()).toRotationMatrix();
        auto robot_yaw = isaaclab::yawQuaternion(robot_quat_w(env.get())).toRotationMatrix();
        init_quat = robot_yaw * ref_yaw.transpose();
        env->reset();

        while (policy_thread_running)
        {
            env->robot->update();
            motion->update(env->episode_length * env->step_dt + time_range_[0]);
            env->step();

            auto action = env->action_manager->processed_actions();
            {
                std::lock_guard<std::mutex> lock(action_mutex_);
                latest_action_ = action;
            }
            has_valid_action_ = true;

            // Sleep
            std::this_thread::sleep_until(sleepTill);
            sleepTill += dt;
        }
    });
}


void State_Mimic::run()
{
    if (!has_valid_action_) {
        hold_current_pose();
        return;
    }

    std::vector<float> action;
    {
        std::lock_guard<std::mutex> lock(action_mutex_);
        action = latest_action_;
    }

    if (safety_hard_limit_enabled_ && !is_action_within_hard_limits(action)) {
        safety_hard_limit_triggered_ = true;
        hold_current_pose();
        return;
    }

    for(int i(0); i < env->robot->data.joint_ids_map.size(); i++) {
        const int motor_idx = env->robot->data.joint_ids_map[i];
        lowcmd->msg_.motor_cmd()[motor_idx].q() = action[i];
    }
}

bool State_Mimic::is_action_within_hard_limits(const std::vector<float>& action)
{
    const auto dof_size = env->robot->data.joint_ids_map.size();
    if (action.size() != dof_size || safety_hard_joint_min_.size() != dof_size) {
        spdlog::error(
            "[SAFETY][{}] hard limit size mismatch: action={}, joint_ids={}, limit={}",
            getStateString(), action.size(), dof_size, safety_hard_joint_min_.size()
        );
        return false;
    }

    for (size_t i = 0; i < dof_size; ++i) {
        const float q_des = action[i];
        if (q_des < safety_hard_joint_min_[i] || q_des > safety_hard_joint_max_[i]) {
            const int motor_id = env->robot->data.joint_ids_map[i];
            spdlog::error(
                "[SAFETY][{}] HARD LIMIT joint {} (motor {}) target out of limit: {:.3f} not in [{:.3f}, {:.3f}]",
                getStateString(), i, motor_id, q_des, safety_hard_joint_min_[i], safety_hard_joint_max_[i]
            );
            return false;
        }
    }

    return true;
}

void State_Mimic::hold_current_pose()
{
    for (size_t i = 0; i < hold_action_.size(); ++i) {
        const int motor_idx = env->robot->data.joint_ids_map[i];
        lowcmd->msg_.motor_cmd()[motor_idx].q() = hold_action_[i];
    }
}
