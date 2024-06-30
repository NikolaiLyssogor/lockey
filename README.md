# lockey
A simple dependency-free password manager written in Python based on gpg.

## Shell Completions
At this time, shell completions are only available for `zsh`. If you would like to add completions for another shell, please open a PR and I will be happy to review it.

To enable shell completions for `zsh`, first add the completions script to a new directory in lockey's config folder. Note that if you use Oh My Zsh you should instead put the script in `~/.oh-my-zsh/completions`, at which point completions will be enabled for you.

```bash
mkdir $HOME/.config/lockey/completions
curl -L https://raw.githubusercontent.com/NikolaiLyssogor/lockey/main/completions/_lockey > $HOME/.config/lockey/completions/_lockey
```

If you do not use Oh My Zsh, you will also need to enable completions in your `.zshrc` if you have not already and add the directory you just created to your `$fpath`. Append the following to the end of your `.zshrc`. 

```bash
fpath=($HOME/.lockey/config/completions $fpath)
autoload -U compinit
compinit
```
