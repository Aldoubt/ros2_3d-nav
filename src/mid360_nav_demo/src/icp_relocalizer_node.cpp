#include <chrono>
#include <memory>
#include <mutex>
#include <string>

#include <Eigen/Geometry>
#include <pcl/common/transforms.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/io/pcd_io.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/registration/icp.h>
#include <pcl_conversions/pcl_conversions.h>

#include <geometry_msgs/msg/pose_with_covariance_stamped.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <std_msgs/msg/string.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Transform.h>
#include <tf2_ros/buffer.h>
#include <tf2_ros/static_transform_broadcaster.h>
#include <tf2_ros/transform_broadcaster.h>
#include <tf2_ros/transform_listener.h>

namespace
{
using PointT = pcl::PointXYZ;
using CloudT = pcl::PointCloud<PointT>;

Eigen::Matrix4f transformMsgToEigen(const geometry_msgs::msg::TransformStamped & msg)
{
  const auto & t = msg.transform.translation;
  const auto & q = msg.transform.rotation;
  Eigen::Quaternionf quat(
    static_cast<float>(q.w), static_cast<float>(q.x), static_cast<float>(q.y),
    static_cast<float>(q.z));
  quat.normalize();

  Eigen::Matrix4f out = Eigen::Matrix4f::Identity();
  out.block<3, 3>(0, 0) = quat.toRotationMatrix();
  out(0, 3) = static_cast<float>(t.x);
  out(1, 3) = static_cast<float>(t.y);
  out(2, 3) = static_cast<float>(t.z);
  return out;
}

Eigen::Matrix4f poseMsgToEigen(const geometry_msgs::msg::Pose & pose)
{
  Eigen::Quaternionf quat(
    static_cast<float>(pose.orientation.w), static_cast<float>(pose.orientation.x),
    static_cast<float>(pose.orientation.y), static_cast<float>(pose.orientation.z));
  quat.normalize();

  Eigen::Matrix4f out = Eigen::Matrix4f::Identity();
  out.block<3, 3>(0, 0) = quat.toRotationMatrix();
  out(0, 3) = static_cast<float>(pose.position.x);
  out(1, 3) = static_cast<float>(pose.position.y);
  out(2, 3) = static_cast<float>(pose.position.z);
  return out;
}

geometry_msgs::msg::TransformStamped eigenToTransformMsg(
  const Eigen::Matrix4f & transform, const rclcpp::Time & stamp,
  const std::string & parent_frame, const std::string & child_frame)
{
  Eigen::Matrix3f rotation = transform.block<3, 3>(0, 0);
  Eigen::Quaternionf quat(rotation);
  quat.normalize();

  geometry_msgs::msg::TransformStamped msg;
  msg.header.stamp = stamp;
  msg.header.frame_id = parent_frame;
  msg.child_frame_id = child_frame;
  msg.transform.translation.x = transform(0, 3);
  msg.transform.translation.y = transform(1, 3);
  msg.transform.translation.z = transform(2, 3);
  msg.transform.rotation.x = quat.x();
  msg.transform.rotation.y = quat.y();
  msg.transform.rotation.z = quat.z();
  msg.transform.rotation.w = quat.w();
  return msg;
}
}  // namespace

