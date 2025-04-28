# PlayerBatch - MCDR Batch Bot Management Plugin

![License](https://img.shields.io/badge/License-GPLv3-blue)
![MCDR](https://img.shields.io/badge/MCDR-2.1.0%2B-blue)

A MCDReforged plugin for batch operations on fake players, supporting quick creation/control of multiple fake players. Compatible with mainstream fake player systems like Carpet Mod.

## Features

- 🚀 **Batch Creation** - Quickly generate sequentially numbered fake players with simple commands
- ⚡ **Action Execution** - Perform batch operations like attack/movement/removal
- 🛠️ **Custom Configuration** - Flexible settings for name prefix and permission levels
- 📊 **Real-time Feedback** - Instant operation results and error logging
- 🔒 **Permission Control** - Multi-level OP permission management

## Installation

1. Place `player_batch.pyz` into MCDR's `plugins` directory
2. Restart MCDR server
3. Configuration file `config/player_batch.json` will be auto-generated

## Usage

### Basic command format
```text
!!plb <name> <start> <end> <action_args>
!!playerbatch <name> <start> <end> <action_args>
```

### Straight line generation command format
```text
!!plb li <name> <start> <length> <direction> <interval>
!!playerbatch li <name> <start> <length> <direction> <interval> 
```

### Square Array command format
```text
!!plb re <name> <start> <long> <width> <direction1> <direction2> <interval> 
!!playerbatch re <name> <start> <long> <width> <direction1> <direction2> <interval>