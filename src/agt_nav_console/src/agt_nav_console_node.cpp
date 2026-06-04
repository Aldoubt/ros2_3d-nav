#include "agt_nav_console/agt_nav_console_node.hpp"

#include <memory>

namespace agt_nav_console
{

AgtNavConsoleNode::AgtNavConsoleNode()
: rclcpp::Node("agt_nav_console")
{
  RCLCPP_INFO(
    get_logger(),
    "agt_nav_console node started. GUI, safety arbitration, e-stop, and navigation bridging are placeholders for now.");
}

}  // namespace agt_nav_console

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<agt_nav_console::AgtNavConsoleNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
