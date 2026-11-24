# Screen pixels may be captured without activation, but must never include an occluding window.
Add-Type -AssemblyName System.Windows.Forms
if(!('BossCaptureVisibility' -as [type])){
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class BossCaptureVisibility {
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
    public delegate bool EnumProc(IntPtr h, IntPtr data);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out Rect r);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb,IntPtr data);
    [DllImport("dwmapi.dll", EntryPoint="DwmGetWindowAttribute")] static extern int GetDwmInt(IntPtr h,int attr,out int value,int size);
    [DllImport("dwmapi.dll", EntryPoint="DwmGetWindowAttribute")] static extern int GetDwmRect(IntPtr h,int attr,out Rect value,int size);
    static bool Cloaked(IntPtr h) { int value; return GetDwmInt(h,14,out value,4)==0 && value!=0; }
    static bool Overlaps(Rect a,Rect b) {return a.Left<b.Right && a.Right>b.Left && a.Top<b.Bottom && a.Bottom>b.Top;}
    public static string Check(IntPtr target,int x,int y,int width,int height) {
        if(width<=0 || height<=0 || !IsWindowVisible(target) || IsIconic(target) || Cloaked(target)) return "capture_window_not_visible";
        Rect area=new Rect {Left=x,Top=y,Right=x+width,Bottom=y+height};
        Rect host;
        if(!GetWindowRect(target,out host) || area.Left<host.Left || area.Top<host.Top || area.Right>host.Right || area.Bottom>host.Bottom) return "capture_region_outside_window";
        bool found=false,occluded=false;
        bool enumerated=EnumWindows(delegate(IntPtr h,IntPtr data) {
            if(h==target) {found=true;return false;}
            if(!IsWindowVisible(h) || IsIconic(h) || Cloaked(h)) return true;
            Rect r;
            if(GetDwmRect(h,9,out r,Marshal.SizeOf(typeof(Rect)))!=0 && !GetWindowRect(h,out r)) {occluded=true;return false;}
            if(Overlaps(area,r)) {occluded=true;return false;}
            return true;
        },IntPtr.Zero);
        if(occluded) return "capture_region_occluded";
        if(!found) return "capture_window_not_in_visible_zorder";
        return null;
    }
}
'@
}

function Assert-BossCaptureVisible([long]$WindowHandle,$Geometry) {
    $null=Get-BossBrowserRoot $WindowHandle
    $area=[Drawing.Rectangle]::new([int]$Geometry.left,[int]$Geometry.top,[int]$Geometry.width,[int]$Geometry.height)
    $contained=$false
    foreach($monitor in [Windows.Forms.Screen]::AllScreens){if($monitor.Bounds.Contains($area)){$contained=$true;break}}
    if(!$contained){throw 'capture_region_outside_monitor'}
    $reason=[BossCaptureVisibility]::Check([IntPtr]$WindowHandle,$area.X,$area.Y,$area.Width,$area.Height)
    if($reason){throw $reason}
}
