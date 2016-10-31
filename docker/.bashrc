#!/usr/bin/env bash

path_extend() {
    if [ -d "$1" ]; then
        val=${1:-" "};
        script="import os; env = os.environ; path = env['PATH'].split(':'); path.append('$val' if '$val' not in path else ''); path=':'.join(p for p in path if p.strip()); print(path)";
        new_path=$(python -c "$script");
        # echo "----------------------------------------"
        # echo " Adding: $1"
        # echo "----------------------------------------"
        # echo "before: $PATH"
        PATH=$new_path;
        # echo " after: $PATH"
        # echo "----------------------------------------"
        export PATH;
    fi
}


path_insert() {
    if [ -d "$1" ]; then
        val=${1:-" "};
        script="import os; env = os.environ; path = env['PATH'].split(':'); path.insert(0, '$val' if '$val' not in path else ''); path=':'.join(p for p in path if p.strip()); print(path)";
        new_path=$(python -c "$script");
        # echo "----------------------------------------"
        # echo " Inserting: $1"
        # echo "----------------------------------------"
        # echo "before: $PATH"
        PATH=$new_path;
        # echo " after: $PATH"
        # echo "----------------------------------------"
        export PATH;
    fi
}

path_insert "/sbin"
path_insert "/usr/sbin"
path_insert "/bin"
path_insert "/usr/bin"
path_insert "/usr/local/bin"

# BEGIN ANSIBLE MANAGED BLOCK
if [ -s ~/.envrc ]; then source ~/.envrc; fi
if [ -s ~/.bin/tmuxinator.zsh ]; then source ~/.bin/tmuxinator.zsh; fi

# Setup prompt colors
reset_color="\[\e[m\]"
declare -A fg
magenta="\[\e[35m\]"
yellow="\[\e[33m\]"

function virtualenv_prompt() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "(${magenta}vex:${reset_color}${yellow}${VIRTUAL_ENV##*/}$reset_color) "
    fi
}

export PS1="$(virtualenv_prompt)${PS1}"
# END ANSIBLE MANAGED BLOCK
