# 游戏资源使用指南

## 资源已迁移完成 ✅

所有游戏资源（立绘和身份牌）已从 `resource/` 目录迁移到前端项目：

```
frontend/public/images/
├── portraits/      # 7个角色立绘
└── role-cards/     # 7个角色身份牌 + 1个反面牌
```

## 快速开始

### 1. 使用资源配置

```typescript
// 导入资源配置
import {
  getPortrait,
  getRoleCard,
  getRoleName,
  getRoleDescription,
  ROLE_CARD_BACK
} from '@/config/assets'

// 获取立绘URL
const portraitUrl = getPortrait('seer')  // '/images/portraits/预言家.jpg'

// 获取身份牌URL
const cardUrl = getRoleCard('wolf')  // '/images/role-cards/狼人.png'

// 获取角色名称
const name = getRoleName('witch')  // '女巫'

// 获取角色描述
const desc = getRoleDescription('hunter')  // '被投票或击杀时可开枪带走一人'

// 未知身份牌
const backCard = ROLE_CARD_BACK  // '/images/role-cards/反面.png'
```

### 2. 使用 RoleImage 组件

```vue
<template>
  <!-- 显示立绘 -->
  <RoleImage
    :role="player.role"
    type="portrait"
    containerClass="w-48 h-64"
    imageClass="rounded-lg shadow-lg"
  />

  <!-- 显示身份牌 -->
  <RoleImage
    :role="player.role"
    type="card"
    containerClass="w-24 h-32"
    :fallbackToBack="!player.is_revealed"
  />
</template>

<script setup lang="ts">
import RoleImage from '@/components/common/RoleImage.vue'
</script>
```

## 组件 Props 说明

### RoleImage 组件

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `role` | `RoleType` | 必填 | 角色类型 |
| `type` | `'portrait' \| 'card'` | `'portrait'` | 图片类型 |
| `showName` | `boolean` | `false` | 是否显示角色名称 |
| `containerClass` | `string` | `''` | 容器样式类 |
| `imageClass` | `string` | `''` | 图片样式类 |
| `fallbackToBack` | `boolean` | `true` | 加载失败时是否显示反面牌 |

## 角色类型

```typescript
type RoleType =
  | 'villager'    // 村民
  | 'seer'        // 预言家
  | 'witch'       // 女巫
  | 'guard'       // 守卫
  | 'hunter'      // 猎人
  | 'wolf'        // 狼人
  | 'wolf_king'   // 狼王
```

## 使用场景示例

### 场景1: 玩家座位显示

```vue
<template>
  <div class="player-seat">
    <!-- 显示角色身份牌（未揭示时显示反面） -->
    <RoleImage
      :role="player.role"
      type="card"
      containerClass="w-16 h-24"
      :fallbackToBack="!isRoleRevealed"
    />
    <span class="player-name">{{ player.name }}</span>
  </div>
</template>
```

### 场景2: 对话框立绘

```vue
<template>
  <div class="dialog-box">
    <!-- 显示说话者立绘 -->
    <RoleImage
      :role="speaker.role"
      type="portrait"
      containerClass="w-64 h-96"
      imageClass="rounded-lg shadow-2xl"
    />
    <div class="speech-content">
      <h3>{{ speaker.name }}</h3>
      <p>{{ content }}</p>
    </div>
  </div>
</template>
```

### 场景3: 身份展示面板

```vue
<template>
  <div class="role-panel">
    <RoleImage
      :role="myRole"
      type="card"
      containerClass="w-32 h-48 mb-4"
    />
    <h2>{{ getRoleName(myRole) }}</h2>
    <p>{{ getRoleDescription(myRole) }}</p>
  </div>
</template>
```

## 后端集成

后端已更新，返回的 `Player` 对象中 `portrait` 字段包含完整路径：

```python
# backend/app/core/game_manager.py
portrait_map = {
    Role.VILLAGER: "/images/portraits/村民.jpg",
    Role.WOLF: "/images/portraits/狼人.png",
    # ...
}
```

前端可以直接使用后端返回的路径：

```vue
<img :src="player.portrait" :alt="player.name" />
```

## 图片预加载

建议在游戏开始前预加载所有图片：

```typescript
// src/utils/preloadImages.ts
import { PORTRAITS, ROLE_CARDS, ROLE_CARD_BACK } from '@/config/assets'

export async function preloadGameImages() {
  const allImages = [
    ...Object.values(PORTRAITS),
    ...Object.values(ROLE_CARDS),
    ROLE_CARD_BACK
  ]

  const promises = allImages.map(src => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = resolve
      img.onerror = reject
      img.src = src
    })
  })

  await Promise.all(promises)
  console.log('All game images preloaded')
}
```

在游戏初始化时调用：

```typescript
// App.vue 或 GameRoom.vue
import { preloadGameImages } from '@/utils/preloadImages'

onMounted(async () => {
  await preloadGameImages()
  // 然后开始游戏
})
```

## 注意事项

1. ✅ 所有图片路径已统一管理在 `config/assets.ts` 中
2. ✅ 使用 `RoleImage` 组件自动处理图片加载和错误
3. ✅ 后端和前端的角色映射已同步
4. ✅ 支持图片加载失败时的降级处理
5. 🔄 建议在生产环境使用CDN加速图片加载
6. 🔄 可以根据需要添加图片懒加载功能

## 文件清单

已创建/修改的文件：

- ✅ `frontend/public/images/portraits/` - 7个立绘文件
- ✅ `frontend/public/images/role-cards/` - 8个身份牌文件
- ✅ `frontend/src/config/assets.ts` - 资源配置
- ✅ `frontend/src/components/common/RoleImage.vue` - 图片组件
- ✅ `backend/app/core/game_manager.py` - 更新portrait映射

## 下一步建议

1. 在组件中使用 `RoleImage` 替代硬编码的图片路径
2. 实现图片预加载功能提升用户体验
3. 添加图片加载动画和骨架屏
4. 根据网络状况提供不同质量的图片
