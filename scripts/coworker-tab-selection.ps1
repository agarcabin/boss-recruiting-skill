# Keep positive selection evidence from the tab when examining its ancestors.
function Test-CoworkerTabSelection([bool]$AlreadySelected, [bool]$PatternSelected, [string]$ClassName) {
    return ($AlreadySelected -or $PatternSelected -or
        $ClassName -match '(^|\s)(active|selected|is-active|is-selected)(\s|$)')
}
