// Single source of truth for role display: names, colors, portrait/card art.
// Migrated here from duplicated copies in PlayerSeat / ActionPanel / VoteModal /
// SidePanel / DialogBox.
import type { Role } from '../types'
import { ROLE_NAMES, isWolfRole } from '../types'

// Roles that ship with portrait + identity-card art. 'unknown' intentionally
// excluded (hidden role -> show number / face-down card).
export const KNOWN_ROLES: readonly Role[] = [
  'villager', 'wolf', 'wolf_king', 'seer', 'witch', 'guard', 'hunter',
]

function isKnownRole(role: string): boolean {
  return (KNOWN_ROLES as readonly string[]).includes(role)
}

/** Localized role name, tolerant of unexpected/open backend role strings. */
export function getRoleName(role: string): string {
  return ROLE_NAMES[role as Role] || role
}

/** Circular seat portrait; null when the role is unknown/hidden. */
export function getPortraitUrl(role: string): string | null {
  return isKnownRole(role) ? `/images/portraits/${role}.webp` : null
}

/** Large identity-card art; falls back to the face-down back for unknown roles. */
export function getRoleCardUrl(role: string): string {
  return isKnownRole(role) ? `/images/role-cards/${role}.webp` : '/images/role-cards/back.webp'
}

// Per-role text color class used in lists (SidePanel). Defined in index.css.
const ROLE_TEXT_CLASS: Record<string, string> = {
  wolf: 'role-wolf',
  wolf_king: 'role-wolf-king',
  seer: 'role-seer',
  witch: 'role-witch',
  guard: 'role-guard',
  hunter: 'role-hunter',
  villager: 'role-villager',
}

/** Per-role name color class (SidePanel / game-over reveal). */
export function getRoleTextClass(role: string): string {
  return ROLE_TEXT_CLASS[role] || 'role-villager'
}

/** Camp-colored pill class used on seat badges (index.css .role-wolf/.role-good). */
export function getSeatBadgeClass(role: Role): string {
  return isWolfRole(role) ? 'role-wolf' : 'role-good'
}

/** Camp-colored pill class used on the dialog header (index.css .badge-wolf/.badge-good). */
export function getCampBadgeClass(role: Role): string {
  return isWolfRole(role) ? 'badge-wolf' : 'badge-good'
}
