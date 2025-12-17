# PlayerBatch - MCDR Fake Player Batch Operation Plugin

🎮 A MCDReforged-based plugin providing powerful Carpet fake player batch operation capabilities

![License](https://img.shields.io/badge/License-GPLv3-blue)
![MCDR](https://img.shields.io/badge/MCDR-2.1.0%2B-blue)

## 📦 Features

- **Batch Basic Operations**: Control multiple fake players to execute commands simultaneously
- **Smart Arrangement Generation**: Support linear/square formation generation
- **Initialization Sequence**: Customized generation + action execution + automatic cleanup process
- **Multi-dimensional Configuration**: Customizable naming rules and operation intervals
- **Permission Management**: Control command permissions through config file

## 🛠️ Installation

1. Ensure [MCDReforged] is installed
2. Download latest `PlayerBatch.pyz`
3. Place into MCDR's plugins directory
4. Restart MCDR server

## ⚙️ Configuration

Path: `config/player_batch.json`

```json
{
    "base_name": "bot_",
    "permission": 0,
    "interval": 1.0
}
```
## 🎯 Commands

### Basic Commands
```text
!!plb <name> <start> <end> <action>
!!playerbatch <name> <start> <end> <action>
```

### Linear Generation
```text
!!plb l <name> <start> <length> <direction> <interval>
!!playerbatch l <name> <start> <length> <direction> <interval>
```

### Square Formation Generation
```text
!!plb s <name> <start> <length> <width> <direction1> <direction2> <interval>
!!playerbatch s <name> <start> <length> <width> <direction1> <direction2> <interval>
```

### Initialization Sequence
```text
!!plb init <name> <start> <length> <interval1> <interval2> <x> <y> <z> <action>
!!playerbatch init <name> <start> <length> <interval1> <interval2> <x> <y> <z> <action>
```

### Stop command
```text
!!plb stop
!!playerbatch stop
```


## ⚠️ Notes

1. Requires Carpet Mod with fake player functionality
2. Interval settings affect server performance - configure reasonably
3. Fake player name format: Prefix + Custom name + Sequence number