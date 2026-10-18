#include <windows.h>
#include <stdio.h>

#define FG_ADDR     0x00447950u
#define FG_BACK     0x0044795Au
#define FG_STOLEN   10

static FILE* g_log;
static BYTE* g_tramp;
static int g_cursor, g_lastX, g_y = -1;

static const int g_w[256] = {
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,14,12,16,36,32,46,25,9,20,20,24,30,13,26,12,24,38,16,30,31,36,32,33,31,32,33,12,13,24,25,32,30,0,36,31,32,36,28,38,25,28,30,43,27,31,34,30,34,30,32,28,32,30,45,31,43,33,31,27,15,0,15,36,34,0,25,27,27,32,25,39,19,24,25,34,22,28,31,25,27,24,26,26,25,25,37,26,36,27,27,24,38,34,26,30,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
};

static void logf(const char* s)
{
    if (!g_log) return;
    fprintf(g_log, "%s\n", s);
    fflush(g_log);
}

__declspec(naked) void HookFG()
{
    __asm {
        pushad
        mov edx, [esp+0x28]
        mov eax, [esp+0x2C]
        mov ebx, [esp+0x30]
        cmp ebx, g_y
        jne reset
        cmp eax, g_lastX
        jg  cont
    reset:
        mov g_cursor, eax
        mov g_y, ebx
    cont:
        mov ecx, g_cursor
        mov [esp+0x2C], ecx
        mov ecx, edx
        and ecx, 255
        mov ecx, [g_w + ecx*4]
        add g_cursor, ecx
        mov g_lastX, eax
        popad
        mov eax, g_tramp
        jmp eax
    }
}

static void install_fg(void)
{
    DWORD old;
    g_tramp = (BYTE*)VirtualAlloc(0, 0x40, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!g_tramp) return;
    memcpy(g_tramp, (void*)FG_ADDR, FG_STOLEN);
    g_tramp[FG_STOLEN] = 0xE9;
    *(int*)(g_tramp + FG_STOLEN + 1) = (int)FG_BACK - (int)(g_tramp + FG_STOLEN + 5);
    if (!VirtualProtect((void*)FG_ADDR, 16, PAGE_EXECUTE_READWRITE, &old)) return;
    ((BYTE*)FG_ADDR)[0] = 0xE9;
    *(int*)((BYTE*)FG_ADDR + 1) = (int)HookFG - (int)(FG_ADDR + 5);
    FlushInstructionCache(GetCurrentProcess(), (void*)FG_ADDR, 16);
    logf("cursor hook installed");
}

static DWORD WINAPI Main(LPVOID)
{
    g_log = fopen("C:\\Users\\yagan\\Downloads\\DungeonTravelers2_EN\\hookfont.log", "a");
    logf("=== hookfont loaded ===");
    install_fg();
    return 0;
}

BOOL APIENTRY DllMain(HMODULE h, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        CreateThread(0, 0, Main, 0, 0, 0);
    }
    return TRUE;
}
