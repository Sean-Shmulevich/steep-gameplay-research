#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <stdio.h>
int main(void){
    EXCEPTION_RECORD r={0};CONTEXT c={0};EXCEPTION_POINTERS e={&r,&c};
    assert(snow_first_execute_classify(NULL,0x10000,4096)==1);
    e.ContextRecord=NULL;assert(snow_first_execute_classify(&e,0x10000,4096)==1);e.ContextRecord=&c;
    assert(snow_first_execute_classify(&e,0x10000,4096)==2);
    r.ExceptionCode=EXCEPTION_ACCESS_VIOLATION;
    assert(snow_first_execute_classify(&e,0x10000,4096)==3);
    r.NumberParameters=2;r.ExceptionFlags=EXCEPTION_NONCONTINUABLE;
    assert(snow_first_execute_classify(&e,0x10000,4096)==4);
    r.ExceptionFlags=0;
    assert(snow_first_execute_classify(&e,0x10000,4096)==5);
    r.ExceptionInformation[0]=8;r.ExceptionInformation[1]=0xffff;
    assert(snow_first_execute_classify(&e,0x10000,4096)==6);
    r.ExceptionInformation[1]=0x11000;
    assert(snow_first_execute_classify(&e,0x10000,4096)==6);
    r.ExceptionInformation[1]=0x10000;c.Rip=0xffff;
    assert(snow_first_execute_classify(&e,0x10000,4096)==0);
    c.Rip=0xfff1;assert(snow_first_execute_classify(&e,0x10000,4096)==7);
    c.Rip=0xfff2;assert(snow_first_execute_classify(&e,0x10000,4096)==0);
    c.Rip=0x11000;assert(snow_first_execute_classify(&e,0x10000,4096)==7);
    c.Rip=0x10000;assert(snow_first_execute_classify(&e,0x10000,4096)==0);
    c.Rip=0x10fff;r.ExceptionInformation[1]=0x10fff;
    assert(snow_first_execute_classify(&e,0x10000,4096)==0);
    assert(snow_first_execute_classify(&e,0x10000,0)==6);
    puts("15 classifier cases passed");return 0;
}
