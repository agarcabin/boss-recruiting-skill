# Shared label matcher; keep anchored to exclude unrelated filter text.
function Test-BossFilterLabel([string]$Label){
 return $Label -match '^筛选(?:条件)?(?:\s*(?:[·•:：]\s*\d+|[（(]\s*\d+\s*[)）]|\d+))?\s*$'
}
