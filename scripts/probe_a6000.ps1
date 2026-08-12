param(
    [string[]]$Hosts = @(
        "202.120.62.181-hfy-24100",
        "202.120.62.181-sunyinan-24097",
        "202.120.62.181-hfy-24095"
    )
)

$ErrorActionPreference = "Continue"
foreach ($RemoteHost in $Hosts) {
    Write-Output "[$RemoteHost]"
    ssh -o BatchMode=yes -o ConnectTimeout=8 $RemoteHost "hostname; nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader; python3 --version; df -BG . | tail -1"
}
