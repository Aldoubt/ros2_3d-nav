#include "LIVMapper.h"

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions options;
  options.allow_undeclared_parameters(true);
  options.automatically_declare_parameters_from_overrides(true);
  auto bootstrap_node = std::make_shared<rclcpp::Node>("fastlivo_bootstrap");
  rclcpp::Node::SharedPtr nh = bootstrap_node;
  image_transport::ImageTransport it_(bootstrap_node);
  LIVMapper mapper(nh, "laserMapping", options);
  mapper.initializeSubscribersAndPublishers(nh, it_);
  mapper.run(nh);
  rclcpp::shutdown();
  return 0;
}
