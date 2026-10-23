#include "../../native/snow_host/examples/protection_api_snapshot.c"
#include <assert.h>
int main(int argc,char **argv){
    assert(argc==2);unsigned char *page=VirtualAlloc(NULL,8192,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(page);
    DWORD old;assert(VirtualProtect(page+4096,4096,PAGE_NOACCESS,&old));
    FILE *f=fopen(argv[1],"w");assert(f);fputc('[',f);
    const char *names[]={"rel32","rel8","indirect","rex_indirect","absolute","cycle","limit","unreadable_slot","unreadable_entry","wine_prefix"};
    for(unsigned i=0;i<10;i++){
        memset(page,0x90,4096);uintptr_t target=(uintptr_t)(page+128);int32_t disp;
        if(i==0){page[0]=0xe9;disp=123;memcpy(page+1,&disp,4);}
        if(i==1){page[0]=0xeb;page[1]=126;}
        if(i==2 || i==3 || i==7){
            unsigned prefix=i==3;page[0]=prefix?0x48:0xff;page[prefix]=0xff;page[1+prefix]=0x25;
            disp=(i==7?4096:96)-6-prefix;memcpy(page+2+prefix,&disp,4);memcpy(page+96,&target,8);
        }
        if(i==4){page[0]=0x48;page[1]=0xb8;memcpy(page+2,&target,8);page[10]=0xff;page[11]=0xe0;}
        if(i==5){page[0]=0xeb;page[1]=0xfe;}
        if(i==6)for(unsigned j=0;j<5;j++){page[128*j]=0xe9;disp=123;memcpy(page+128*j+1,&disp,4);}
        if(i==9){
            const unsigned char prefix[]={0x48,0x8d,0xa4,0x24,0,0,0,0};memcpy(page,prefix,8);
            page[8]=0xff;page[9]=0x25;disp=82;memcpy(page+10,&disp,4);memcpy(page+96,&target,8);
        }
        fprintf(f,"%s{\"case\":\"%s\",\"route\":",i?",":"",names[i]);route(f,(uintptr_t)(i==8?page+4096:page));fputc('}',f);
    }
    fputs("]\n",f);
    fclose(f);return 0;
}
