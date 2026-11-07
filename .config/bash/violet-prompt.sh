# Zorin Violet interactive Bash prompt.
if [[ $- == *i* && $TERM != dumb ]]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[1;32m\]┌──(\[\033[1;31m\]\u@\h\[\033[1;32m\])-[\[\033[1;37m\]\w\[\033[1;32m\]]\n└─\[\033[1;31m\]\$\[\033[0m\] '
fi
