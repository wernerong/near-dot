; Preserve startup registration during updater replacement; remove our own
; per-user OS startup override only on an explicit uninstall.
!macro NSIS_HOOK_POSTUNINSTALL
  ${If} $UpdateMode <> 1
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Near Dot"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" "Near Dot"
  ${EndIf}
!macroend
