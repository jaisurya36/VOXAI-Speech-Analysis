Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice.SetOutputToWaveFile('tests\sample_speech.wav')
$voice.Speak('Hello, this is a test of counterpointing speech analytics and temporal flaw finding.')
$voice.Dispose()
Write-Output "Done"
