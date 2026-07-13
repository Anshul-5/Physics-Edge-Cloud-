# SPDX-License-Identifier: Apache-2.0
# PhysEdge-Cloud: L1 Edge Gate - ESP32-S3 Firmware

cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_SOURCE_DIR}/components"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(physedge_l1_gate)
