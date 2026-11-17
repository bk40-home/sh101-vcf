# A/B: TAL-BassLine-101 (sh101_capture.wav) against the FM-1 (M-Vsynth2 FILTER TYPE 5).
#   .\run_ab.ps1 -Fm1 "FM-1_updated 3-Audio.wav"    (Live adds the track's name to an export: quote the name)
# Writes tal\ and fm1\ (the takes and their analysis) and ab_report.md. Needs Python with numpy and scipy.
param([Parameter(Mandatory = $true)][string]$Fm1, [switch]$RedoTal)
Set-Location $PSScriptRoot
function Step($what) { Write-Host "== $what" }
function Check($what) { if ($LASTEXITCODE -ne 0) { Write-Host "STOPPED: $what failed (above)"; exit 1 } }

if (-not (Test-Path -LiteralPath $Fm1)) {
    Write-Host "STOPPED: '$Fm1' is not in this folder. The WAV files here:"
    Get-ChildItem *.wav | ForEach-Object { Write-Host "   $($_.Name)" }
    exit 1
}
if ($RedoTal -or -not (Test-Path "tal\analysis\calib.json")) {
    Step "TAL: cut sh101_capture.wav into takes, put in the two re-exports, measure"
    py split_takes.py sh101_capture.wav sh101_ab.timeline.json tal; Check "split (TAL)"
    Copy-Item T3_open.wav, T3_res0250.wav tal -Force
    py analyse.py tal tal\analysis; Check "analyse (TAL)"
} else { Step "TAL: already measured (tal\analysis\calib.json; -RedoTal to measure again)" }

Step "FM-1: $Fm1"
py -c "import sys, numpy as np, wave; w = wave.open(sys.argv[1]); n = w.getnframes(); s = w.getsampwidth(); b = np.frombuffer(w.readframes(min(n, 44100 * 60)), np.uint8); sys.exit(0 if b.size and np.abs(b.view(np.int16) if s == 2 else b.astype(np.int16) - 128).max() > (8 if s == 2 else 1) else 3)" "$Fm1"
if ($LASTEXITCODE -eq 3) { Write-Host "STOPPED: '$Fm1' is silent: the FM-1 was not recorded (check track 2's MIDI To and track 3's Audio From, and that the recorded clip shows a waveform)"; exit 1 }
if (Test-Path fm1) { Remove-Item fm1 -Recurse -Force }
py split_takes.py "$Fm1" sh101_ab.timeline.json fm1; Check "split (FM-1)"
py analyse.py fm1 fm1\analysis; Check "analyse (FM-1)"

Step "compare"
py compare_ab.py tal\analysis\calib.json fm1\analysis\calib.json sh101_ab.timeline.json ab_report.md; Check "compare"
Write-Host "done: ab_report.md"
