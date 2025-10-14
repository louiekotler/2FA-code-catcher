# 2FA-code-catcher
Two-factor authentication code copier for MacOS.

## Quick Installation Setup
1. `cd scripts`
1. `chmod +x install.sh`
1. `./install.sh`
1. Go to `System Settings -> Privacy & Security -> Full Disk Access` and enable `2FA-code-catcher`
1. You may have to reboot for this to take effect.


## Developer Setup
### Initialize environment
1. `python3 -m venv venv`
1. `source venv/bin/activate`
1. `pip install -r requirements.txt`
1. `pip install -r requirements-dev.txt`

### Modify and Build Executable
1. Modify project files if desired
1. `cd scripts`
1. `chmod +x build_exec.sh`
1. `./build_exec.sh`
1. `chmod +x install.sh`
1. `./install.sh`

## Debugging
Restart launchd service
`launchctl kickstart -k gui/$(id -u)/com.louiekotler.2FA-code-catcher`

## Uninstall
1. `cd scripts`
1. `./uninstall.sh`
