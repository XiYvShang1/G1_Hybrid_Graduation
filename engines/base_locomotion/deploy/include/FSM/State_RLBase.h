// Copyright (c) 2025, Unitree Robotics Co., Ltd.
// All rights reserved.

#pragma once

#include "FSMState.h"
#include "isaaclab/envs/mdp/actions/joint_actions.h"
#include "isaaclab/envs/mdp/terminations.h"
#include <atomic>
#include <mutex>

class State_RLBase : public FSMState
{
public:
    State_RLBase(int state_mode, std::string state_string);

    void enter()
    {
        safety_hard_limit_triggered_ = false;
        has_valid_action_ = false;

        // set gain
        for (int i = 0; i < env->robot->data.joint_stiffness.size(); ++i)
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

        env->robot->update();
        policy_thread_running = true;
        policy_thread = std::thread([this]{
            using clock = std::chrono::high_resolution_clock;
            const std::chrono::duration<double> desiredDuration(env->step_dt);
            const auto dt = std::chrono::duration_cast<clock::duration>(desiredDuration);

            auto sleepTill = clock::now() + dt;
            env->reset();

            while (policy_thread_running)
            {
                env->step();
                {
                    std::lock_guard<std::mutex> lock(action_mutex_);
                    latest_action_ = env->action_manager->processed_actions();
                }
                has_valid_action_ = true;

                std::this_thread::sleep_until(sleepTill);
                sleepTill += dt;
            }
        });
    }

    void run();

    void exit()
    {
        policy_thread_running = false;
        if (policy_thread.joinable()) {
            policy_thread.join();
        }
    }

private:
    bool is_action_within_hard_limits(const std::vector<float>& action);
    void hold_current_pose();

    std::unique_ptr<isaaclab::ManagerBasedRLEnv> env;

    std::mutex action_mutex_;
    std::vector<float> latest_action_;
    std::vector<float> hold_action_;
    std::atomic<bool> has_valid_action_{false};

    std::vector<float> safety_hard_joint_min_;
    std::vector<float> safety_hard_joint_max_;
    bool safety_hard_limit_enabled_ = false;
    bool safety_hard_limit_triggered_ = false;

    std::thread policy_thread;
    std::atomic<bool> policy_thread_running{false};
};

REGISTER_FSM(State_RLBase)
