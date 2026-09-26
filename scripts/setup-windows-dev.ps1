# One-time local dev setup for Windows (no Docker required).
# Installs MSYS2 + the UCRT64 Pango stack needed by WeasyPrint.
# Django dev settings register C:\msys64\ucrt64\bin via os.add_dll_directory.

$ErrorActionPreference = "Stop"

if (-not (Test-Path "C:\msys64\msys2_shell.cmd")) {
    Write-Host "Installing MSYS2 via winget..."
    winget install --id MSYS2.MSYS2 -e --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "MSYS2 already installed."
}

Write-Host "Installing Pango (UCRT64)..."
& C:\msys64\usr\bin\bash.exe -lc "pacman -Sy --noconfirm --needed mingw-w64-ucrt-x86_64-pango"

$dll = "C:\msys64\ucrt64\bin\libpango-1.0-0.dll"
if (Test-Path $dll) {
    Write-Host "OK: $dll present. Run 'uv run python -c \"import weasyprint\"' in backend/ to verify."
} else {
    Write-Warning "Pango DLL not found at $dll — check the pacman output above."
}
