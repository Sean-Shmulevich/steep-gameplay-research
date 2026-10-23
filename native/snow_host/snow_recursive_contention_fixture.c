/* Authored OS-thread critical-section test. No game code, hooks or payloads. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct Shared { CRITICAL_SECTION cs; volatile LONG inside, violations, order; } Shared;
typedef struct Worker { Shared *s; HANDLE ready, acquired, release, thread; LONG order; BOOL refused; } Worker;
static FILE *out;
static void fail(const char *stage) {
    fprintf(out,"{\"passed\":false,\"stage\":\"%s\"}\n",stage); fflush(out); ExitProcess(1);
}
static void require(BOOL yes,const char *stage) { if(!yes) fail(stage); }
static DWORD WINAPI worker(void *arg) {
    Worker *w=(Worker *)arg;
    w->refused=!TryEnterCriticalSection(&w->s->cs);
    if(!w->refused) LeaveCriticalSection(&w->s->cs);
    SetEvent(w->ready);
    EnterCriticalSection(&w->s->cs);
    if(InterlockedIncrement(&w->s->inside)!=1) InterlockedIncrement(&w->s->violations);
    w->order=InterlockedIncrement(&w->s->order);
    SetEvent(w->acquired);
    if(WaitForSingleObject(w->release,5000)!=WAIT_OBJECT_0) fail("worker_release_timeout");
    InterlockedDecrement(&w->s->inside);
    LeaveCriticalSection(&w->s->cs);
    return 0;
}
int main(int argc,char **argv) {
    out=argc>1?fopen(argv[1],"wb"):stdout;
    if(!out) return 2;
    const int depths[]={1,2,3,8}; unsigned scenarios=0;
    for(unsigned d=0;d<4;d++) for(int n=1;n<=2;n++) {
        Shared s={0}; Worker w[2]={0}; HANDLE ready[2],acquired[2];
        InitializeCriticalSection(&s.cs);
        for(int j=0;j<depths[d];j++) EnterCriticalSection(&s.cs);
        s.inside=1;
        for(int i=0;i<n;i++) {
            w[i].s=&s;
            w[i].ready=ready[i]=CreateEventA(NULL,TRUE,FALSE,NULL);
            w[i].acquired=acquired[i]=CreateEventA(NULL,TRUE,FALSE,NULL);
            w[i].release=CreateEventA(NULL,TRUE,FALSE,NULL);
            require(ready[i]&&acquired[i]&&w[i].release,"create_events");
            w[i].thread=CreateThread(NULL,0,worker,&w[i],0,NULL);
            require(w[i].thread!=NULL,"create_thread");
        }
        require(WaitForMultipleObjects(n,ready,TRUE,5000)==WAIT_OBJECT_0,"workers_ready");
        for(int i=0;i<n;i++) require(w[i].refused,"foreign_try_enter_refused");
        for(int j=depths[d]-1;j>0;j--) {
            LeaveCriticalSection(&s.cs);
            require(WaitForMultipleObjects(n,acquired,FALSE,20)==WAIT_TIMEOUT,"partial_release_stays_owned");
        }
        require(s.order==0,"no_acquisition_before_final_release");
        s.inside=0; LeaveCriticalSection(&s.cs);
        for(int rank=1;rank<=n;rank++) {
            DWORD idx=WaitForMultipleObjects(n,acquired,FALSE,5000)-WAIT_OBJECT_0;
            require(idx<(DWORD)n,"wait_for_handoff");
            require(w[idx].order==rank,"handoff_sequence");
            ResetEvent(acquired[idx]);
            SetEvent(w[idx].release);
            require(WaitForSingleObject(w[idx].thread,5000)==WAIT_OBJECT_0,"worker_complete");
        }
        require(s.inside==0&&s.violations==0&&s.order==n,"exclusive_and_balanced");
        require(TryEnterCriticalSection(&s.cs),"main_reacquires_after_workers");
        LeaveCriticalSection(&s.cs);
        for(int i=0;i<n;i++) { CloseHandle(w[i].thread);CloseHandle(w[i].ready);CloseHandle(w[i].acquired);CloseHandle(w[i].release); }
        DeleteCriticalSection(&s.cs);scenarios++;
    }
    fprintf(out,"{\"passed\":true,\"scenarios\":%u,\"real_os_threads\":true,\"game_loaded\":false,\"fairness_claimed\":false}\n",scenarios);
    fflush(out); if(out!=stdout) fclose(out); return 0;
}
