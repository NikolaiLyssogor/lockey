# lockey
Lockey is a CLI password manager that uses `gpg` symmetric keys to securely store passwords. Text can also be saved unencrypted so that you can also use lockey to quickly retrieve things like commands you can never seem to remember. Secrets are stored in a configurable directory which defaults to `$HOME/.lockey`. Lockey also has a configuration file stored in `$HOME/.config/lockey/`. For more information about lockey's commands, see the `docs` directory, which has the same information you would see from running `lockey <command> --help`.

## Installation
Given that lockey is a CLI tool written in Python, I highly recommend installing lockey using [`pipx`](https://pipx.pypa.io/stable/.). This will make sure that lockey is installed into an isolated environment while still being available globally. Once you have lockey installed, you must first create the directories where lockey stores information using `lockey init`. After that you may `lockey add`, `lockey get`, etc as you please. 

> [!WARNING]
> At this time, lockey has only been tested on MacOS. I welcome contributions by anyone interested making lockey usable on other platforms.

## Shell Completions
At this time, shell completions are only available for `zsh`. If you would like to add completions for another shell, please open a PR and I will be happy to review it.

To enable shell completions for `zsh`, first add the completions script to a new directory in lockey's configuration directory. Note that if you use Oh My Zsh you should instead put the script in `~/.oh-my-zsh/completions`, at which point completions will be enabled for you.

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

## FAQ
*Q:* Why wouldn't I just use <other CLI password manager>?
*A:* If some other more popular tool does what you want it to, I would actually recommend using that over lockey. Other tools that have been around longer are probably going to be more stable than lockey is. I made lockey because it's something I can tailor to my workflow as needed.
