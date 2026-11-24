param([Parameter(Mandatory=$true)][string]$PythonPath,[switch]$Maximized)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies @('System.Windows.Forms','System.Windows.Forms.Primitives','System.Drawing','System.Drawing.Primitives','System.ComponentModel.Primitives','System.ComponentModel','System.Runtime') @'
using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;
public class PassiveDisplayTestForm : Form {
    protected override bool ShowWithoutActivation { get {return true;} }
    protected override CreateParams CreateParams { get {var cp=base.CreateParams;cp.ExStyle|=0x08000000;return cp;} }
}
public static class DisplayTestNative {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
}
'@
[void][DisplayTestNative]::SetProcessDpiAwarenessContext([IntPtr](-4))
[void][DisplayTestNative]::SetThreadDpiAwarenessContext([IntPtr](-4))
. (Join-Path $PSScriptRoot 'capture-visibility.ps1')
$screens=[Windows.Forms.Screen]::AllScreens
$screen=@($screens|Where-Object {!$_.Primary})|Select-Object -First 1
if(!$screen){$screen=[Windows.Forms.Screen]::PrimaryScreen}
$before=[DisplayTestNative]::GetForegroundWindow()
$form=[PassiveDisplayTestForm]::new()
$cover=[PassiveDisplayTestForm]::new()
try {
    $form.Text='Recruiting display QA (synthetic)'
    $form.FormBorderStyle='None'
    $form.StartPosition='Manual'
    $form.BackColor=[Drawing.Color]::FromArgb(36,125,196)
    $form.Bounds=[Drawing.Rectangle]::new($screen.WorkingArea.Left+100,$screen.WorkingArea.Top+140,320,180)
    $form.TopMost=$true
    if($Maximized){$form.WindowState='Maximized'}
    $form.Show()
    [Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 200
    $rect=$form.Bounds
    $x=$rect.Left+20;$y=$rect.Top+20
    $reason=[BossCaptureVisibility]::Check($form.Handle,$x,$y,120,90)
    if($reason){throw ('unobscured_test_window_rejected: '+$reason)}
    if([DisplayTestNative]::GetForegroundWindow() -ne $before){throw 'synthetic_form_stole_focus'}
    $bitmap=[Drawing.Bitmap]::new(120,90)
    $graphics=[Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($x,$y,0,0,$bitmap.Size)
        $actual=$bitmap.GetPixel(60,45);$expected=$form.BackColor
        if([math]::Abs($actual.R-$expected.R)+[math]::Abs($actual.G-$expected.G)+[math]::Abs($actual.B-$expected.B) -gt 15){
            throw ('background_screen_pixels_mismatch: actual='+$actual+' expected='+$expected+' rect='+$rect+' screen='+$screen.Bounds)
        }
    } finally {$graphics.Dispose();$bitmap.Dispose()}
    $cover.FormBorderStyle='None';$cover.StartPosition='Manual';$cover.TopMost=$true
    $cover.Bounds=[Drawing.Rectangle]::new($x,$y,120,90)
    $cover.Show();[Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds 100
    if([BossCaptureVisibility]::Check($form.Handle,$x,$y,120,90) -ne 'capture_region_occluded'){throw 'occluder_not_rejected'}
    $cover.Hide()
    [Windows.Forms.Application]::DoEvents()
    $code=@'
import ctypes,json,sys
ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
sys.path.insert(0,sys.argv[1])
import display_switch
native=display_switch.NativeDisplays()
hwnd=int(sys.argv[2]);current=native.monitor_for_window(hwnd)
native.api.GetForegroundWindow.restype=ctypes.c_void_p
foreground=native.api.GetForegroundWindow()
monitors=native.monitors()
if len(monitors)>1:
    for _ in range(2):
        target=display_switch.destination(monitors,native.monitor_for_window(hwnd))
        native.move(hwnd,target['work'])
        if native.monitor_for_window(hwnd)!=target['handle']:raise RuntimeError('native_move_wrong_monitor')
        if native.api.GetForegroundWindow()!=foreground:raise RuntimeError('native_move_stole_focus')
print(json.dumps(dict(state='passed',monitors=len(monitors),focus_preserved=True)))
'@
    $nativeResult=& $PythonPath -c $code $PSScriptRoot $form.Handle.ToInt64()
    if($LASTEXITCODE -ne 0){throw 'native_display_roundtrip_failed'}
    if([DisplayTestNative]::GetForegroundWindow() -ne $before){throw 'native_test_changed_foreground'}
    @{state='passed';background_pixels=$true;occlusion_rejected=$true;native_move=($nativeResult|ConvertFrom-Json)}|ConvertTo-Json -Compress -Depth 4
} finally {$cover.Dispose();$form.Dispose()}
