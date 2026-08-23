cmake_minimum_required(VERSION 3.16)
project(PhysEdgeFuzzers C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_C_STANDARD 11)

include_directories(
    /../../components/secure_ota/include
    /../../components/downscaler/include
    /../../components/optical_flow/include
    /../../components/uplink_buffer/include
)

if(NOT DEFINED LIB_FUZZING_ENGINE OR LIB_FUZZING_ENGINE STREQUAL "")
    set(FUZZER_FLAG "-fsanitize=fuzzer")
else()
    set(FUZZER_FLAG "")
endif()

add_executable(fuzz_secure_ota
    fuzz_secure_ota.cpp
    ../../components/secure_ota/secure_ota.cpp
)
target_link_libraries(fuzz_secure_ota PRIVATE  crypto ssl)

add_executable(fuzz_downscaler
    fuzz_downscaler.cpp
    ../../components/downscaler/downscaler.cpp
)
target_link_libraries(fuzz_downscaler PRIVATE )

add_executable(fuzz_optical_flow
    fuzz_optical_flow.cpp
    ../../components/optical_flow/optical_flow.cpp
)
target_link_libraries(fuzz_optical_flow PRIVATE )

add_executable(fuzz_uplink_buffer
    fuzz_uplink_buffer.cpp
    ../../components/uplink_buffer/uplink_buffer.cpp
)
target_link_libraries(fuzz_uplink_buffer PRIVATE )
