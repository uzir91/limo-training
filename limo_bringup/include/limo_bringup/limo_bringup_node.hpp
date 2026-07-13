// Copyright 2024 Muhajir Mustapa
// SPDX-License-Identifier: Apache-2.0

#ifndef LIMO_BRINGUP__LIMO_BRINGUP_NODE_HPP_
#define LIMO_BRINGUP__LIMO_BRINGUP_NODE_HPP_

#include <map>
#include <memory>
#include <string>
#include <vector>

#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/types/hardware_interface_return_values.hpp"
#include <rclcpp/rclcpp.hpp>
#include "rclcpp/logger.hpp"
#include "rclcpp/clock.hpp"
#include "rclcpp/time.hpp"
#include "rclcpp/duration.hpp"
#include "rclcpp_lifecycle/state.hpp"

#include <std_msgs/msg/float64.hpp>

namespace limo_bringup
{
    double wrap_to_pi(double angle)
    {
        angle = std::fmod(angle + M_PI, 2 * M_PI);
        if (angle < 0)
            angle += 2 * M_PI;
        return angle - M_PI;
    }

    // Optionally, store per-joint state and command
    struct JointValue
    {
        double position{0.0};
        double velocity{0.0};
        double effort{0.0};
    };

    struct JointBool
    {
        bool position{false};
        bool velocity{false};
        bool effort{false};
    };

    struct JointTime
    {
        rclcpp::Time position;
        rclcpp::Time velocity;
        rclcpp::Time effort;
    };

    struct JointSubscription
    {
        rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr position;
        rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr velocity;
        rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr effort;
    };

    struct JointPublisher
    {
        rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr position;
        rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr velocity;
        rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr effort;
    };

    struct JointTimer
    {
        rclcpp::TimerBase::SharedPtr position;
        rclcpp::TimerBase::SharedPtr velocity;
        rclcpp::TimerBase::SharedPtr effort;
    };

    struct JointMsg
    {
        std_msgs::msg::Float64 position;
        std_msgs::msg::Float64 velocity;
        std_msgs::msg::Float64 effort;
    };

    struct Joint
    {
        explicit Joint(const std::string & name) : joint_name(name) {}
        Joint() = default;

        std::string joint_name;
        JointValue state;
        JointValue command;

        JointSubscription state_sub;
        JointPublisher command_pub;

        JointMsg state_msg;
        JointMsg command_msg;

        JointValue timeout;
        JointBool state_dir;
        JointBool command_dir;

        JointBool status;
        JointTime now;
        JointTimer timer;
    };

    class LimoSystemHardware : public hardware_interface::SystemInterface
    {
        public:
            RCLCPP_SHARED_PTR_DEFINITIONS(LimoSystemHardware)

            void stateCallback(
                const std_msgs::msg::Float64::SharedPtr msg, std::string joint_name, int state);
            void timerCallback(
                std::string joint_name, int state);

            // Called once at startup, parses info (URDF, parameters, etc.)
            hardware_interface::CallbackReturn on_init(
                const hardware_interface::HardwareInfo & info) override;

            std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
            std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

            hardware_interface::CallbackReturn on_activate(
                const rclcpp_lifecycle::State & previous_state) override;
            hardware_interface::CallbackReturn on_deactivate(
                const rclcpp_lifecycle::State & previous_state) override;

            hardware_interface::return_type read(
                const rclcpp::Time & time, const rclcpp::Duration & period) override;
            hardware_interface::return_type write(
                const rclcpp::Time & time, const rclcpp::Duration & period) override;

            rclcpp::Logger get_logger() const { return *logger_; }
            rclcpp::Clock::SharedPtr get_clock() const { return clock_; }

        private:
            // Your robot hardware data members
            double hw_start_sec_{0.0};
            double hw_stop_sec_{0.0};

            std::shared_ptr<rclcpp::Logger> logger_;
            rclcpp::Clock::SharedPtr clock_;
            rclcpp::Node::SharedPtr node_;

            // Map from joint name to Joint
            std::map<std::string, Joint> hw_joints_;

            template<typename T>
            static T getParam(const std::unordered_map<std::string, std::string> &params, const std::string &key, const T &default_value)
            {
                auto it = params.find(key);
                if (it == params.end()) return default_value;

                std::istringstream iss(it->second);
                T value;
                if constexpr (std::is_same<T, bool>::value)
                {
                    std::string val = it->second;
                    return (val == "true" || val == "1");
                }
                else if constexpr (std::is_integral<T>::value && !std::is_same<T, bool>::value)
                {
                    iss >> value;
                    return iss.fail() ? default_value : value;
                }
                else if constexpr (std::is_floating_point<T>::value)
                {
                    iss >> value;
                    return iss.fail() ? default_value : value;
                }
                else if constexpr (std::is_same<T, std::string>::value)
                {
                    return it->second;
                }
                else
                {
                    return default_value;
                }
            }
    };

}  // namespace limo_bringup

#endif  // LIMO_BRINGUP__LIMO_BRINGUP_NODE_HPP_
