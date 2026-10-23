using System;
using System.IO;
using System.Threading;
class ArmedGateFixture {
    static void Check(bool ok) {if(!ok)throw new Exception("fixture assertion");}
    static bool Refused(Action run) {try{run();return false;}catch{return true;}}
    static int Main() {
        string dir=Path.Combine(Path.GetTempPath(),"snow-arm-"+Guid.NewGuid());Directory.CreateDirectory(dir);
        try {
            string ready=Path.Combine(dir,"ready"),trigger=Path.Combine(dir,"trigger");
            int guards=0;bool released=false;
            var writer=new Thread(()=>{while(!File.Exists(ready))Thread.Sleep(1);Thread.Sleep(30);Check(!released);File.WriteAllText(trigger,"go");});
            writer.Start();ArmedInputGate.Wait(ready,trigger,2000,()=>{Interlocked.Increment(ref guards);});released=true;writer.Join();Check(guards>=2);
            Check(Refused(()=>ArmedInputGate.Wait(ready,trigger,100,()=>{})));
            File.Delete(trigger);File.Delete(ready);
            Check(Refused(()=>ArmedInputGate.Wait(ready,trigger,20,()=>{})));Check(!File.Exists(trigger));
            File.Delete(ready);int calls=0;
            Check(Refused(()=>ArmedInputGate.Wait(ready,trigger,100,()=>{if(++calls==2)throw new Exception("target invalid");})));
            Check(calls==2);Check(Refused(()=>ArmedInputGate.Wait(ready,ready,100,()=>{})));
            Console.WriteLine("PASS: readiness precedes release, fresh trigger, timeout and target invalidation");return 0;
        } finally {Directory.Delete(dir,true);}
    }
}
