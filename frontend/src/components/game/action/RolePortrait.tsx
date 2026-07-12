import { useState } from 'react'
import type { Role } from '../../../types'
import { ROLE_DESCRIPTIONS } from '../../../types'
import { getPortraitUrl, getRoleCardUrl, getRoleName } from '../../../lib/roles'

interface RolePortraitProps {
  role: Role
}

/**
 * The human's role portrait pinned to the bottom-left of the action panel.
 * Click to reveal the full identity card. Extracted from ActionPanel so the
 * panel body is only about phase actions.
 */
export function RolePortrait({ role }: RolePortraitProps) {
  const [showCard, setShowCard] = useState(false)
  const roleName = getRoleName(role)

  return (
    <>
      <div
        className="role-portrait absolute left-5 bottom-4 w-[120px] h-[180px] cursor-pointer z-50 transition-transform hover:scale-105 group"
        onClick={() => setShowCard(true)}
      >
        <img
          src={getPortraitUrl(role) ?? getRoleCardUrl(role)}
          alt={roleName}
          className="w-full h-full object-cover rounded-xl"
        />
        <div className="portrait-overlay absolute inset-0 flex items-center justify-center bg-transparent rounded-xl transition-colors group-hover:bg-black/40">
          <span className="text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">点击查看身份牌</span>
        </div>
        <div className="portrait-border absolute -inset-[2px] border-2 border-[#c5a059]/40 rounded-[14px]"></div>
      </div>

      {showCard && (
        <div
          className="role-card-modal fixed left-5 bottom-4 w-[360px] h-[540px] rounded-2xl overflow-hidden cursor-pointer z-[100] shadow-[0_10px_40px_rgba(0,0,0,0.6),0_0_20px_rgba(197,160,89,0.35)] border border-[color:var(--border-gilded)] bg-[#141210] animate-scale-in"
          onClick={() => setShowCard(false)}
        >
          <img
            src={getRoleCardUrl(role)}
            alt={roleName}
            className="w-full h-full object-cover"
          />
          <div className="role-card-info absolute bottom-0 inset-x-0 p-5 bg-gradient-to-t from-black/90 to-transparent">
            <h3 className="font-display text-2xl font-bold text-[#f4d03f] mb-2 drop-shadow-md tracking-wide">{roleName}</h3>
            <p className="text-sm text-parchment/90 leading-relaxed">
              {ROLE_DESCRIPTIONS[role as keyof typeof ROLE_DESCRIPTIONS]}
            </p>
          </div>
          <div className="close-hint absolute top-3 right-3 px-3 py-1 bg-black/60 rounded-full text-xs text-white/70 backdrop-blur-md">点击关闭</div>
        </div>
      )}
    </>
  )
}
