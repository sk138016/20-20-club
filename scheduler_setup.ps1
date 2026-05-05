# 20-20 Club — Windows 작업 스케줄러 등록
# 매년 3/15, 6/15, 9/15, 12/15 오전 09:00 에 스크리너를 자동 실행합니다.
# PowerShell 을 관리자 권한으로 실행한 후 이 스크립트를 실행하세요.
#
# 실행 방법:
#   powershell -ExecutionPolicy Bypass -File scheduler_setup.ps1

$ProjectDir = "C:\Users\rlatp\Documents\Claude\Projects\2. Stock Projects\1. 20-20 Club"
$BatchFile  = Join-Path $ProjectDir "run.bat"
$TaskBase   = "20-20Club"

if (-not (Test-Path $BatchFile)) {
    Write-Error "run.bat 을 찾을 수 없습니다: $BatchFile"
    exit 1
}

# 분기별 실행 월 및 레이블
$Quarters = @(
    @{ Label = "Q1-Mar15"; Month = 3  },
    @{ Label = "Q2-Jun15"; Month = 6  },
    @{ Label = "Q3-Sep15"; Month = 9  },
    @{ Label = "Q4-Dec15"; Month = 12 }
)

foreach ($q in $Quarters) {
    $TaskName = "$TaskBase-$($q.Label)"
    $Month    = $q.Month
    $MonthStr = $Month.ToString().PadLeft(2, '0')

    # 기존 작업 제거
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # XML 로 정확한 월별 반복 트리거 등록
    $Xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-${MonthStr}-15T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByYear>
        <DaysOfMonth>
          <Day>15</Day>
        </DaysOfMonth>
        <Months>
          <Month${Month}/>
        </Months>
      </ScheduleByYear>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c "$BatchFile"</Arguments>
      <WorkingDirectory>$ProjectDir</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <ExecutionTimeLimit>PT3H</ExecutionTimeLimit>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <RestartOnFailure>
      <Interval>PT30M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
</Task>
"@

    Register-ScheduledTask -TaskName $TaskName -Xml $Xml -Force | Out-Null
    Write-Host "등록 완료: $TaskName  (매년 ${Month}월 15일 09:00)"
}

Write-Host ""
Write-Host "등록된 작업 목록:"
Get-ScheduledTask | Where-Object { $_.TaskName -like "$TaskBase-*" } |
    Format-Table TaskName, State -AutoSize

Write-Host "즉시 테스트 실행:"
Write-Host "  Start-ScheduledTask -TaskName `"$TaskBase-Q1-Mar15`""
Write-Host ""
Write-Host "전체 작업 삭제:"
Write-Host "  Get-ScheduledTask | Where-Object { `$_.TaskName -like `"$TaskBase-*`" } | Unregister-ScheduledTask -Confirm:`$false"