class IcpRelocalizerNode : public rclcpp::Node
{
public:
  IcpRelocalizerNode()
  : Node("icp_relocalizer_node"),
    tf_buffer_(this->get_clock()),
    tf_listener_(tf_buffer_)
  {
    global_map_pcd_ = declare_parameter<std::string>(
      "global_map_pcd",
      "/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_downsampled_points.pcd");
    global_frame_ = declare_parameter<std::string>("global_frame", "map");
    odom_frame_ = declare_parameter<std::string>("odom_frame", "odom");
    tracking_frame_ = declare_parameter<std::string>("tracking_frame", "livox_frame");
    cloud_topic_ = declare_parameter<std::string>("cloud_topic", "/cloud_registered");
    initialpose_topic_ = declare_parameter<std::string>("initialpose_topic", "/initialpose");
    max_correspondence_distance_ =
      declare_parameter<double>("max_correspondence_distance", 3.0);
    transformation_epsilon_ = declare_parameter<double>("transformation_epsilon", 1e-6);
    euclidean_fitness_epsilon_ =
      declare_parameter<double>("euclidean_fitness_epsilon", 1e-6);
    fitness_score_threshold_ = declare_parameter<double>("fitness_score_threshold", 2.0);
    map_voxel_leaf_size_ = declare_parameter<double>("map_voxel_leaf_size", 0.25);
    scan_voxel_leaf_size_ = declare_parameter<double>("scan_voxel_leaf_size", 0.25);
    min_scan_points_ = declare_parameter<int>("min_scan_points", 200);
    maximum_iterations_ = declare_parameter<int>("maximum_iterations", 100);
    publish_tf_ = declare_parameter<bool>("publish_tf", true);
    publish_aligned_cloud_ = declare_parameter<bool>("publish_aligned_cloud", true);

    if (!loadGlobalMap()) {
      RCLCPP_WARN(
        get_logger(),
        "Global PCD is not loaded yet. Set global_map_pcd and restart before using /initialpose.");
    }

    status_pub_ = create_publisher<std_msgs::msg::String>("/relocalization/status", 10);
    aligned_cloud_pub_ =
      create_publisher<sensor_msgs::msg::PointCloud2>("/relocalization/aligned_cloud", 10);
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    tf_timer_ = create_wall_timer(
      std::chrono::milliseconds(50), std::bind(&IcpRelocalizerNode::publishLatestTf, this));

    cloud_sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      cloud_topic_, rclcpp::SensorDataQoS(),
      std::bind(&IcpRelocalizerNode::cloudCallback, this, std::placeholders::_1));
    initialpose_sub_ = create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
      initialpose_topic_, 10,
      std::bind(&IcpRelocalizerNode::initialPoseCallback, this, std::placeholders::_1));

    RCLCPP_INFO(
      get_logger(),
      "ICP relocalizer ready. cloud_topic=%s initialpose_topic=%s global_map_pcd=%s",
      cloud_topic_.c_str(), initialpose_topic_.c_str(), global_map_pcd_.c_str());
  }

