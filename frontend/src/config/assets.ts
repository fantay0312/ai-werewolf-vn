/**
 * 游戏资源配置
 * 管理所有图片资源路径
 */

export type RoleType = 'villager' | 'seer' | 'witch' | 'guard' | 'hunter' | 'wolf' | 'wolf_king'

/**
 * 角色立绘映射
 * 用于对话框和玩家展示
 */
export const PORTRAITS: Record<RoleType, string> = {
  villager: '/images/portraits/村民.jpg',
  seer: '/images/portraits/预言家.jpg',
  witch: '/images/portraits/女巫.png',
  guard: '/images/portraits/守卫.png',
  hunter: '/images/portraits/猎人.png',
  wolf: '/images/portraits/狼人.png',
  wolf_king: '/images/portraits/狼王.png',
}

/**
 * 角色身份牌映射
 * 用于身份展示
 */
export const ROLE_CARDS: Record<RoleType, string> = {
  villager: '/images/role-cards/村民.png',
  seer: '/images/role-cards/预言家.png',
  witch: '/images/role-cards/女巫.png',
  guard: '/images/role-cards/守卫.png',
  hunter: '/images/role-cards/猎人.png',
  wolf: '/images/role-cards/狼人.png',
  wolf_king: '/images/role-cards/狼王.png',
}

/**
 * 身份牌反面（未知身份时显示）
 */
export const ROLE_CARD_BACK = '/images/role-cards/反面.png'

/**
 * 角色中文名称
 */
export const ROLE_NAMES: Record<RoleType, string> = {
  villager: '村民',
  seer: '预言家',
  witch: '女巫',
  guard: '守卫',
  hunter: '猎人',
  wolf: '狼人',
  wolf_king: '狼王',
}

/**
 * 角色描述
 */
export const ROLE_DESCRIPTIONS: Record<RoleType, string> = {
  villager: '无特殊技能，通过发言和投票找出狼人',
  seer: '每晚查验一名玩家身份',
  witch: '拥有解药和毒药各一瓶',
  guard: '每晚守护一名玩家，不可连续守护同一人',
  hunter: '被投票或击杀时可开枪带走一人',
  wolf: '每晚参与击杀行动',
  wolf_king: '被票出局可开枪带走一人',
}

/**
 * 获取角色立绘路径
 */
export function getPortrait(role: RoleType): string {
  return PORTRAITS[role] || PORTRAITS.villager
}

/**
 * 获取角色身份牌路径
 */
export function getRoleCard(role: RoleType): string {
  return ROLE_CARDS[role] || ROLE_CARD_BACK
}

/**
 * 获取角色名称
 */
export function getRoleName(role: RoleType): string {
  return ROLE_NAMES[role] || '未知'
}

/**
 * 获取角色描述
 */
export function getRoleDescription(role: RoleType): string {
  return ROLE_DESCRIPTIONS[role] || ''
}
