# Graceful Chrome Management for Surfboard
# Prevents "Restore pages?" dialog by properly closing Chrome processes

function Close-ChromeGracefully {
    <#
    .SYNOPSIS
    Closes Google Chrome gracefully to prevent restore session dialogs

    .DESCRIPTION
    Uses CloseMainWindow() method first, then falls back to Stop-Process if needed.
    This prevents Chrome from showing "Restore pages?" dialog on next launch.
    #>

    Write-Host 'Closing Chrome gracefully...'

    # Step 1: Try graceful shutdown using CloseMainWindow()
    $chromeProcesses = Get-Process -Name chrome -ErrorAction SilentlyContinue
    if ($chromeProcesses) {
        Write-Host "Found $($chromeProcesses.Count) Chrome processes"

        # Close main windows first (this is key to avoiding restore dialog)
        $chromeProcesses | ForEach-Object {
            if ($_.MainWindowTitle -ne '') {
                Write-Host "Gracefully closing: '$($_.MainWindowTitle)' (PID: $($_.Id))"
                $_.CloseMainWindow() | Out-Null
            }
        }

        # Allow time for graceful shutdown
        Write-Host 'Waiting for graceful shutdown...'
        Start-Sleep -Seconds 5

        # Step 2: Check for remaining processes
        $remainingProcesses = Get-Process -Name chrome -ErrorAction SilentlyContinue
        if ($remainingProcesses) {
            Write-Host "Gently stopping remaining $($remainingProcesses.Count) processes"
            $remainingProcesses | Stop-Process
            Start-Sleep -Seconds 2

            # Step 3: Force close any stubborn processes
            $finalCheck = Get-Process -Name chrome -ErrorAction SilentlyContinue
            if ($finalCheck) {
                Write-Host "Force closing $($finalCheck.Count) stubborn processes"
                $finalCheck | Stop-Process -Force
            }
        } else {
            Write-Host '✅ All Chrome processes closed gracefully!'
        }
    } else {
        Write-Host 'No Chrome processes found'
    }

    Write-Host 'Chrome closure completed successfully'
}

function Start-ChromeWithProfile {
    <#
    .SYNOPSIS
    Launches Chrome with Windows user profile

    .DESCRIPTION
    Starts Chrome with the specified user data directory and profile
    #>
    param(
        [string]$UserDataDir = "C:\Users\Learn\AppData\Local\Google\Chrome\User Data",
        [string]$Profile = "Default"
    )

    Write-Host 'Launching Chrome with profile...'

    $process = Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList "--user-data-dir=`"$UserDataDir`"", "--profile-directory=$Profile", "--new-window" -PassThru

    Write-Host "Chrome launched with PID: $($process.Id)"
    return $process
}

function Test-ChromeGracefulCycle {
    <#
    .SYNOPSIS
    Tests complete Chrome launch/close cycle

    .DESCRIPTION
    Launches Chrome, waits, closes gracefully, and relaunches to verify no restore dialog
    #>

    Write-Host "=== Testing Chrome Graceful Management ==="

    # Launch Chrome
    $chrome = Start-ChromeWithProfile
    Start-Sleep -Seconds 5

    # Close gracefully
    Close-ChromeGracefully
    Start-Sleep -Seconds 2

    # Relaunch to test
    Write-Host "Relaunching to verify no restore dialog..."
    $chrome2 = Start-ChromeWithProfile
    Start-Sleep -Seconds 5

    Write-Host "✅ Chrome graceful management test completed"
    Write-Host "Check Chrome window - should have NO 'Restore pages?' dialog"

    return $chrome2
}

# Export functions for use in other scripts
Export-ModuleMember -Function Close-ChromeGracefully, Start-ChromeWithProfile, Test-ChromeGracefulCycle
