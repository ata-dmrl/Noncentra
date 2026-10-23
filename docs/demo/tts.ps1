# Turkish narration with the Windows voice (Microsoft Tolga, tr-TR).
# usage: powershell -File docs/demo/tts.ps1 <lines.json> <out_dir>
# lines.json: [{"id": "...", "say": "..."}]  ->  <out_dir>/<id>.wav
param([string]$Lines, [string]$OutDir)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$asTask = $asTask.MakeGenericMethod([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$synth.Voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
    Where-Object { $_.Language -eq 'tr-TR' } | Select-Object -First 1
$synth.Options.SpeakingRate = 1.08
foreach ($line in (Get-Content -Raw -Encoding UTF8 $Lines | ConvertFrom-Json)) {
    $task = $asTask.Invoke($null, @($synth.SynthesizeTextToStreamAsync($line.say)))
    $task.Wait()
    $src = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($task.Result)
    $dst = [System.IO.File]::Create((Join-Path $OutDir "$($line.id).wav"))
    $src.CopyTo($dst)
    $dst.Close()
}
