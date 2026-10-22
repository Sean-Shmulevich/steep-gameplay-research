/* Launch the original game normally, load/start the host as soon as its Windows
 * loader is available, and remain its parent until exit. No DLL replacement,
 * suspension, debugger, or game instruction patches. Not a pre-entrypoint hook.
 * Usage: startup_launcher.exe <absolute game.exe> <absolute snow_host.dll> <port>
 * The bootstrap report lives beside snow_host.dll. */
#define SNOW_REMOTE_TIMEOUT_MS 30000
#define wmain snow_checked_load_host
#include "host_loader.c"
#undef wmain

static FILE *report;
static ULONGLONG begun;
static DWORD child_pid;
static int visible_count;
static BOOL CALLBACK count_window(HWND w, LPARAM unused) {
    (void)unused; DWORD pid = 0; GetWindowThreadProcessId(w, &pid);
    if (pid == child_pid && IsWindowVisible(w)) visible_count++;
    return TRUE;
}
static int visible(void) { visible_count = 0; EnumWindows(count_window, 0); return visible_count; }
static void record(const char *phase, int ok, int windows) {
    if (!report) return;
    fprintf(report, "{\"phase\":\"%s\",\"ok\":%s,\"elapsed_ms\":%llu,\"pid\":%lu,\"visible_windows\":%d}\n",
            phase, ok ? "true" : "false", (unsigned long long)(GetTickCount64()-begun), child_pid, windows);
    fflush(report);
}
int wmain(int argc, WCHAR **argv) {
    if (argc != 4 || wcslen(argv[1]) >= MAX_PATH || wcslen(argv[2]) >= MAX_PATH ||
        (_wcsicmp(base(argv[1]), L"steep.exe") && _wcsicmp(base(argv[1]), L"late_fixture.exe")) ||
        _wcsicmp(base(argv[2]), L"snow_host.dll")) return 2;
    WCHAR report_path[MAX_PATH], cwd[MAX_PATH], command[2*MAX_PATH];
    wcscpy(report_path, argv[2]); WCHAR *sep = wcsrchr(report_path, L'\\');
    if (!sep || (size_t)(sep-report_path)+25 >= MAX_PATH) return 2;
    wcscpy(sep+1, L"snow_startup.jsonl"); report = _wfopen(report_path, L"w");
    if (!report) return 2;
    wcscpy(cwd, argv[1]); sep = wcsrchr(cwd, L'\\');
    if (!sep) { fclose(report); return 2; } *sep = 0;
    _snwprintf(command, 2*MAX_PATH, L"\"%ls\"", argv[1]);
    STARTUPINFOW si = {0}; si.cb = sizeof si; PROCESS_INFORMATION pi = {0};
    begun = GetTickCount64();
    if (!CreateProcessW(argv[1], command, NULL, NULL, FALSE, 0, NULL, cwd, &si, &pi)) {
        record("create_process", 0, 0); fclose(report); return 3;
    }
    child_pid = pi.dwProcessId; CloseHandle(pi.hThread);
    record("created", 1, visible());
    MODULEENTRY32W m; ULONGLONG deadline = GetTickCount64()+15000;
    while (!module(child_pid, L"kernel32.dll", &m) && GetTickCount64()<deadline && WaitForSingleObject(pi.hProcess, 25)==WAIT_TIMEOUT) {}
    FILETIME c,e,k,u; WCHAR pid[32],created[32]; int load_rc = 2;
    if (module(child_pid, L"kernel32.dll", &m) && GetProcessTimes(pi.hProcess,&c,&e,&k,&u)) {
        _snwprintf(pid,32,L"%lu",child_pid);
        _snwprintf(created,32,L"%llx",((unsigned long long)c.dwHighDateTime<<32)|c.dwLowDateTime);
        WCHAR *load_args[] = {argv[0],pid,created,argv[2],argv[3]};
        record("load_begin", 1, visible());
        load_rc = snow_checked_load_host(5,load_args);
        fflush(stdout);
        record("host_started", load_rc==0, visible());
    } else record("loader_unavailable",0,visible());
    fclose(report);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code=0; GetExitCodeProcess(pi.hProcess,&code); CloseHandle(pi.hProcess);
    return load_rc ? load_rc : (int)code;
}
