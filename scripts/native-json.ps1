# Native stdout/stderr always use real pipes, including hidden window hosts.
function Invoke-NativeJson([string]$Executable,[string[]]$Arguments,[int]$TimeoutMs=120000) {
    if($PSVersionTable.PSVersion.Major -lt 7){throw 'powershell_7_required_for_capture'}
    $start=[Diagnostics.ProcessStartInfo]::new()
    $start.FileName=$Executable
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true
    $start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    $start.StandardOutputEncoding=[Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding=[Text.UTF8Encoding]::new($false)
    $start.Environment['PYTHONUTF8']='1';$start.Environment['PYTHONIOENCODING']='utf-8'
    foreach($arg in $Arguments){$start.ArgumentList.Add($arg)}
    $proc=[Diagnostics.Process]::new();$proc.StartInfo=$start
    try {
        if(!$proc.Start()){throw 'capture_native_process_not_started'}
        $stdout=$proc.StandardOutput.ReadToEndAsync();$stderr=$proc.StandardError.ReadToEndAsync()
        if(!$proc.WaitForExit($TimeoutMs)){$proc.Kill($true);throw 'capture_native_process_timeout'}
        $out=$stdout.GetAwaiter().GetResult();$err=$stderr.GetAwaiter().GetResult()
        if($proc.ExitCode -ne 0){throw "capture_native_failed: exit=$($proc.ExitCode); $err"}
        if(!$out.Trim()){throw "capture_native_empty_json: $err"}
        return $out
    } finally {$proc.Dispose()}
}
