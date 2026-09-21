cmake_minimum_required(VERSION 3.16)
project(P5AgentLifecycleTests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Core Network Test)
if(NOT P5_SOURCE_DIR)
  message(FATAL_ERROR "Set P5_SOURCE_DIR to the fully reconstructed P5 source")
endif()
set(AGENT_DIR "${P5_SOURCE_DIR}/src/aiassistant")
add_executable(agent-lifecycle-test
  agent_lifecycle_test.cpp
  "${AGENT_DIR}/openaicompatibleagent.cpp"
  "${AGENT_DIR}/openaicompatibleagent.h"
  "${AGENT_DIR}/agenttoolregistry.cpp"
  "${AGENT_DIR}/agenttoolregistry.h")
target_include_directories(agent-lifecycle-test PRIVATE "${AGENT_DIR}")
target_link_libraries(agent-lifecycle-test PRIVATE Qt6::Core Qt6::Network Qt6::Test)
enable_testing()
add_test(NAME agent-lifecycle COMMAND agent-lifecycle-test)
set_tests_properties(agent-lifecycle PROPERTIES TIMEOUT 30)
