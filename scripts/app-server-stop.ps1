param([Parameter(Mandatory=$true)][string]$Binding,[ValidateSet('Probe','Stop')][string]$Action='Probe')
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
$b=Get-Content -LiteralPath $Binding -Raw|ConvertFrom-Json
$uri=[Uri]$b.url
if($uri.Scheme -ne 'ws' -or $uri.Host -notin @('127.0.0.1','localhost','::1')){throw 'local_app_server_required'}
$ws=[Net.WebSockets.ClientWebSocket]::new()
$cancel=[Threading.CancellationTokenSource]::new(4000)
$events=[Collections.Generic.Queue[object]]::new()
function Send-Object($obj){
 $bytes=[Text.Encoding]::UTF8.GetBytes(($obj|ConvertTo-Json -Depth 20 -Compress))
 $ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,$cancel.Token).GetAwaiter().GetResult()
}
function Receive-Object {
 $memory=[IO.MemoryStream]::new()
 try{
  do {
   $buffer=[byte[]]::new(65536)
   $received=$ws.ReceiveAsync([ArraySegment[byte]]::new($buffer),$cancel.Token).GetAwaiter().GetResult()
   if($received.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close){throw 'app_server_closed'}
   $memory.Write($buffer,0,$received.Count)
   if($memory.Length -gt 16777216){throw 'app_server_message_too_large'}
  }while(!$received.EndOfMessage)
  return ([Text.Encoding]::UTF8.GetString($memory.ToArray())|ConvertFrom-Json)
 }finally{$memory.Dispose()}
}
function Invoke-Rpc($id,$method,$params){
 Send-Object @{id=$id;method=$method;params=$params}
 while($true){
  $message=Receive-Object
  if($message.id -eq $id){if($message.error){throw ($message.error|ConvertTo-Json -Compress)};return $message.result}
  $events.Enqueue($message)
 }
}
try{
 $ws.ConnectAsync($uri,$cancel.Token).GetAwaiter().GetResult()
 $null=Invoke-Rpc 1 'initialize' @{clientInfo=@{name='recruiting-stop';version='2'}}
 Send-Object @{method='initialized';params=@{}}
 $result=Invoke-Rpc 2 'thread/read' @{threadId=$b.thread_id;includeTurns=$true}
 $turns=@($result.thread.turns)
 if(!$turns.Count -or $turns[-1].id -ne $b.turn_id -or $turns[-1].status -notin @('inProgress','in_progress')){throw 'bound_turn_not_active'}
 if($Action -eq 'Stop'){
  $null=Invoke-Rpc 3 'turn/interrupt' @{threadId=$b.thread_id;turnId=$b.turn_id}
  do{
   $message=if($events.Count){$events.Dequeue()}else{Receive-Object}
  }while($message.method -ne 'turn/completed' -or $message.params.turn.id -ne $b.turn_id -or $message.params.turn.status -ne 'interrupted')
 }
 @{state=$(if($Action -eq 'Stop'){'interrupted'}else{'ready'});kind='app_server'}|ConvertTo-Json -Compress
}finally{$ws.Dispose();$cancel.Dispose()}
