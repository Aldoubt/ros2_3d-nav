#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/float32.hpp>

class ObstacleStopNode : public rclcpp::Node
{
public:
  ObstacleStopNode()
  : Node("obstacle_stop_node")
  {
    front_angle_deg_ = declare_parameter<double>("front_angle_deg", 30.0);
    stop_distance_m_ = declare_parameter<double>("stop_distance_m", 0.8);
    slow_distance_m_ = declare_parameter<double>("slow_distance_m", 1.5);
    min_valid_range_m_ = declare_parameter<double>("min_valid_range_m", 0.15);
    consecutive_stop_frames_ = declare_parameter<int>("consecutive_stop_frames", 2);
    consecutive_clear_frames_ = declare_parameter<int>("consecutive_clear_frames", 3);

    scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
      "/scan", rclcpp::SensorDataQoS(),
      std::bind(&ObstacleStopNode::onScan, this, std::placeholders::_1));

    obstacle_stop_pub_ = create_publisher<std_msgs::msg::Bool>("/agt/obstacle_stop", 10);
    obstacle_distance_pub_ =
      create_publisher<std_msgs::msg::Float32>("/agt/obstacle_distance", 10);

    RCLCPP_INFO(
      get_logger(),
      "obstacle_stop_node started. scan=/scan front_angle_deg=%.1f stop_distance=%.2f slow_distance=%.2f",
      front_angle_deg_, stop_distance_m_, slow_distance_m_);
  }

private:
  void onScan(const sensor_msgs::msg::LaserScan::SharedPtr msg)
  {
    const double half_window_rad = degreesToRadians(front_angle_deg_) * 0.5;
    float nearest_distance = std::numeric_limits<float>::infinity();

    for (size_t i = 0; i < msg->ranges.size(); ++i) {
      const double angle = static_cast<double>(msg->angle_min) +
        static_cast<double>(i) * static_cast<double>(msg->angle_increment);

      if (std::fabs(angle) > half_window_rad) {
        continue;
      }

      const float range = msg->ranges[i];
      if (!std::isfinite(range)) {
        continue;
      }
      if (range < min_valid_range_m_) {
        continue;
      }

      nearest_distance = std::min(nearest_distance, range);
    }

    const bool in_slow_zone = std::isfinite(nearest_distance) && nearest_distance <= slow_distance_m_;
    const bool stop_candidate = std::isfinite(nearest_distance) && nearest_distance <= stop_distance_m_;

    if (stop_candidate) {
      stop_frame_count_++;
      clear_frame_count_ = 0;
    } else {
      clear_frame_count_++;
      stop_frame_count_ = 0;
    }

    if (!obstacle_stop_active_ && stop_frame_count_ >= std::max(1, consecutive_stop_frames_)) {
      obstacle_stop_active_ = true;
    } else if (
      obstacle_stop_active_ &&
      clear_frame_count_ >= std::max(1, consecutive_clear_frames_))
    {
      obstacle_stop_active_ = false;
    }

    std_msgs::msg::Bool stop_msg;
    stop_msg.data = obstacle_stop_active_;
    obstacle_stop_pub_->publish(stop_msg);

    std_msgs::msg::Float32 distance_msg;
    distance_msg.data = in_slow_zone ? nearest_distance : std::numeric_limits<float>::infinity();
    obstacle_distance_pub_->publish(distance_msg);

    const std::string state =
      obstacle_stop_active_ ? "stop" : (in_slow_zone ? "slow" : "clear");
    if (state != last_state_) {
      if (std::isfinite(nearest_distance)) {
        RCLCPP_INFO(
          get_logger(),
          "Front obstacle state=%s nearest_distance=%.3f m stop_frames=%d clear_frames=%d",
          state.c_str(), nearest_distance, stop_frame_count_, clear_frame_count_);
      } else {
        RCLCPP_INFO(
          get_logger(),
          "Front obstacle state=%s nearest_distance=inf stop_frames=%d clear_frames=%d",
          state.c_str(), stop_frame_count_, clear_frame_count_);
      }
      last_state_ = state;
    }
  }

  static double degreesToRadians(const double degrees)
  {
    return degrees * M_PI / 180.0;
  }

  double front_angle_deg_{30.0};
  double stop_distance_m_{0.8};
  double slow_distance_m_{1.5};
  double min_valid_range_m_{0.15};
  int consecutive_stop_frames_{2};
  int consecutive_clear_frames_{3};
  int stop_frame_count_{0};
  int clear_frame_count_{0};
  bool obstacle_stop_active_{false};
  std::string last_state_{"init"};

  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr obstacle_stop_pub_;
  rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr obstacle_distance_pub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ObstacleStopNode>());
  rclcpp::shutdown();
  return 0;
}
