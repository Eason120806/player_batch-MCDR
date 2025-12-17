# PlayerBatch - MCDR假人批量操作插件

🎮 一个基于MCDReforged的插件，提供强大的Carpet假人批量操作功能

![License](https://img.shields.io/badge/License-GPLv3-blue)
![MCDR](https://img.shields.io/badge/MCDR-2.1.0%2B-blue)

## 📦 功能特性

- **批量基础操作**：同时控制多个假人执行任意指令
- **智能排列生成**：支持直线/方阵排列生成假人
- **初始化序列**：定制化生成+执行动作+自动清理流程
- **多维度配置**：可自定义假人命名规则和操作间隔
- **权限管理**：通过配置文件控制命令使用权限

## 🛠️ 安装方法

1. 确保已安装 [MCDReforged]
2. 下载最新版 `PlayerBatch.pyz`
3. 放入MCDR的plugins目录
4. 重启MCDR服务端

## ⚙️ 配置文件

路径：`config/player_batch.json`

```json
{
    "base_name": "bot_",
    "permission": 0,
    "interval": 1.0
}
```
## 🎯 命令列表

### 基础命令
```text
!!plb <名称> <起始> <结束> <动作>
!!playerbatch <名称> <起始> <结束> <动作>
```

### 直线生成
```text
!!plb l <名称> <起始> <长度> <方向> <间隔>
!!playerbatch l <名称> <起始> <长度> <方向> <间隔>
```

### 方阵生成
```text
!!plb s <名称> <起始> <长> <宽> <方向1> <方向2> <间隔>
!!playerbatch s <名称> <起始> <长> <宽> <方向1> <方向2> <间隔>
```

### 初始化序列
```text
!!plb init <名称> <起始> <长度> <间隔1> <间隔2> <x> <y> <z> <动作>
!!playerbatch init <名称> <起始> <长度> <间隔1> <间隔2> <x> <y> <z> <动作>
```

### 停止命令
```text
!!plb stop
!!playerbatch stop
```


## ⚠️ 注意事项

1. 需要安装Carpet Mod及其假人功能
2. 间隔时间影响服务器性能，请合理设置
3. 假人名称格式：前缀 + 自定义名 + 序号