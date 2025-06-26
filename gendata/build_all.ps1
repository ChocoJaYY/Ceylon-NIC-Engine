$AppName = "NICServer"
$OutputDir = "../bin"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$targets = @(
    @{ OS = "windows"; ARCH = "amd64" },
    @{ OS = "linux"; ARCH = "amd64" },
    @{ OS = "darwin"; ARCH = "amd64" },
    @{ OS = "linux"; ARCH = "arm64" },
    @{ OS = "darwin"; ARCH = "arm64" }
)

foreach ($target in $targets) {
    $os = $target.OS
    $arch = $target.ARCH
    $output = "${OutputDir}/${arch}_${os}_${AppName}"
    
    if ($os -eq "windows") {
        $output += ".exe"
    }

    Write-Host "Building for $os/$arch -> $(Split-Path $output -Leaf)"
    $env:GOOS = $os
    $env:GOARCH = $arch

    go build -o $output nic_generator.go
}

# Clean up environment variables
Remove-Item Env:GOOS
Remove-Item Env:GOARCH
