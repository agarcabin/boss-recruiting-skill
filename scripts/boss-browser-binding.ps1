# Shared, fail-closed boundary for BOSS UIA only. No browser/desktop fallback.
function Get-BossBrowserRoot([long]$Handle=0) {
 if(!$env:BOSS_BROWSER_BINDING -or !(Test-Path -LiteralPath $env:BOSS_BROWSER_BINDING)){throw 'codex_iab_binding_required'}
 $b=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
 if($b.browser_target -ne 'codex_iab' -or !$b.tab_id -or !$b.chat_title){throw 'invalid_codex_iab_binding'}
 if($Handle -and $Handle -ne [long]$b.hwnd){throw 'external_browser_window_forbidden'}
 $process=Get-Process -Id $b.process_id -ErrorAction Stop
 if($process.ProcessName -ne 'Codex' -or $process.StartTime.ToUniversalTime().Ticks.ToString() -ne [string]$b.process_started_ticks){throw 'codex_iab_host_changed'}
 $hostRoot=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$b.hwnd)
 if(!$hostRoot -or $hostRoot.Current.ProcessId -ne $b.process_id){throw 'codex_iab_window_changed'}
 $dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
 $docs=@($hostRoot.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc))
 $chat=@($docs|Where-Object {$v=$null; !$_.Current.IsOffscreen -and $_.Current.Name -eq $b.chat_title -and $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -like 'app://*/index.html*'})
 if($chat.Count -ne 1){throw 'codex_iab_chat_changed'}
 $bound=@($docs|Where-Object {($_.GetRuntimeId() -join ',') -eq ($b.document_runtime_id -join ',')})
 if($bound.Count -ne 1 -or $bound[0].Current.IsOffscreen){throw 'codex_iab_document_lost_rebind_required'}
 $value=$null
 if(!$bound[0].TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -or $value.Current.Value -notmatch '^https://www\.zhipin\.com(?:/|$)'){throw 'codex_iab_not_boss'}
 return $bound[0]
}

function Assert-BossBrowserTarget($Element,[long]$Handle=0) {
 $bound=Get-BossBrowserRoot $Handle
 $cursor=$Element;$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
 for($i=0;$cursor -and $i -lt 100;$i++){
  if(($cursor.GetRuntimeId() -join ',') -eq ($bound.GetRuntimeId() -join ',')){return}
  $cursor=$walker.GetParent($cursor)
 }
 throw 'target_outside_bound_codex_iab'
}

function Get-BossDocuments($Root) {
 $dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
 return @($Root)+@($Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc))
}

function Get-BossBindingId {
 $null=Get-BossBrowserRoot
 $binding=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
 if(!$binding.binding_id){throw 'codex_iab_rebind_required'}
 return $binding.binding_id
}


function Assert-BossForeground {
 if(!('BossBrowserNative' -as [type])){Add-Type 'using System;using System.Runtime.InteropServices;public class BossBrowserNative{[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();}'}
 $null=Get-BossBrowserRoot
 $b=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
 if([BossBrowserNative]::GetForegroundWindow().ToInt64() -ne [long]$b.hwnd){throw 'bound_codex_iab_not_foreground'}
}

function Assert-BossPointer {
 Assert-BossForeground
 Add-Type -AssemblyName System.Windows.Forms
 $p=[System.Windows.Forms.Cursor]::Position
 $element=[System.Windows.Automation.AutomationElement]::FromPoint([System.Windows.Point]::new($p.X,$p.Y))
 Assert-BossBrowserTarget $element
}
