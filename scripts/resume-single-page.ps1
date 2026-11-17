param([string]$ObservationFile)

function Test-ResumeSinglePage($Observation) {
    if ($Observation.scrollable) { return @{complete=$false;reason='resume_has_scrollable_content'} }
    $doc=$Observation.document
    if ($doc.width -le 0 -or $doc.height -le 0) {
        return @{complete=$false;reason='resume_document_geometry_missing'}
    }
    foreach ($node in $Observation.nodes) {
        if ($node.name -match '^(加载中|正在加载|载入中|Loading)([.。…\s]*)$') {
            return @{complete=$false;reason='resume_still_loading'}
        }
    }
    return @{complete=$true;reason='single_page_pending_ocr_bottom_marker'}
}

if ($ObservationFile) {
    Test-ResumeSinglePage (Get-Content -LiteralPath $ObservationFile -Raw -Encoding UTF8|ConvertFrom-Json) | ConvertTo-Json -Compress
}