private:
  bool loadGlobalMap()
  {
    CloudT::Ptr raw_map(new CloudT);
    if (pcl::io::loadPCDFile<PointT>(global_map_pcd_, *raw_map) != 0) {
      publishStatus("failed: could not load global_map_pcd=" + global_map_pcd_);
      return false;
    }

    global_map_.reset(new CloudT);
    if (map_voxel_leaf_size_ > 0.0) {
      pcl::VoxelGrid<PointT> voxel;
      voxel.setLeafSize(map_voxel_leaf_size_, map_voxel_leaf_size_, map_voxel_leaf_size_);
      voxel.setInputCloud(raw_map);
      voxel.filter(*global_map_);
    } else {
      *global_map_ = *raw_map;
    }

    RCLCPP_INFO(
      get_logger(), "Loaded global map: raw=%zu filtered=%zu from %s", raw_map->size(),
      global_map_->size(), global_map_pcd_.c_str());
    return !global_map_->empty();
  }

  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    std::lock_guard<std::mutex> lock(cloud_mutex_);
    latest_cloud_msg_ = msg;
  }

  void initialPoseCallback(const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg)
  {
    if (!global_map_ || global_map_->empty()) {
      if (!loadGlobalMap()) {
        RCLCPP_ERROR(get_logger(), "Relocalization skipped because global map is unavailable.");
        return;
      }
    }

    sensor_msgs::msg::PointCloud2::SharedPtr cloud_msg;
    {
      std::lock_guard<std::mutex> lock(cloud_mutex_);
      cloud_msg = latest_cloud_msg_;
    }

    if (!cloud_msg) {
      publishStatus("failed: no latest cloud on " + cloud_topic_);
      RCLCPP_WARN(get_logger(), "No cloud has been received yet.");
      return;
    }

    CloudT::Ptr scan(new CloudT);
    pcl::fromROSMsg(*cloud_msg, *scan);
    if (scan_voxel_leaf_size_ > 0.0) {
      CloudT::Ptr filtered(new CloudT);
      pcl::VoxelGrid<PointT> voxel;
      voxel.setLeafSize(scan_voxel_leaf_size_, scan_voxel_leaf_size_, scan_voxel_leaf_size_);
      voxel.setInputCloud(scan);
      voxel.filter(*filtered);
      scan = filtered;
    }

    if (static_cast<int>(scan->size()) < min_scan_points_) {
      publishStatus("failed: scan has too few points");
      RCLCPP_WARN(get_logger(), "Scan has too few points: %zu", scan->size());
      return;
    }

    Eigen::Matrix4f initial_guess = poseMsgToEigen(msg->pose.pose);
    try {
      const auto odom_to_tracking_msg = tf_buffer_.lookupTransform(
        odom_frame_, tracking_frame_, tf2::TimePointZero, std::chrono::milliseconds(200));
      const Eigen::Matrix4f odom_to_tracking = transformMsgToEigen(odom_to_tracking_msg);
      initial_guess = poseMsgToEigen(msg->pose.pose) * odom_to_tracking.inverse();
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN(
        get_logger(),
        "Could not lookup %s -> %s. Using /initialpose directly as map->odom guess: %s",
        odom_frame_.c_str(), tracking_frame_.c_str(), ex.what());
    }

    pcl::IterativeClosestPoint<PointT, PointT> icp;
    icp.setInputSource(scan);
    icp.setInputTarget(global_map_);
    icp.setMaxCorrespondenceDistance(max_correspondence_distance_);
    icp.setTransformationEpsilon(transformation_epsilon_);
    icp.setEuclideanFitnessEpsilon(euclidean_fitness_epsilon_);
    icp.setMaximumIterations(maximum_iterations_);

    CloudT aligned;
    icp.align(aligned, initial_guess);
    const double fitness = icp.getFitnessScore();

    if (!icp.hasConverged() || fitness > fitness_score_threshold_) {
      publishStatus(
        "failed: converged=" + std::string(icp.hasConverged() ? "true" : "false") +
        " fitness=" + std::to_string(fitness));
      RCLCPP_WARN(
        get_logger(), "ICP relocalization failed. converged=%d fitness=%.4f threshold=%.4f",
        icp.hasConverged(), fitness, fitness_score_threshold_);
      return;
    }

    const Eigen::Matrix4f map_to_odom = icp.getFinalTransformation();
    const auto stamp = now();
    if (publish_tf_) {
      {
        std::lock_guard<std::mutex> lock(tf_mutex_);
        latest_map_to_odom_ = map_to_odom;
        has_latest_tf_ = true;
      }
      tf_broadcaster_->sendTransform(
        eigenToTransformMsg(map_to_odom, stamp, global_frame_, odom_frame_));
    }

    if (publish_aligned_cloud_) {
      sensor_msgs::msg::PointCloud2 aligned_msg;
      pcl::toROSMsg(aligned, aligned_msg);
      aligned_msg.header.stamp = stamp;
      aligned_msg.header.frame_id = global_frame_;
      aligned_cloud_pub_->publish(aligned_msg);
    }

    publishStatus("success: fitness=" + std::to_string(fitness));
    RCLCPP_INFO(get_logger(), "ICP relocalization succeeded. fitness=%.4f", fitness);
  }

  void publishStatus(const std::string & text)
  {
    if (!status_pub_) {
      return;
    }
    std_msgs::msg::String msg;
    msg.data = text;
    status_pub_->publish(msg);
  }

  void publishLatestTf()
  {
    if (!publish_tf_) {
      return;
    }

    Eigen::Matrix4f map_to_odom;
    {
      std::lock_guard<std::mutex> lock(tf_mutex_);
      if (!has_latest_tf_) {
        return;
      }
      map_to_odom = latest_map_to_odom_;
    }

    tf_broadcaster_->sendTransform(
      eigenToTransformMsg(map_to_odom, now(), global_frame_, odom_frame_));
  }

  std::string global_map_pcd_;
  std::string global_frame_;
  std::string odom_frame_;
  std::string tracking_frame_;
  std::string cloud_topic_;
  std::string initialpose_topic_;
  double max_correspondence_distance_;
  double transformation_epsilon_;
  double euclidean_fitness_epsilon_;
  double fitness_score_threshold_;
  double map_voxel_leaf_size_;
  double scan_voxel_leaf_size_;
  int min_scan_points_;
  int maximum_iterations_;
  bool publish_tf_;
  bool publish_aligned_cloud_;

  CloudT::Ptr global_map_;
  sensor_msgs::msg::PointCloud2::SharedPtr latest_cloud_msg_;
  std::mutex cloud_mutex_;
  Eigen::Matrix4f latest_map_to_odom_{Eigen::Matrix4f::Identity()};
  bool has_latest_tf_{false};
  std::mutex tf_mutex_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  rclcpp::TimerBase::SharedPtr tf_timer_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr aligned_cloud_pub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr initialpose_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<IcpRelocalizerNode>());
  rclcpp::shutdown();
  return 0;
}
