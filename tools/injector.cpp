#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv)
{
    if (argc < 3) { printf("usage: injector.exe PID dllpath\n"); return 1; }
    DWORD pid = (DWORD)atoi(argv[1]);
    HANDLE h = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!h) { printf("OpenProcess failed %lu\n", GetLastError()); return 1; }
    size_t len = strlen(argv[2]) + 1;
    void* mem = VirtualAllocEx(h, 0, len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!mem) { printf("VirtualAllocEx failed %lu\n", GetLastError()); return 1; }
    if (!WriteProcessMemory(h, mem, argv[2], len, 0)) { printf("WriteProcessMemory failed\n"); return 1; }
    HMODULE k = GetModuleHandleA("kernel32.dll");
    void* load = (void*)GetProcAddress(k, "LoadLibraryA");
    HANDLE t = CreateRemoteThread(h, 0, 0, (LPTHREAD_START_ROUTINE)load, mem, 0, 0);
    if (!t) { printf("CreateRemoteThread failed %lu\n", GetLastError()); return 1; }
    WaitForSingleObject(t, 10000);
    DWORD code = 0;
    GetExitCodeThread(t, &code);
    printf("injected, exit=%lu\n", code);
    return 0;
}
