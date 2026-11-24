function Invoke-BossMsaaNavigation($Element,$Scope) {
 $allowed=@('card-inner','turn-btn','close-btn','boss-popup__close')
 $classes=$Element.Current.ClassName -split '\s+'
 if(!@($classes|Where-Object {$_ -in $allowed}).Count){throw 'msaa_navigation_target_not_allowed'}
 if($classes -contains 'turn-btn' -and !($classes -contains 'next')){throw 'msaa_navigation_direction_not_allowed'}
 Add-Type -AssemblyName Accessibility
 if(!('BossMsaaNavigation' -as [type])){
  Add-Type -IgnoreWarnings -WarningAction SilentlyContinue -ReferencedAssemblies @([Accessibility.IAccessible].Assembly.Location,[Diagnostics.Stopwatch].Assembly.Location) -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Accessibility;
public class BossMsaaNavigation {
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr window,uint id,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out IAccessible accessible);
 [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible parent,int start,int count,[Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=2)] object[] children,out int obtained);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);
 static IAccessible Root(long window,int process) {
  uint owner;GetWindowThreadProcessId(new IntPtr(window),out owner);
  if(owner!=(uint)process)throw new Exception("msaa_renderer_process_changed");
  Guid iid=new Guid("618736E0-3C3D-11CF-810C-00AA00389B71");IAccessible result;
  Marshal.ThrowExceptionForHR(AccessibleObjectFromWindow(new IntPtr(window),0xFFFFFFFC,ref iid,out result));return result;
 }
 static IAccessible Find(IAccessible root,string url,int x,int y,int width,int height,bool document,int limitNodes,int limitMs) {
  var queue=new IAccessible[12000];queue[0]=root;int head=0,tail=1,matches=0;IAccessible found=null;
  var timer=System.Diagnostics.Stopwatch.StartNew();
  while(head<tail){
   if(head>=limitNodes || timer.ElapsedMilliseconds>limitMs)throw new Exception("msaa_navigation_search_limit");
   IAccessible item=queue[head++];
   bool intersects=true;
   try{
    bool match=false;
    if(document)match=item.get_accValue(0)==url;
    else{
     int left,top,w,h;item.accLocation(out left,out top,out w,out h,0);
     string action=item.get_accDefaultAction(0);
     match=Math.Abs(left-x)<=1 && Math.Abs(top-y)<=1 && Math.Abs(w-width)<=1 && Math.Abs(h-height)<=1 &&
      (action=="点击" || String.Equals(action,"click",StringComparison.OrdinalIgnoreCase));
     // 目标矩形之外的子树不再展开，避免整窗搜索触顶。
     if(!match && w>0 && h>0)intersects=!(x+width<left-2 || x>left+w+2 || y+height<top-2 || y>top+h+2);
    }
    if(match){found=item;matches++;if(document)return found;}
   }catch(COMException){}
   if(!document && !intersects)continue;
   int count=item.accChildCount;
   if(count>1000 || tail+count>queue.Length)throw new Exception("msaa_navigation_children_limit");
   if(count==0)continue;
   var children=new object[count];int obtained;
   Marshal.ThrowExceptionForHR(AccessibleChildren(item,0,count,children,out obtained));
   for(int index=0;index<obtained;index++){var child=children[index] as IAccessible;if(child!=null)queue[tail++]=child;}
  }
  // 同一位置、同一默认动作的重复节点视为同一目标，取第一个。
  if(matches<1)throw new Exception("msaa_navigation_target_not_unique:"+matches);
  return found;
 }
 public static void Invoke(long window,int process,string url,int x,int y,int width,int height){
  IAccessible root=Root(window,process);
  IAccessible scope=null;
  // 文档 URL 匹配失败时退回窗口根节点，由目标矩形剪枝后继续查找。
  try{scope=Find(root,url,0,0,0,0,true,1500,1200);}catch(Exception){scope=null;}
  if(scope==null)scope=root;
  IAccessible target=Find(scope,url,x,y,width,height,false,6000,4000);
  int left,top,w,h;target.accLocation(out left,out top,out w,out h,0);
  if(Math.Abs(left-x)>1 || Math.Abs(top-y)>1 || Math.Abs(w-width)>1 || Math.Abs(h-height)>1)throw new Exception("msaa_navigation_target_moved");
  target.accDoDefaultAction(0);
 }
}
'@
 }
 $rect=$Element.Current.BoundingRectangle
 if($Element.Current.IsOffscreen -or $rect.Width -le 0 -or $rect.Height -le 0){throw 'msaa_navigation_target_not_visible'}
 $value=$null
 if(!$Scope.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value)){throw 'msaa_navigation_document_unreadable'}
 Assert-BossBrowserTarget $Element
 [BossMsaaNavigation]::Invoke([long]$Scope.GetRuntimeId()[1],$Scope.Current.ProcessId,$value.Current.Value,[int]$rect.Left,[int]$rect.Top,[int]$rect.Width,[int]$rect.Height)
}
