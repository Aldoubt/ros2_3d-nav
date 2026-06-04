#include <chrono>
#include <cmath>
#include <memory>
#include <string>

#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_srvs/srv/trigger.hpp>

using namespace std::chrono_literals;

namespace
{

bool isZeroTwist(const geometry_msgs::msg::Twist & msg)
{
  constexpr double kEpsilon = 1e-6;
  return std::fabs(msg.linear.x) < kEpsilon &&
         std::fabs(msg.linear.y) < kEpsilon &&
         std::fabs(msg.linear.z) < kEpsilon &&
         std::fabs(msg.angular.x) < kEpsilon &&
         std::fabs(msg.angular.y) < kEpsilon &&
         std::fabs(msg.angular.z) < kEpsilon;
}

geometry_msgs::msg::Twist makeZeroTwist()
{
  return geometry_msgs::msg::Twist();
}

}  // namespace

class SafetyGuardNode : public rclcpp::Node
{
public:
  SafetyGuardNode()
  : Node("safety_guard_node"),
    estop_active_(declare_parameter<bool>("default_estop_active", false)),
    obstacle_stop_active_(false),
    manual_enable_(declare_parameter<bool>("default_manual_enable", false)),
    auto_enable_(declare_parameter<bool>("default_auto_enable", true)),
    cmd_vel_timeout_sec_(declare_parameter<double>("cmd_vel_timeout_sec", 0.5))
  {
    manual_cmd_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/agt/cmd_vel_manual", rclcpp::QoS(10),
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
        manual_cmd_ = *msg;
        last_manual_cmd_time_ = now();
      });

    auto_cmd_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/agt/cmd_vel_nav", rclcpp::QoS(10),
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
        auto_cmd_ = *msg;
        last_auto_cmd_time_ = now();
      });

    obstacle_stop_sub_ = create_subscription<std_msgs::msg::Bool>(
      "/agt/obstacle_stop", rclcpp::QoS(10).reliable(),
      [this](const std_msgs::msg::Bool::SharedPtr msg) {
        obstacle_stop_active_ = msg->data;
      });

    manual_enable_sub_ = create_subscription<std_msgs::msg::Bool>(
      "/agt/manual_enable", rclcpp::QoS(10).reliable(),
      [this](const std_msgs::msg::Bool::SharedPtr msg) {
        manual_enable_ = msg->data;
      });

    auto_enable_sub_ = create_subscription<std_msgs::msg::Bool>(
      "/agt/auto_enable", rclcpp::QoS(10).reliable(),
      [this](const std_msgs::msg::Bool::SharedPtr msg) {
        auto_enable_ = msg->data;
      });

    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>("/cmd_vel_safe", rclcpp::QoS(10));

    set_estop_srv_ = create_service<std_srvs::srv::Trigger>(
      "/agt/set_estop",
      [this](
        const std::shared_ptr<std_srvs::srv::Trigger::Request>,
        std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
        estop_active_ = true;
        response->success = true;
        response->message = "Emergency stop set";
        RCLCPP_WARN(get_logger(), "Emergency stop activated by service request.");
      });

    clear_estop_srv_ = create_service<std_srvs::srv::Trigger>(
      "/agt/clear_estop",
      [this](
        const std::shared_ptr<std_srvs::srv::Trigger::Request>,
        std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
        estop_active_ = false;
        response->success = true;
        response->message = "Emergency stop cleared";
        RCLCPP_INFO(get_logger(), "Emergency stop cleared by service request.");
      });

    publish_timer_ = create_wall_timer(50ms, [this]() { publishSafeCommand(); });

    RCLCPP_INFO(
      get_logger(),
      "safety_guard_node started. timeout=%.3f s, default_manual_enable=%s default_auto_enable=%s "
      "priority: estop > obstacle_stop > manual > auto > zero",
      cmd_vel_timeout_sec_,
      manual_enable_ ? "true" : "false",
      auto_enable_ ? "true" : "false");
  }

private:
  bool commandIsFresh(const rclcpp::Time & stamp) const
  {
    if (stamp.nanoseconds() == 0) {
      return false;
    }
    return (now() - stamp).seconds() <= cmd_vel_timeout_sec_;
  }

  void publishSafeCommand()
  {
    std::string reason = "zero";
    geometry_msgs::msg::Twist output = makeZeroTwist();

    if (estop_active_) {
      reason = "estop";
    } else if (obstacle_stop_active_) {
      reason = "obstacle_stop";
    } else if (manual_enable_ && commandIsFresh(last_manual_cmd_time_)) {
      output = manual_cmd_;
      reason = "manual";
    } else if (auto_enable_ && commandIsFresh(last_auto_cmd_time_)) {
      output = auto_cmd_;
      reason = "auto";
    }

    cmd_pub_->publish(output);

    if (reason != last_reason_ || isZeroTwist(output) != last_output_zero_) {
      RCLCPP_INFO(
        get_logger(),
        "Publishing /cmd_vel_safe from source=%s manual_enable=%s auto_enable=%s obstacle_stop=%s estop=%s",
        reason.c_str(),
        manual_enable_ ? "true" : "false",
        auto_enable_ ? "true" : "false",
        obstacle_stop_active_ ? "true" : "false",
        estop_active_ ? "true" : "false");
      last_reason_ = reason;
      last_output_zero_ = isZeroTwist(output);
    }
  }

  geometry_msgs::msg::Twist manual_cmd_;
  geometry_msgs::msg::Twist auto_cmd_;
  rclcpp::Time last_manual_cmd_time_;
  rclcpp::Time last_auto_cmd_time_;

  bool estop_active_;
  bool obstacle_stop_active_;
  bool manual_enable_;
  bool auto_enable_;
  bool last_output_zero_{true};
  double cmd_vel_timeout_sec_;
  std::string last_reason_{"zero"};

  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr manual_cmd_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr auto_cmd_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr obstacle_stop_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr manual_enable_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr auto_enable_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr set_estop_srv_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr clear_estop_srv_;
  rclcpp::TimerBase::SharedPtr publish_timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SafetyGuardNode>());
  rclcpp::shutdown();
  return 0;
}
