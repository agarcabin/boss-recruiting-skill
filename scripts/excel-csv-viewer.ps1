param([Parameter(Mandatory=$true)][string]$Config)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false);[Console]::OutputEncoding=$OutputEncoding
$c=Get-Content -LiteralPath $Config -Raw -Encoding UTF8|ConvertFrom-Json
function MText([string]$Value){return '"'+$Value.Replace('"','""')+'"'}
$excel=$null;$book=$null
try {
 $excel=New-Object -ComObject Excel.Application
 $excel.Visible=$false;$excel.DisplayAlerts=$false;$excel.AskToUpdateLinks=$false
 $excel.AutomationSecurity=3
 $book=$excel.Workbooks.Open([string]$c.template,0,$false)
 $batchRefs=@();$refreshRefs=@();$i=0
 foreach($spec in $c.tables){
  $i++;$queryName='RecruitData'+$i;$tableName='RecruitTable'+$i
  try{$ws=$book.Worksheets.Item([string]$spec.sheet)}catch{$ws=$book.Worksheets.Add();$ws.Name=[string]$spec.sheet}
  $ws.Visible=-1
  $start=[int]$spec.row
  $last=[math]::Max($start,$ws.UsedRange.Row+$ws.UsedRange.Rows.Count)
  $width=[math]::Max($spec.columns.Count+3,$ws.UsedRange.Columns.Count)
  $null=$ws.Range($ws.Cells.Item($start,1),$ws.Cells.Item($last,$width)).ClearContents()
  $pairs=@()
  for($j=0;$j -lt $spec.columns.Count;$j++){$pairs+='{'+(MText $spec.columns[$j])+', type '+[string]$spec.types[$j]+'}'}
  $formula='let Raw=Csv.Document(File.Contents('+(MText $spec.file)+'),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]), Headers=Table.PromoteHeaders(Raw,[PromoteAllScalars=true]), Typed=Table.TransformColumnTypes(Headers,{'+($pairs -join ',')+'}), Refreshed=Table.AddColumn(Typed,"__刷新时间",each DateTime.LocalNow(),type datetime) in Refreshed'
  $null=$book.Queries.Add($queryName,$formula)
  $connection='OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location='+$queryName+';Extended Properties=""'
  $table=$ws.ListObjects.Add(0,$connection,[Type]::Missing,1,$ws.Cells.Item($start,1))
  $table.Name=$tableName
  $q=$table.QueryTable
  $q.CommandType=2;$q.CommandText='SELECT * FROM ['+$queryName+']'
  $q.BackgroundQuery=$false;$q.AdjustColumnWidth=$false;$q.PreserveFormatting=$true
  $q.RefreshPeriod=1;$q.RefreshOnFileOpen=$true;$q.RefreshStyle=1
  if(!$q.Refresh($false)){throw 'excel_first_refresh_failed'}
  if($q.RefreshPeriod -ne 1 -or !$q.RefreshOnFileOpen){throw 'excel_refresh_settings_not_retained'}
  if($spec.links){
   foreach($prop in $spec.links.PSObject.Properties){
    $column=$table.ListColumns.Add();$column.Name=$prop.Name
    $source='[@['+$prop.Value+']]'
    if($column.DataBodyRange){$column.DataBodyRange.Formula='=IF(OR('+$source+'="",'+$source+'="未保存"),"未保存",HYPERLINK('+$source+',"'+$prop.Name+'"))'}
   }
  }
  foreach($column in $table.ListColumns){
   if($column.Name.StartsWith('__')){$column.Range.EntireColumn.Hidden=$true}
  }
  $batchRefs+="'$($ws.Name.Replace("'","''"))'!"+$ws.Cells.Item($start+1,$spec.columns.Count-1).Address($false,$false)
  $refreshRefs+="'$($ws.Name.Replace("'","''"))'!"+$ws.Cells.Item($start+1,$spec.columns.Count+1).Address($false,$false)
  if($spec.sheet -eq '候选人简报'){
   $null=$table.DataBodyRange.Interior.ColorIndex=-4142
   $null=$table.DataBodyRange.FormatConditions.Delete()
   $first=$start+1
   $green=$table.DataBodyRange.FormatConditions.Add(2,[Type]::Missing,'=OR($J'+$first+'="sent",ISNUMBER(SEARCH("第1句:sent",$J'+$first+')))')
   $green.Interior.Color=14282978
   $yellow=$table.DataBodyRange.FormatConditions.Add(2,[Type]::Missing,'=ISNUMBER(SEARCH("复核",$D'+$first+'))')
   $yellow.Interior.Color=10284031
   $ws.Cells.Item(1,1).Formula="='_刷新汇总'!A2"
  }
  if($spec.hidden){$ws.Visible=0}
 }
 $status=$book.Worksheets.Add();$status.Name='数据刷新'
 $status.Cells.Item(1,1).Value2='CSV 自动刷新状态'
 $status.Cells.Item(2,1).Value2='批次一致性'
 $checks=@();for($j=1;$j -lt $batchRefs.Count;$j++){$checks+=($batchRefs[$j]+'='+$batchRefs[0])}
 $status.Cells.Item(2,2).Formula='=IF(AND('+($checks -join ',')+'),"已刷新至同一批次","待刷新：各页批次尚未一致")'
 $status.Cells.Item(3,1).Value2='数据源批次';$status.Cells.Item(3,2).Formula='='+$batchRefs[0]
 $status.Cells.Item(4,1).Value2='最近成功查询时间';$status.Cells.Item(4,2).Formula='=MAX('+($refreshRefs -join ',')+')'
 $status.Cells.Item(4,2).NumberFormat='yyyy-mm-dd hh:mm:ss'
 $status.Cells.Item(6,1).Value2='Excel保持打开时每分钟刷新；数据修改不回写CSV。'
 $status.Columns.Item(1).ColumnWidth=48;$status.Columns.Item(2).ColumnWidth=48
 $book.Worksheets.Item('候选人简报').Activate()
 $excel.CalculateUntilAsyncQueriesDone()
 $book.SaveAs([string]$c.target,51)
 $book.Close($true);$book=$null
 @{state='verified';queries=$i;refresh_minutes=1;refresh_on_open=$true;target=$c.target}|ConvertTo-Json -Compress
} catch {
 [Console]::Error.WriteLine($_.ScriptStackTrace+"`n"+$_.InvocationInfo.Line+"`n"+$_.Exception.Message)
 throw
} finally {
 if($book){$book.Close($false)}
 if($excel){$excel.Quit();[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel)}
 [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
