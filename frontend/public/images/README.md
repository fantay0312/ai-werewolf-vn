# 游戏资源说明

## 目录结构

```
images/
├── game-bg.webp        # 白天场景背景
├── game-bg2.webp       # 夜晚场景背景
│
├── portraits/          # 角色立绘（对话框、行动面板展示）
│   ├── villager.webp   # 村民
│   ├── seer.webp       # 预言家
│   ├── witch.webp      # 女巫
│   ├── guard.webp      # 守卫
│   ├── hunter.webp     # 猎人
│   ├── wolf.webp       # 狼人
│   └── wolf_king.webp  # 狼王
│
└── role-cards/         # 角色身份牌
    ├── villager.webp
    ├── seer.webp
    ├── witch.webp
    ├── guard.webp
    ├── hunter.webp
    ├── wolf.webp
    ├── wolf_king.webp
    └── back.webp       # 未知身份时显示的牌背
```

## 命名与格式约定

1. 文件名与后端角色 key 一致（`villager` / `seer` / `witch` / `guard` / `hunter` / `wolf` / `wolf_king`），代码可直接用 `role` 拼接路径，无需映射表
2. 统一使用 WebP 格式：立绘/身份牌宽 600px，背景宽 1920px
3. 路径从 `/images/` 开始，对应 `public/images/` 目录
4. `back.webp` 用于未知身份或隐藏身份时的显示
