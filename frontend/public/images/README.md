# 游戏资源说明

## 目录结构

```
images/
├── portraits/      # 角色立绘（用于对话框和玩家展示）
│   ├── 村民.jpg
│   ├── 预言家.jpg
│   ├── 女巫.png
│   ├── 守卫.png
│   ├── 猎人.png
│   ├── 狼人.png
│   └── 狼王.png
│
└── role-cards/     # 角色身份牌（用于身份展示）
    ├── 村民.png
    ├── 预言家.png
    ├── 女巫.png
    ├── 守卫.png
    ├── 猎人.png
    ├── 狼人.png
    ├── 狼王.png
    └── 反面.png   # 未知身份时显示
```

## 使用方式

在代码中使用资源配置文件：

```typescript
import { getPortrait, getRoleCard, getRoleName } from '@/config/assets'

// 获取角色立绘
const portraitUrl = getPortrait('seer') // '/images/portraits/预言家.jpg'

// 获取角色身份牌
const cardUrl = getRoleCard('witch') // '/images/role-cards/女巫.png'

// 获取角色名称
const name = getRoleName('hunter') // '猎人'
```

## 图片规格

- **立绘**: 用于视觉小说风格的对话展示，尺寸较大
- **身份牌**: 用于玩家座位和身份展示，尺寸较小

## 注意事项

1. 所有图片文件名使用中文，与游戏主题一致
2. 路径从 `/images/` 开始，对应 `public/images/` 目录
3. 使用 `assets.ts` 配置文件统一管理，避免硬编码路径
4. 反面身份牌用于未知身份或死亡玩家的显示
