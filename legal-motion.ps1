param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
python -m legal_auto_motion.cli @Arguments
exit $LASTEXITCODE
