!macro NSIS_HOOK_POSTINSTALL
  CreateShortcut "$DESKTOP\咕咕PDF工具箱.lnk" "$INSTDIR\gugu-pdf-tools.exe"
!macroend