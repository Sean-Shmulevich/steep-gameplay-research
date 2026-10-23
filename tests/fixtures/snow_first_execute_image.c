#include <stdint.h>
#ifndef SNOW_FIXTURE_RESULT
#define SNOW_FIXTURE_RESULT 42
#endif
#define SNOW_STRING_INNER(x) #x
#define SNOW_STRING(x) SNOW_STRING_INNER(x)
/* Authored fixture functions, never game instructions. Compile with
 * -fno-toplevel-reorder so both exported entries share a dedicated code page. */
__declspec(dllexport) __attribute__((naked,aligned(4096))) uint64_t snow_execute_target(void){
    __asm__("mov $" SNOW_STRING(SNOW_FIXTURE_RESULT) ", %eax; ret");
}
__declspec(dllexport) __attribute__((naked,aligned(64))) uint64_t snow_execute_neighbor(void){
    __asm__("mov $99, %eax; ret");
}
__attribute__((naked,aligned(4096),used)) void snow_execute_end(void){__asm__("ret");}
