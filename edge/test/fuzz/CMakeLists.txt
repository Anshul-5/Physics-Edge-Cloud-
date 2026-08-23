cmake_minimum_required(VERSION 3.16)
project(PhysEdgeFuzzers C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/secure_ota/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/downscaler/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/optical_flow/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/uplink_buffer/include
)

if(NOT DEFINED LIB_FUZZING_ENGINE OR LIB_FUZZING_ENGINE STREQUAL "")
    set(FUZZER_FLAG "-fsanitize=fuzzer")
else()
    set(FUZZER_FLAG "${LIB_FUZZING_ENGINE}")
endif()

add_executable(fuzz_secure_ota
    fuzz_secure_ota.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/secure_ota/secure_ota.cpp
)
target_link_libraries(fuzz_secure_ota PRIVATE ${FUZZER_FLAG} crypto ssl)

add_executable(fuzz_downscaler
    fuzz_downscaler.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/downscaler/downscaler.cpp
)
target_link_libraries(fuzz_downscaler PRIVATE ${FUZZER_FLAG})

add_executable(fuzz_optical_flow
    fuzz_optical_flow.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/optical_flow/optical_flow.cpp
)
target_link_libraries(fuzz_optical_flow PRIVATE ${FUZZER_FLAG})

add_executable(fuzz_uplink_buffer
    fuzz_uplink_buffer.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../../components/uplink_buffer/uplink_buffer.cpp
)
target_link_libraries(fuzz_uplink_buffer PRIVATE ${FUZZER_FLAG})
