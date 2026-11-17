function Get-StopConfirmation([int]$VisibleStopCount, [int]$PreviousMissingSamples) {
    # After a real Stop invoke, stable disappearance confirms interruption.
    # The idle composer may still be rendering and is not required evidence.
    $missing = if ($VisibleStopCount -eq 0) { $PreviousMissingSamples + 1 } else { 0 }
    return @{ missing_samples = $missing; confirmed = ($missing -ge 2) }
}
