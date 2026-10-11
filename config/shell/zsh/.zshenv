# Restore normal startup lookup immediately, then defer integration until prompt time.
if [[ -n ${CC_ORIGINAL_ZDOTDIR_SET:-} ]]; then
    export ZDOTDIR=$CC_ORIGINAL_ZDOTDIR
else
    unset ZDOTDIR
fi
unset CC_ORIGINAL_ZDOTDIR CC_ORIGINAL_ZDOTDIR_SET
if [[ -r ${ZDOTDIR-$HOME}/.zshenv ]]; then
    source "${ZDOTDIR-$HOME}/.zshenv"
fi
if [[ -o interactive && -n ${ZELLIJ:-} ]]; then
    autoload -Uz add-zsh-hook
    _cc_init_titles() {
        add-zsh-hook -d precmd _cc_init_titles
        source "$CC_ROOT/config/shell/titles.zsh"
    }
    add-zsh-hook precmd _cc_init_titles
fi
