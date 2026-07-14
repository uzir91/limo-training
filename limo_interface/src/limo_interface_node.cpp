#include "limo_interface/limo_interface_node.hpp"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <limits>
#include <memory>
#include <sstream>
#include <vector>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"

namespace limo_interface
{

void LimoSystem::stateCallback(
    const std_msgs::msg::Float64::SharedPtr msg, std::string joint_name, int state) {
    if (hw_joints_.count(joint_name)) {
        auto& kv = hw_joints_[joint_name];
        if (state == 0) {
            kv.state_msg.position.data = kv.state_dir.position ? -msg->data : msg->data;
            kv.status.position = true;
            kv.now.position = node_->now();
        }
        else if (state == 1) {
            kv.state_msg.velocity.data = kv.state_dir.velocity ? -msg->data : msg->data;
            kv.status.velocity = true;
            kv.now.velocity = node_->now();
        }
        else if (state == 2) {
            kv.state_msg.effort.data = kv.state_dir.effort ? -msg->data : msg->data;
            kv.status.effort = true;
            kv.now.effort = node_->now();
        }
    }
}

void LimoSystem::timerCallback(
    std::string joint_name, int state) {
    if (hw_joints_.count(joint_name)) {
        auto& kv = hw_joints_[joint_name];
        if (state == 0) {
            if (kv.status.position) {
                if ((node_->now() - kv.now.position).seconds() > kv.timeout.position) {
                    kv.status.position = false;
                    // kv.state_msg.position.data = 0.0;
                }
            }
        }
        else if (state == 1) {
            if (kv.status.velocity) {
                if ((node_->now() - kv.now.velocity).seconds() > kv.timeout.velocity) {
                    kv.status.velocity = false;
                    kv.state_msg.velocity.data = 0.0;
                }
            }
        }
        else if (state == 2) {
            if (kv.status.effort) {
                if ((node_->now() - kv.now.effort).seconds() > kv.timeout.effort) {
                    kv.status.effort = false;
                    kv.state_msg.effort.data = 0.0;
                }
            }
        }
    }
}

hardware_interface::CallbackReturn LimoSystem::on_init(
    const hardware_interface::HardwareInfo & info)
{
    if (hardware_interface::SystemInterface::on_init(info) !=
            hardware_interface::CallbackReturn::SUCCESS)
    {
        return hardware_interface::CallbackReturn::ERROR;
    }
    logger_ = std::make_shared<rclcpp::Logger>(rclcpp::get_logger("limo_interface.LimoSystem"));
    clock_ = std::make_shared<rclcpp::Clock>(rclcpp::Clock());

    node_ = rclcpp::Node::make_shared("limo_interface_node");
    auto executor = std::make_shared<rclcpp::executors::MultiThreadedExecutor>();
    executor->add_node(node_);
    std::thread(
        [executor]() { 
            executor->spin(); 
        }).detach();

    // Init joints using the joint names from the URDF/hardware info
    for (const auto & joint : info_.joints)
    {
        // Add to hardware map, initial values zeroed
        hw_joints_[joint.name] = Joint(joint.name);

        hw_joints_[joint.name].timeout.position = getParam<double>(
            info_.hardware_parameters, joint.name + "_position_timeout", 1.0);
        hw_joints_[joint.name].timeout.velocity = getParam<double>(
            info_.hardware_parameters, joint.name + "_velocity_timeout", 1.0);
        hw_joints_[joint.name].timeout.effort = getParam<double>(
            info_.hardware_parameters, joint.name + "_effort_timeout", 1.0);

        hw_joints_[joint.name].state_dir.position = getParam<bool>(
            info_.hardware_parameters, joint.name + "_position_state_dir", false);
        hw_joints_[joint.name].state_dir.velocity = getParam<bool>(
            info_.hardware_parameters, joint.name + "_velocity_state_dir", false);
        hw_joints_[joint.name].state_dir.effort = getParam<bool>(
            info_.hardware_parameters, joint.name + "_effort_state_dir", false);

        hw_joints_[joint.name].command_dir.position = getParam<bool>(
            info_.hardware_parameters, joint.name + "_position_command_dir", false);
        hw_joints_[joint.name].command_dir.velocity = getParam<bool>(
            info_.hardware_parameters, joint.name + "_velocity_command_dir", false);
        hw_joints_[joint.name].command_dir.effort = getParam<bool>(
            info_.hardware_parameters, joint.name + "_effort_command_dir", false);

    }

    for (const auto & parameter : info_.hardware_parameters) {
        RCLCPP_INFO_STREAM(get_logger(), parameter.first << ": " << parameter.second);
    }

    return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface>
LimoSystem::export_state_interfaces()
{
    std::vector<hardware_interface::StateInterface> state_interfaces;
    for (auto & kv : hw_joints_)
    {
        state_interfaces.emplace_back(
            hardware_interface::StateInterface(
                kv.first, hardware_interface::HW_IF_POSITION, &kv.second.state.position));
        state_interfaces.emplace_back(
            hardware_interface::StateInterface(
                kv.first, hardware_interface::HW_IF_VELOCITY, &kv.second.state.velocity));
        state_interfaces.emplace_back(
            hardware_interface::StateInterface(
                kv.first, hardware_interface::HW_IF_EFFORT, &kv.second.state.effort));
    }
    return state_interfaces;
}

std::vector<hardware_interface::CommandInterface>
LimoSystem::export_command_interfaces()
{
    std::vector<hardware_interface::CommandInterface> command_interfaces;
    for (auto & kv : hw_joints_) {
        command_interfaces.emplace_back(
            hardware_interface::CommandInterface(
                kv.first, hardware_interface::HW_IF_POSITION, &kv.second.command.position));
        command_interfaces.emplace_back(
            hardware_interface::CommandInterface(
                kv.first, hardware_interface::HW_IF_VELOCITY, &kv.second.command.velocity));
        command_interfaces.emplace_back(
            hardware_interface::CommandInterface(
                kv.first, hardware_interface::HW_IF_EFFORT, &kv.second.command.effort));
    }
    return command_interfaces;
}

hardware_interface::CallbackReturn LimoSystem::on_activate(
    const rclcpp_lifecycle::State & /*previous_state*/)
{
    RCLCPP_INFO(get_logger(), "Activating LimoSystem ...");
    // Optionally initialize hardware, start communication threads, etc.

    // Zero all positions, velocities, commands
    for (auto & kv : hw_joints_)
    {
        // kv.second.state.position = 0.0;
        kv.second.state.velocity = 0.0;
        kv.second.state.effort = 0.0;
        // kv.second.command.position = 0.0;
        kv.second.command.velocity = 0.0;
        kv.second.command.effort = 0.0;

        // kv.second.state_msg.position.data = 0.0;
        kv.second.state_msg.velocity.data = 0.0;
        kv.second.state_msg.effort.data = 0.0;
        // kv.second.command_msg.position.data = 0.0;
        kv.second.command_msg.velocity.data = 0.0;
        kv.second.command_msg.effort.data = 0.0;

        kv.second.state_sub.velocity = node_->create_subscription<std_msgs::msg::Float64>(
            kv.first + "/state/velocity", 10,
            [this, joint_name=kv.first, state=1](const std_msgs::msg::Float64::SharedPtr msg) {
                this->stateCallback(msg, joint_name, state);
            }
        );
        kv.second.command_pub.velocity = node_->create_publisher<std_msgs::msg::Float64>(
            kv.first + "/command/velocity", 10
        );

        kv.second.timer.velocity = node_->create_wall_timer(
            std::chrono::milliseconds(1000 / 50),
            [this, joint_name=kv.first, state=1]() {
                this->timerCallback(joint_name, state);
            }
        );
    }

    // TODO: Start up ROS publishers/subscribers, connect to drivers, etc.

    return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn LimoSystem::on_deactivate(
    const rclcpp_lifecycle::State & /*previous_state*/)
{
    RCLCPP_INFO(get_logger(), "Deactivating LimoSystem ...");
    // TODO: Stop hardware safely

    // Zero all positions, velocities, commands
    for (auto & kv : hw_joints_)
    {
        kv.second.state_sub.velocity.reset();
        kv.second.command_pub.velocity.reset();
        kv.second.timer.velocity.reset();

        // kv.second.state.position = 0.0;
        kv.second.state.velocity = 0.0;
        kv.second.state.effort = 0.0;
        // kv.second.command.position = 0.0;
        kv.second.command.velocity = 0.0;
        kv.second.command.effort = 0.0;

        // kv.second.state_msg.position.data = 0.0;
        kv.second.state_msg.velocity.data = 0.0;
        kv.second.state_msg.effort.data = 0.0;
        // kv.second.command_msg.position.data = 0.0;
        kv.second.command_msg.velocity.data = 0.0;
        kv.second.command_msg.effort.data = 0.0;
    }

    return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::return_type LimoSystem::read(
    const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
{
    // TODO: Read feedback from your real/simulated motors (via ROS topic, CAN, serial, etc.)

    // Here, we just simulate: integrate velocity to position
    for (auto & kv : hw_joints_)
    {
        kv.second.state.position += kv.second.state_msg.velocity.data * period.seconds();
        kv.second.state.velocity = kv.second.state_msg.velocity.data;
        kv.second.state.effort = kv.second.state_msg.effort.data;

        // need wrap since the position is rotation
        kv.second.state.position = wrap_to_pi(kv.second.state.position);
    }

    return hardware_interface::return_type::OK;
}

hardware_interface::return_type LimoSystem::write(
    const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
    // TODO: Send velocity command (kv.second.command.velocity) to your motors via ROS pub, CAN, etc.

    // This is where you send the actual command to the actuators
    for (auto & kv : hw_joints_)
    {
        kv.second.command_msg.position.data = kv.second.command.position;
        kv.second.command_msg.velocity.data = kv.second.command.velocity;
        kv.second.command_msg.effort.data = kv.second.command.effort;
        
        kv.second.command_pub.velocity->publish(kv.second.command_msg.velocity);
    }
    return hardware_interface::return_type::OK;
}

}    // namespace limo_interface

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(
    limo_interface::LimoSystem, hardware_interface::SystemInterface)
