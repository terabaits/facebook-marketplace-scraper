# Stop the SS-WEBSITE Flask server. Finds the listener on :5000 and
# stops it (the worker is a child of the python.exe that bound the port).
$conn = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $pid_to_kill = $conn.OwningProcess
    Write-Host "Killing SS-WEBSITE (PID $pid_to_kill on :5000)..."
    Stop-Process -Id $pid_to_kill -Force -ErrorAction SilentlyContinue
    # Also stop the parent if it was a launcher shell
    $wmi = Get-WmiObject -Class Win32_Process -Filter "ProcessId=$pid_to_kill" -ErrorAction SilentlyContinue
    if ($wmi -and $wmi.ParentProcessId -and $wmi.ParentProcessId -ne 0) {
        $parent = Get-WmiObject -Class Win32_Process -Filter "ProcessId=$($wmi.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent -and $parent.CommandLine -like '*start_tornado*') {
            Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
    $check = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($check) {
        Write-Host "Port 5000 still in use by PID $($check.OwningProcess). Force-killing..."
        Stop-Process -Id $check.OwningProcess -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "Server stopped."
    }
} else {
    Write-Host "No server listening on :5000."
}
