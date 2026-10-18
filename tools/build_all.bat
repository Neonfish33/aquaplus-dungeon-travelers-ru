@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d "%~dp0"
cl /nologo /LD /EHsc /O2 hookfont.cpp /Fe:hookfont.dll /link /MACHINE:X86 kernel32.lib
cl /nologo /EHsc /O2 injector.cpp /Fe:injector.exe /link /MACHINE:X86 kernel32.lib
