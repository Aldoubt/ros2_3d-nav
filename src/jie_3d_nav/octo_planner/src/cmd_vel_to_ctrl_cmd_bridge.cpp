#include <algorithm>
#include <cmath>
#include <memory>
#include <string>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"
#include "yhs_can_interfaces/msg/ctrl_cmd.hpp"
#include "yhs_can_interfaces/msg/io_cmd.hpp"

class CmdVelToCtrlCmdBridge : public rclcpp::Node
{
public:
  CmdVelToCtrlCmdBridge()
  : Node("cmd_vel_to_ctrl_cmd_bridge")
  {
    declare_parameter<std::string>("cmd_vel_topic", "/cmd_vel");
    declare_parameter<std::string>("ctrl_cmd_topic", "/ctrl_cmd");
    declare_parameter<std::string>("io_cmd_topic", "/io_cmd");
    declare_parameter<double>("wheel_base", 0.6);
    declare_parameter<double>("publish_rate", 20.0);
    declare_parameter<double>("cmd_timeout_sec", 0.5);
    declare_parameter<double>("max_speed_mps", 1.0);
    declare_parameter<double>("max_steering_deg", 30.0);
    declare_parameter<double>("min_speed_for_steering", 0.05);
    declare_parameter<int>("forward_gear", 4);
    declare_parameter<int>("reverse_gear", 2);
    declare_parameter<int>("neutral_gear", 3);
    declare_parameter<bool>("publish_io_cmd", true);
    declare_parameter<bool>("io_cmd_enable", true);
    declare_parameter<bool>("io_cmd_dis_charge", false);

    const auto cmd_vel_topic = get_parameter("cmd_vel_topic").as_string();
    const auto ctrl_cmd_topic = get_parameter("ctrl_cmd_topic").as_string();
    const auto io_cmd_topic = get_parameter("io_cmd_topic").as_string();
    const double publish_rate = std::max(1.0, get_parameter("publish_rate").as_double());

    cmd_vel_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      cmd_vel_topic,
      rclcpp::QoS(10).reliable(),
      std::bind(&CmdVelToCtrlCmdBridge::onCmdVel, this, std::placeholders::_1));
    ctrl_cmd_pub_ = create_publisher<yhs_can_interfaces::msg::CtrlCmd>(ctrl_cmd_topic, 10);
    io_cmd_pub_ = create_publisher<yhs_can_interfaces::msg::IoCmd>(io_cmd_topic, 10);

    const auto period = std::chrono::duration<double>(1.0 / publish_rate);
    publish_timer_ = create_wall_timer(
      std::chrono::duration_cast<std::chrono::milliseconds>(period),
      std::bind(&CmdVelToCtrlCmdBridge::onPublishTimer, this));

    last_cmd_time_ = now();
    RCLCPP_INFO(
      get_logger(),
      "cmd_vel_to_ctrl_cmd_bridge started. cmd_vel=%s ctrl_cmd=%s wheel_base=%.3f "
      "io_cmd=%s max_speed=%.3f max_steering_deg=%.1f",
      cmd_vel_topic.c_str(),
      ctrl_cmd_topic.c_str(),
      get_parameter("wheel_base").as_double(),
      io_cmd_topic.c_str(),
      get_parameter("max_speed_mps").as_double(),
      get_parameter("max_steering_deg").as_double());
  }

