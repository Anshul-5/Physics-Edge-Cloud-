#!/bin/bash -eu
mkdir -p build-fuzz
cd build-fuzz
cmake ../edge/test/fuzz -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" -DCMAKE_CXX_FLAGS="$CXXFLAGS" -DLIB_FUZZING_ENGINE="$LIB_FUZZING_ENGINE"
make -j4
cp fuzz_* "$OUT/"
