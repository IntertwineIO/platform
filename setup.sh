#!/usr/bin/env bash

# Script variables
PROJECT_NAME='intertwine'
PROJECT_FOLDER="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PORT=5000

# System packages
if [ "$(uname)" != "Darwin" ]; then
    brew update
    brew install --upgrade tmux
    brew install --upgrade  ruby
fi
gem install tmuxinator

# Python packages
pip install --upgrade pip
pip install --upgrade virtualenv


mkdir -p ~/.tmuxinator

read -r -d '' TMUX_CONF << EOF
# Use ZSH
set -g utf8
set-window-option -g utf8 on
# set-option -g default-shell /bin/bash
# set-option -g default-command "reattach-to-user-namespace -l bash"
# set -g default-terminal "screen-256color"
set -g status-interval 5

# for tmuxinator
set -g base-index 1
set -g pane-base-index 1

# default statusbar colors
set-option -g status-bg colour235 #base02
set-option -g status-fg colour136 #yellow
set-option -g status-attr default

# default window title colors
set-window-option -g window-status-fg colour244 #base0
set-window-option -g window-status-bg default
# set-window-option -g window-status-attr dim

# active window title colors
# set-window-option -g window-status-current-fg colour166 #orange
# set-window-option -g window-status-current-bg default
# set-window-option -g window-status-current-attr bright

# pane border
set-option -g pane-border-fg colour235 #base02
set-option -g pane-active-border-fg colour240 #base01

# message text
set-option -g message-bg colour235 #base02
set-option -g message-fg colour166 #orange

# pane number display
set-option -g display-panes-active-colour colour33 #blue
set-option -g display-panes-colour colour166 #orange

# clock
set-window-option -g clock-mode-colour colour64 #green

set-option -g status-left ' #[bold] #(hostname) '
set-option -g status-right '#[bold] %_d %b · %H:%M · %a'

set-option -g status-right-length 60
set-option -g status-left-length 60

## highlight active window
# set-window-option -g window-status-current-bg colour136
# set-window-option -g window-status-current-fg colour235
# set-window-option -g window-status-current-attr bold
# set-window-option -g window-status-current-format ' #I #W '


## set window notifications
set-option -g visual-activity on
# set-option -g visual-content on
set-window-option -g monitor-activity on

## tmux window titling for X
set-option -g set-titles on
set-option -g set-titles-string '[#I] #W'
set-window-option -g automatic-rename on
set-window-option -g window-status-format ' #I #W '
# set-window-option -g window-status-attr bold

## enable mouse
# Use option in iterm to disable mouse mode for clipboard
set -g mouse-utf8 on
set -g mouse on
bind -n WheelUpPane   select-pane -t= \; copy-mode -e \; send-keys -M
bind -n WheelDownPane select-pane -t= \;                 send-keys -M
# set-option -g mouse-resize-pane on
# set-option -g mouse-select-window on
# set-option -g mouse-select-pane on
# set-window-option -g mode-mouse on

# session history
set -g history-limit 30000

# Resizing
bind < resize-pane -L 4
bind > resize-pane -R 4
bind - resize-pane -D 4
bind + resize-pane -U 4

#### Color Scheme (Solarized 256)
# github:

# default statusbar colors
set-option -g status-bg colour235 #base02
set-option -g status-fg colour136 #yellow
set-option -g status-attr default

# default window title colors
set-window-option -g window-status-fg colour244 #base0
set-window-option -g window-status-bg default
#set-window-option -g window-status-attr dim

# active window title colors
set-window-option -g window-status-current-fg colour166 #orange
set-window-option -g window-status-current-bg default
#set-window-option -g window-status-current-attr bright

# pane border
set-option -g pane-border-fg colour235 #base02
set-option -g pane-active-border-fg colour240 #base01

# message text
set-option -g message-bg colour235 #base02
set-option -g message-fg colour166 #orange

# pane number display
set-option -g display-panes-active-colour colour33 #blue
set-option -g display-panes-colour colour166 #orange

# clock
set-window-option -g clock-mode-colour colour64 #green

# bell
set-window-option -g window-status-bell-style fg=colour235,bg=colour160 #base02, red
EOF

echo "$TMUX_CONF" > ~/.tmux.conf

read -r -d '' TMUXINATOR_SESSION << EOF
# ~/.tmuxinator/$PROJECT_NAME.yml

name: $PROJECT_NAME
root: ~/

windows:
  - $PROJECT_NAME:
      layout: 36f4,160x49,0,0[160x12,0,0,0,160x36,0,13,1]
      panes:
        - cd $PROJECT_FOLDER && source venv/bin/activate && ./run.py -p $PORT
        - cd $PROJECT_FOLDER && source venv/bin/activate

EOF
mkdir -p ~/.tmuxinator
echo "$TMUXINATOR_SESSION" > ~/.tmuxinator/$PROJECT_NAME.yml

cd $PROJECT_FOLDER && python -m virtualenv venv
cd $PROJECT_FOLDER && source venv/bin/activate && pip install -e . && pip install -e .[dev]

tmuxinator intertwine &

sleep 1

if [ "$(uname)" == "Darwin" ]; then
    open -a "Safari" http://localhost:$PORT &
fi

