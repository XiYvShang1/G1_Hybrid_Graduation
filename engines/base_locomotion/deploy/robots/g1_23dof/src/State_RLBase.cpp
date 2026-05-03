#include "FSM/State_RLBase.h"
#include "unitree_articulation.h"
#include "isaaclab/envs/mdp/observations/observations.h"
#include "isaaclab/envs/mdp/actions/joint_actions.h"

State_RLBase::State_RLBase(int state_mode, std::string state_string)
: FSMState(state_mode, state_string)
{
    auto cfg = param::config["FSM"][state_string];
    auto policy_dir = param::parser_policy_dir(cfg["policy_dir"].as<std::string>());

    env = std::make_unique<isaaclab::ManagerBasedRLEnv>(
        YAML::LoadFile(policy_dir / "params" / "deploy.yaml"),
        std::make_shared<unitree::BaseArticulation<LowState_t::SharedPtr>>(FSMState::lowstate)
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
            [&]()->bool{ return isaaclab::mdp::bad_orientation(env.get(), 1.0); },
            FSMStringMap.right.at("Passive")
        )
    );
}

void State_RLBase::run()
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

bool State_RLBase::is_action_within_hard_limits(const std::vector<float>& action)
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
        const float q = action[i];
        if (q < safety_hard_joint_min_[i] || q > safety_hard_joint_max_[i]) {
            const int motor_idx = env->robot->data.joint_ids_map[i];
            spdlog::error(
                "[SAFETY][{}] HARD LIMIT joint {} (motor {}) target out of limit: {:.3f} not in [{:.3f}, {:.3f}]",
                getStateString(), i, motor_idx, q, safety_hard_joint_min_[i], safety_hard_joint_max_[i]
            );
            return false;
        }
    }

    return true;
}

void State_RLBase::hold_current_pose()
{
    if (hold_action_.empty()) {
        return;
    }

    for (size_t i = 0; i < hold_action_.size(); ++i) {
        const int motor_idx = env->robot->data.joint_ids_map[i];
        lowcmd->msg_.motor_cmd()[motor_idx].q() = hold_action_[i];
    }
}
