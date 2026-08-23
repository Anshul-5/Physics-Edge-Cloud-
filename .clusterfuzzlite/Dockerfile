FROM gcr.io/oss-fuzz-base/base-builder:v1
RUN apt-get update && apt-get install -y cmake make libssl-dev
COPY . /Physics-Edge-Cloud
WORKDIR /Physics-Edge-Cloud
COPY .clusterfuzzlite/build.sh /build.sh
