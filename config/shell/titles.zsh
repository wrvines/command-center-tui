# Safe to source repeatedly in an existing command-center zsh pane.
[[ -o interactive && -n ${ZELLIJ:-} ]] || return 0
autoload -Uz add-zsh-hook
_cc_title() {
    local label=${1//[[:cntrl:]]/}
    builtin printf '\033]2;%s\007' "${label[1,80]}"
}
_cc_title_prompt() {
    _cc_title zsh
    return 0
}
_cc_title_command() {
    local -a words
    local label
    words=(${(z)1})
    # Lex only; never evaluate the command or display its arguments.
    while (( ${#words} )) && [[ $words[1] =~ '^[A-Za-z_][A-Za-z0-9_]*=' ]]; do
        shift words
    done
    (( ${#words} )) || return 0
    label=${(Q)words[1]}
    if [[ ${label:t} == command-center || ${label:t} == ccenter ]]; then
        if [[ ${words[2]:-} == run || ${words[2]:-} == pane ]]; then
            label=${words[3]:-command-center}
        fi
    fi
    _cc_title "${label:t}"
    return 0
}
add-zsh-hook precmd _cc_title_prompt
add-zsh-hook preexec _cc_title_command
_cc_title_prompt