private:
  void onCmdVel(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    latest_cmd_vel_ = *msg;
    last_cmd_time_ = now();
    has_cmd_ = true;

    if (std::abs(msg->linear.y) > 1.0e-4) {
      RCLCPP_WARN_THROTTLE(
        get_logger(),
        *get_clock(),
        2000,
        "Received lateral velocity %.3f m/s, but ctrl_cmd only supports Ackermann-style "
        "forward velocity and steering. linear.y will be ignored.",
        msg->linear.y);
    }
  }

  void onPublishTimer()
  {
    if (!has_cmd_) {
      publishCtrlCmd(makeZeroCmd());
      return;
    }

    const double timeout_sec = get_parameter("cmd_timeout_sec").as_double();
    if ((now() - last_cmd_time_).seconds() > timeout_sec) {
      publishCtrlCmd(makeZeroCmd());
      return;
    }

    publishCtrlCmd(convertCmd(latest_cmd_vel_));
  }

  yhs_can_interfaces::msg::CtrlCmd convertCmd(const geometry_msgs::msg::Twist & twist) const
  {
    yhs_can_interfaces::msg::CtrlCmd cmd;

    const double max_speed = std::max(0.0, get_parameter("max_speed_mps").as_double());
    const double wheel_base = std::max(1.0e-6, get_parameter("wheel_base").as_double());
    const double min_speed_for_steering =
      std::max(1.0e-4, get_parameter("min_speed_for_steering").as_double());
    const double max_steering_deg =
      std::max(0.0, get_parameter("max_steering_deg").as_double());
    const double max_steering_rad = max_steering_deg * M_PI / 180.0;

    const double linear_x = std::clamp(static_cast<double>(twist.linear.x), -max_speed, max_speed);
    const double angular_z = static_cast<double>(twist.angular.z);
    const double steering_rad = std::clamp(
      std::atan2(wheel_base * angular_z, std::max(std::abs(linear_x), min_speed_for_steering)),
      -max_steering_rad,
      max_steering_rad);

    if (std::abs(linear_x) < 1.0e-4) {
      cmd.ctrl_cmd_gear = static_cast<std::uint8_t>(get_parameter("neutral_gear").as_int());
      cmd.ctrl_cmd_velocity = 0.0F;
    } else if (linear_x > 0.0) {
      cmd.ctrl_cmd_gear = static_cast<std::uint8_t>(get_parameter("forward_gear").as_int());
      cmd.ctrl_cmd_velocity = static_cast<float>(linear_x);
    } else {
      cmd.ctrl_cmd_gear = static_cast<std::uint8_t>(get_parameter("reverse_gear").as_int());
      cmd.ctrl_cmd_velocity = static_cast<float>(std::abs(linear_x));
    }

    cmd.ctrl_cmd_steering = static_cast<float>(steering_rad * 180.0 / M_PI);
    return cmd;
  }

  yhs_can_interfaces::msg::CtrlCmd makeZeroCmd() const
  {
    yhs_can_interfaces::msg::CtrlCmd cmd;
    cmd.ctrl_cmd_gear = static_cast<std::uint8_t>(get_parameter("neutral_gear").as_int());
    cmd.ctrl_cmd_velocity = 0.0F;
    cmd.ctrl_cmd_steering = 0.0F;
    return cmd;
  }

  void publishCtrlCmd(const yhs_can_interfaces::msg::CtrlCmd & cmd)
  {
    ctrl_cmd_pub_->publish(cmd);
    publishIoCmd();
  }

  void publishIoCmd()
  {
    if (!get_parameter("publish_io_cmd").as_bool()) {
      return;
    }

    yhs_can_interfaces::msg::IoCmd io_cmd;
    io_cmd.io_cmd_enable = get_parameter("io_cmd_enable").as_bool();
    io_cmd.io_cmd_dis_charge = get_parameter("io_cmd_dis_charge").as_bool();
    io_cmd_pub_->publish(io_cmd);
  }

  geometry_msgs::msg::Twist latest_cmd_vel_;
  rclcpp::Time last_cmd_time_;
  bool has_cmd_{false};
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Publisher<yhs_can_interfaces::msg::CtrlCmd>::SharedPtr ctrl_cmd_pub_;
  rclcpp::Publisher<yhs_can_interfaces::msg::IoCmd>::SharedPtr io_cmd_pub_;
  rclcpp::TimerBase::SharedPtr publish_timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CmdVelToCtrlCmdBridge>());
  rclcpp::shutdown();
  return 0;
}
