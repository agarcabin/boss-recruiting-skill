param([Parameter(Mandatory=$true)][long]$WindowHandle,[Parameter(Mandatory=$true)][string]$CandidateName,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class CardNative { [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
'@
[void][CardNative]::SetProcessDPIAware()
if([CardNative]::GetForegroundWindow().ToInt64() -ne $WindowHandle){throw 'boss_window_not_foreground'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
$docCondition=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'BOSS直聘'))
$docs=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$docCondition)
$document=$null;$url=$null
foreach($doc in $docs){$pattern=$null;if($doc.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)){$value=$pattern.Current.Value;if($value -like 'https://www.zhipin.com/web/chat/recommend*'){$document=$doc;$url=$value;break}}}
if(!$document){throw 'recommend_document_not_found'}
$cardCondition=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'card-item'))
$matches=@($document.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cardCondition)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.Name.Contains($CandidateName)})
if($matches.Count -ne 1){throw 'candidate_card_ambiguous_or_missing'}
$card=$matches[0];$rect=$card.Current.BoundingRectangle
if($rect.Width -lt 20 -or $rect.Height -lt 20){throw 'card_bounds_invalid'}
$center=[System.Windows.Point]::new($rect.X+$rect.Width/2,$rect.Y+$rect.Height/2)
$hit=[System.Windows.Automation.AutomationElement]::FromPoint($center)
$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker;$belongs=$false
for($i=0;$hit -and $i -lt 15;$i++) {if(($hit.GetRuntimeId() -join ',') -eq ($card.GetRuntimeId() -join ',')){$belongs=$true;break};$hit=$walker.GetParent($hit)}
if(!$belongs){throw 'card_occluded_or_target_mismatch'}
$text=$card.Current.Name
$advantage='';$expectation=''
if($text -match '(?s)优势[：:\s]*(.*?)(?=期望[：:\s]|$)'){$advantage=$Matches[1].Trim()}
if($text -match '(?s)期望[：:\s]*(.*?)(?=优势[：:\s]|打招呼|继续沟通|$)'){$expectation=$Matches[1].Trim()}
$fields=@{advantage=$advantage;expectation=$expectation;already_contacted= [bool]($text -match '已沟通|已打招呼|继续沟通')}
$observation=@{name=$CandidateName;card=$fields;raw_text=$text;observed_at=[DateTimeOffset]::Now.ToString('o');document_url=$url;window_handle=$WindowHandle;runtime_id=$card.GetRuntimeId();bounds=@{x=$rect.X;y=$rect.Y;width=$rect.Width;height=$rect.Height}}
$directory=[IO.Path]::GetFullPath($OutputDirectory);[IO.Directory]::CreateDirectory($directory)|Out-Null
$bitmap=[Drawing.Bitmap]::new([int]$rect.Width,[int]$rect.Height);$graphics=[Drawing.Graphics]::FromImage($bitmap)
try {$graphics.CopyFromScreen([int]$rect.X,[int]$rect.Y,0,0,$bitmap.Size);$bitmap.Save((Join-Path $directory 'card.png'),[Drawing.Imaging.ImageFormat]::Png)}finally{$graphics.Dispose();$bitmap.Dispose()}
$observation | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $directory 'card.uia.json') -Encoding UTF8
$observation | ConvertTo-Json -Depth 8 -Compress
