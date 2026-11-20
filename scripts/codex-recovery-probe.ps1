param([Parameter(Mandatory=$true)][string]$Binding)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$b=Get-Content -LiteralPath $Binding -Raw -Encoding UTF8|ConvertFrom-Json
function Unknown([string]$reason){@{state='unknown';reason=$reason;can_resume=$false}|ConvertTo-Json -Compress;exit}
if(!$b.document_runtime_id -or !$b.process_started_at -or !$b.chat_title){Unknown 'original_chat_identity_missing'}
$process=Get-Process -Id $b.process_id -ErrorAction Stop
if($process.StartTime.ToUniversalTime().Ticks -ne ([datetime]$b.process_started_at).ToUniversalTime().Ticks){Unknown 'bound_process_replaced'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$b.hwnd)
if($root.Current.ProcessId -ne $b.process_id){Unknown 'bound_window_replaced'}
$dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$docs=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc)|Where-Object {
 !$_.Current.IsOffscreen -and $_.Current.Name -eq $b.chat_title -and ($_.GetRuntimeId() -join ',') -eq ($b.document_runtime_id -join ',')
})
if($docs.Count -ne 1){Unknown 'original_chat_not_visible'}
$scopeCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'对话')
$scopes=@($docs[0].FindAll([System.Windows.Automation.TreeScope]::Descendants,$scopeCondition)|Where-Object {!$_.Current.IsOffscreen})
if($scopes.Count -ne 1){Unknown 'original_chat_scope_changed'}
$scope=$scopes[0]
$bc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
$buttons=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)|Where-Object {!$_.Current.IsOffscreen})
if(@($buttons|Where-Object {$_.Current.Name -in @('停止','Stop','停止生成')}).Count){@{state='active';can_resume=$false}|ConvertTo-Json -Compress;exit}
if(@($buttons|Where-Object {$_.Current.Name -match '批准|允许一次|允许本次|拒绝|提交答案|Approve|Allow once|Deny'}).Count){Unknown 'awaiting_user_or_approval'}
$ec=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Edit)
$edits=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$ec)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.IsEnabled})
if($edits.Count -ne 1){Unknown 'unique_ready_composer_unavailable'}
$value=$null
if(!$edits[0].TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -or $value.Current.IsReadOnly){Unknown 'composer_readiness_unconfirmed'}
$draft=$value.Current.Value.Trim()
# The contenteditable composer exposes its localized placeholder as the value.
if($draft -and $draft -notmatch '^(?:使用\s*ChatGPT(?:\s*Work)?|今天帮你做点什么|Ask anything|Message ChatGPT|向\s*ChatGPT\s*发送消息)$'){Unknown 'user_draft_present'}
# A voice button is not idle evidence. This probe never mutates the composer.
@{state='idle';can_resume=$false;reason='uia_monitor_only_no_atomic_dispatch'}|ConvertTo-Json -Compress
