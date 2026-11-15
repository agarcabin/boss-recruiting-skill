param([string]$Workbook,[string]$Ready,[string]$Result)
$ErrorActionPreference='Stop'
$app=$null;$book=$null
try {
 $app=New-Object -ComObject Excel.Application;$app.Visible=$false;$app.DisplayAlerts=$false
 $book=$app.Workbooks.Open($Workbook,0,$false)
 $app.CalculateUntilAsyncQueriesDone()
 [IO.File]::WriteAllText($Ready,'ready')
 $seen=@();$deadline=[DateTime]::UtcNow.AddSeconds(160)
 while([DateTime]::UtcNow -lt $deadline){
  $sheet=$book.Worksheets.Item('候选人简报')
  $name=[string]$sheet.Cells.Item(3,2).Value2
  if($name -in @('第二批虚构记录','第三批虚构记录') -and $name -notin $seen){
   $seen+=,$name
   $last=$sheet.ListObjects.Item(1).ListColumns.Item('查看简历').DataBodyRange
   $payload=@{seen=$seen;formula=[string]$last.Cells.Item($last.Rows.Count,1).Formula;rows=$last.Rows.Count;conditions=$sheet.Cells.Item($sheet.ListObjects.Item(1).Range.Rows.Count+1,1).FormatConditions.Count;state='waiting'}
   if($seen.Count -eq 2){$payload.state='verified'}
   $payload|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $Result -Encoding UTF8
   if($seen.Count -eq 2){break}
  }
  Start-Sleep -Milliseconds 400
 }
 if($seen.Count -ne 2){throw 'automatic_refresh_not_observed'}
 $book.Save()
} catch {
 @{state='failed';error=$_.Exception.Message}|ConvertTo-Json|Set-Content -LiteralPath $Result -Encoding UTF8
 throw
} finally {
 if($book){$book.Close($false)}
 if($app){$app.Quit();[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)}
}
