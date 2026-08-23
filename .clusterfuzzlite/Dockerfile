FROM gcr.io/oss-fuzz-base/base-builder:v1
RUN apt-get update && apt-get install -y cmake make libssl-dev
COPY . /src/Physics-Edge-Cloud
WORKDIR /src/Physics-Edge-Cloud
COPY .clusterfuzzlite/build.sh /src/build.sh
RUN chmod +x /src/build.sh
