cmake_minimum_required(VERSION 3.20)

project(fastproto_example_bindings LANGUAGES CXX)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(
  _fastproto_example
  src/fastproto_example_bindings.cpp
)

target_compile_features(_fastproto_example PRIVATE cxx_std_20)

target_include_directories(
  _fastproto_example
  PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

install(TARGETS _fastproto_example LIBRARY DESTINATION fastproto_example_bindings)
