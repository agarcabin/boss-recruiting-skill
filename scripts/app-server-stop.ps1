param([Parameter(Mandatory=$true)][string]$Binding,[ValidateSet('Probe','Stop','RecoveryProbe','Resume')][string]$Action='Probe',[string]$RunId)
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
 $null=$ws.SendAsync([ArraySegment[byte]]::new($bytes),[Net.WebSockets.WebSocketMessageType]::Text,$true,$cancel.Token).GetAwaiter().GetResult()
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
 $null=$ws.ConnectAsync($uri,$cancel.Token).GetAwaiter().GetResult()
 $null=Invoke-Rpc 1 'initialize' @{clientInfo=@{name='recruiting-stop';version='2'}}
 Send-Object @{method='initialized';params=@{}}
 $result=Invoke-Rpc 2 'thread/read' @{threadId=$b.thread_id;includeTurns=$true}
 $turns=@($result.thread.turns)
 if($Action -in @('RecoveryProbe','Resume')){
  if(!$b.desktop_thread_verified -or !$b.thread_id){throw 'verified_desktop_thread_required'}
  $last=if($turns.Count){$turns[-1]}else{$null}
  if($last -and $last.status -eq 'interrupted'){@{state='user_stop';can_resume=$false}|ConvertTo-Json -Compress;exit}
  if($last -and $last.status -in @('inProgress','in_progress')){@{state='active';can_resume=$false}|ConvertTo-Json -Compress;exit}
  $threadState=if($result.thread.status -is [string]){$result.thread.status}else{$result.thread.status.type}
  if($threadState -ne 'idle'){@{state='unknown';reason='desktop_thread_not_confirmed_idle'}|ConvertTo-Json -Compress;exit}
  # A completed question also looks idle. Only a desktop-owned atomic guard can
  # establish that no draft, queued input, approval, or question needs the user.
  if(!$b.recovery_guard_method -or !$b.recovery_dispatch_method){@{state='unknown';reason='guarded_desktop_recovery_unsupported';can_resume=$false}|ConvertTo-Json -Compress;exit}
  $guard=Invoke-Rpc 3 $b.recovery_guard_method @{threadId=$b.thread_id;expectedTurnId=$last.id;runId=$RunId}
  if($guard.userStopped -eq $true){@{state='user_stop';can_resume=$false}|ConvertTo-Json -Compress;exit}
  if($guard.noUserInput -ne $true -or $guard.noPendingQuestion -ne $true -or $guard.noQueuedInput -ne $true -or $guard.noApproval -ne $true -or $guard.noDraft -ne $true -or !$guard.guardToken){@{state='unknown';reason='desktop_user_input_gate_unconfirmed';can_resume=$false}|ConvertTo-Json -Compress;exit}
  if($Action -eq 'RecoveryProbe'){@{state='idle';can_resume=$true}|ConvertTo-Json -Compress;exit}
  if($RunId -notmatch '^[A-Za-z0-9_-]+$'){throw 'invalid_recovery_run_id'}
  $message="继续当前招聘任务；沿用运行 $RunId，从现有检查点处理，不新建运行、不重复招呼。先核对该运行尚未暂停或结束，再继续。"
  # The configured desktop method must atomically consume the one-use guard
  # token and recheck idle/user state; plain turn/start cannot provide that.
  $started=Invoke-Rpc 4 $b.recovery_dispatch_method @{threadId=$b.thread_id;expectedTurnId=$last.id;guardToken=$guard.guardToken;runId=$RunId;text=$message}
  if(!$started.turn.id){throw 'resume_turn_not_acknowledged'}
  @{state='started';thread_id=$b.thread_id;turn_id=$started.turn.id}|ConvertTo-Json -Compress;exit
 }
 if(!$turns.Count -or $turns[-1].status -notin @('inProgress','in_progress')){
  @{state='idle';kind='app_server'}|ConvertTo-Json -Compress
  exit 0
 }
 # Resume starts a new turn on the same bound thread; never reuse the old turn ID.
 $activeTurnId=$turns[-1].id
 if($Action -eq 'Stop'){
  $null=Invoke-Rpc 3 'turn/interrupt' @{threadId=$b.thread_id;turnId=$activeTurnId}
  do{
   $message=if($events.Count){$events.Dequeue()}else{Receive-Object}
  }while($message.method -ne 'turn/completed' -or $message.params.turn.id -ne $activeTurnId -or $message.params.turn.status -ne 'interrupted')
 }
 @{state=$(if($Action -eq 'Stop'){'interrupted'}else{'ready'});kind='app_server'}|ConvertTo-Json -Compress
}finally{$ws.Dispose();$cancel.Dispose()}
