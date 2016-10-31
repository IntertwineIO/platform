export ZSH=$HOME/.oh-my-zsh
ZSH_THEME="robbyrussell"
HIST_STAMPS="yyyy-mm-dd"
plugins=(git osx python virtualenv pip zsh-completions)

alias pip='noglob pip'
alias tox='noglob tox'
source $ZSH/oh-my-zsh.sh

setopt append_history           # append
setopt hist_ignore_all_dups     # no duplicate
unsetopt hist_ignore_space      # ignore space prefixed commands
setopt hist_reduce_blanks       # trim blanks

# For ZSH-Completions
autoload -U compinit && compinit

# Modifying prompt for vex and virtualenv
setopt prompt_subst

function virtualenv_prompt() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "(%{$fg[magenta]%}vex:%{$reset_color%}%{$fg[yellow]%}${VIRTUAL_ENV##*/}%{$reset_color%}) "
    fi
}
export PROMPT="$(virtualenv_prompt)${PROMPT}"
eval "$(vex --shell-config zsh)"
