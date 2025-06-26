#!/bin/bash

APP_NAME=NICServer
OUTPUT_DIR="../bin"

mkdir -p $OUTPUT_DIR

targets=(
  "windows amd64"
  "linux amd64"
  "darwin amd64"
  "linux arm64"
  "darwin arm64"
)

for target in "${targets[@]}"; do
  os=$(echo $target | cut -d' ' -f1)
  arch=$(echo $target | cut -d' ' -f2)
  
  output="${OUTPUT_DIR}/${arch}_${os}_${APP_NAME}"
  if [ "$os" = "windows" ]; then
    output="${output}.exe"
  fi
  
  echo "Building for $os/$arch -> $output"
  GOOS=$os GOARCH=$arch go build -o $output nic_generator.go
done
