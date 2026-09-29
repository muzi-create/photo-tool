; Ensure an in-place upgrade refreshes the bundled Python sidecar.
; NSIS can otherwise retain an existing resource file when the main executable
; is updated, leaving the desktop shell paired with stale frontend assets.
!macro NSIS_HOOK_PREINSTALL
  Delete "$INSTDIR\_up_\build\tauri-resources\sidecar\PhotoToolSidecar.exe"
  Delete "$INSTDIR\_up_\dist\sidecar\PhotoToolSidecar.exe"
!macroend
