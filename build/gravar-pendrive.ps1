# Grava uma imagem .img do Brisa Suave OS num pendrive, no Windows.
# APAGA TUDO o que estiver no pendrive. Precisa rodar como administrador.
#
#   powershell -ExecutionPolicy Bypass -File build\gravar-pendrive.ps1 -Imagem saida\brisa-suave-os-btv11.img -Disco 2
#
# Travas de segurança: só grava em disco USB, que não seja o disco do sistema,
# com no máximo 64 GB e maior que a imagem.
param(
    [Parameter(Mandatory = $true)][string]$Imagem,
    [Parameter(Mandatory = $true)][int]$Disco,
    [string]$Registro = "$env:TEMP\brisa-gravar-pendrive.log",
    [switch]$SoConferir   # não grava: só compara o pendrive com a imagem
)
$ErrorActionPreference = 'Stop'
function Escrever($texto) { $linha = "$(Get-Date -Format 'HH:mm:ss') $texto"; Write-Host $linha; Add-Content -Path $Registro -Value $linha -Encoding UTF8 }

try {
    Set-Content -Path $Registro -Value "Brisa Suave OS: gravação de pendrive" -Encoding UTF8
    $adm = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $adm) { throw "precisa rodar como administrador" }

    $arquivo = Get-Item -LiteralPath $Imagem
    $d = Get-Disk -Number $Disco
    Escrever "Disco $Disco : $($d.FriendlyName) | $($d.BusType) | $([math]::Round($d.Size/1GB,1)) GB"
    if ($d.BusType -ne 'USB') { throw "o disco $Disco não é USB. Nada foi gravado." }
    if ($d.IsBoot -or $d.IsSystem) { throw "o disco $Disco é do sistema. Nada foi gravado." }
    if ($d.Size -gt 64GB) { throw "o disco $Disco tem mais de 64 GB (não parece um pendrive). Nada foi gravado." }
    if ($d.Size -lt $arquivo.Length) { throw "a imagem ($([math]::Round($arquivo.Length/1GB,1)) GB) não cabe no disco $Disco." }
    if ($arquivo.Length % 512 -ne 0) { throw "tamanho da imagem não é múltiplo de 512 bytes." }

    if (-not $SoConferir) {
    Escrever "Apagando o disco $Disco..."
    Get-Partition -DiskNumber $Disco -ErrorAction SilentlyContinue | Where-Object DriveLetter | ForEach-Object {
        Remove-PartitionAccessPath -DiskNumber $Disco -PartitionNumber $_.PartitionNumber -AccessPath "$($_.DriveLetter):\" -ErrorAction SilentlyContinue }
    Clear-Disk -Number $Disco -RemoveData -RemoveOEM -Confirm:$false -ErrorAction SilentlyContinue
    Set-Disk -Number $Disco -IsOffline $true -ErrorAction SilentlyContinue
    Start-Sleep 2

    Escrever "Gravando $($arquivo.Name) ($([math]::Round($arquivo.Length/1MB)) MB)..."
    $bloco = 4MB
    $buffer = New-Object byte[] $bloco
    $origem = [IO.File]::OpenRead($arquivo.FullName)
    $destino = New-Object IO.FileStream("\\.\PhysicalDrive$Disco", [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite, $bloco, [IO.FileOptions]::WriteThrough)
    $total = 0; $ultimo = -1
    while (($lidos = $origem.Read($buffer, 0, $bloco)) -gt 0) {
        if ($lidos % 512 -ne 0) { $lidos = [int]([math]::Ceiling($lidos / 512) * 512) }
        $destino.Write($buffer, 0, $lidos)
        $total += $lidos
        $pct = [int](100 * $total / $arquivo.Length)
        if ($pct -ne $ultimo -and $pct % 5 -eq 0) { Escrever "  $pct%"; $ultimo = $pct }
    }
    $destino.Flush(); $destino.Close(); $origem.Close()
    }

    # Confere a imagem inteira, de 4 MB em 4 MB (as partes vazias também)
    Escrever "Conferindo o pendrive inteiro com a imagem..."
    $bloco = 4MB
    $a = New-Object byte[] $bloco; $b = New-Object byte[] $bloco
    $sha = [Security.Cryptography.SHA256]::Create()
    $f1 = [IO.File]::OpenRead($arquivo.FullName)
    $f2 = New-Object IO.FileStream("\\.\PhysicalDrive$Disco", [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite, $bloco)
    [long]$conferido = 0; $ultimo = -1
    while (($n = $f1.Read($a, 0, $bloco)) -gt 0) {
        $m = [int]([math]::Ceiling($n / 512) * 512)
        $lido = 0
        while ($lido -lt $m) { $r = $f2.Read($b, $lido, $m - $lido); if ($r -le 0) { break }; $lido += $r }
        $ha = [BitConverter]::ToString($sha.ComputeHash($a, 0, $n))
        $hb = [BitConverter]::ToString($sha.ComputeHash($b, 0, $n))
        if ($ha -ne $hb) { $f1.Close(); $f2.Close(); throw "a conferência falhou perto de $([math]::Round($conferido/1MB)) MB: o pendrive não ficou igual à imagem." }
        $conferido += $n
        $pct = [int](100 * $conferido / $arquivo.Length)
        if ($pct -ne $ultimo -and $pct % 10 -eq 0) { Escrever "  conferido $pct%"; $ultimo = $pct }
    }
    $f1.Close(); $f2.Close()
    Set-Disk -Number $Disco -IsOffline $false -ErrorAction SilentlyContinue
    Escrever "PRONTO: gravado e conferido. Pode tirar o pendrive."
    Escrever "Se o Windows pedir para formatar o pendrive, clique em CANCELAR."
}
catch {
    Escrever "ERRO: $($_.Exception.Message)"
    Set-Disk -Number $Disco -IsOffline $false -ErrorAction SilentlyContinue
    exit 1
}
