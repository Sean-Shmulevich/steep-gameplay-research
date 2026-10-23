// Authored file-trigger gate. This class does not send input or select a process.
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
public static class ArmedInputGate {
    public static void Wait(string ready, string trigger, int timeoutMs, Action validate) {
        if(timeoutMs<1 || timeoutMs>30000 || validate==null)throw new ArgumentException("Invalid bounded gate");
        ready=Path.GetFullPath(ready);trigger=Path.GetFullPath(trigger);
        if(String.Equals(ready,trigger,StringComparison.OrdinalIgnoreCase) || File.Exists(trigger))
            throw new InvalidOperationException("Trigger must be fresh and distinct");
        validate();
        using(var f=new FileStream(ready,FileMode.CreateNew,FileAccess.Write,FileShare.Read)) {
            byte[] bytes=System.Text.Encoding.ASCII.GetBytes("ready\n");f.Write(bytes,0,bytes.Length);
        }
        var clock=Stopwatch.StartNew();
        for(;;) {
            validate();
            if(clock.ElapsedMilliseconds>=timeoutMs)throw new TimeoutException("Input arm expired");
            if(File.Exists(trigger)) {validate();return;}
            Thread.Sleep(5);
        }
    }
}
