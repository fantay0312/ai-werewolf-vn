import {
  Skull,
  Crown,
  Moon,
  Sun,
  MessageCircle,
  Lock,
  Megaphone,
  Ban,
  AlertTriangle,
  Users,
  ScrollText,
  Gavel,
  Eye,
  Shield,
  Crosshair,
  FlaskConical,
  Ghost
} from 'lucide-react'
import { cn } from '../../lib/utils'

interface GameIconProps {
  name: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  color?: string
  className?: string
}

export function GameIcon({ name, size = 'md', color = 'currentColor', className }: GameIconProps) {
  const sizeMap = {
    xs: 14,
    sm: 18,
    md: 24,
    lg: 32,
    xl: 48
  }

  const sizeValue = sizeMap[size]
  const iconProps = {
    size: sizeValue,
    color,
    className: cn('inline-flex items-center justify-center shrink-0 leading-none', className)
  }

  switch (name) {
    case 'wolf': return <Ghost {...iconProps} />
    case 'seer': return <Eye {...iconProps} />
    case 'witch': return <FlaskConical {...iconProps} />
    case 'guard': return <Shield {...iconProps} />
    case 'hunter': return <Crosshair {...iconProps} />
    case 'moon': return <Moon {...iconProps} />
    case 'sun': return <Sun {...iconProps} />
    case 'skull': return <Skull {...iconProps} />
    case 'crown': return <Crown {...iconProps} />
    case 'judge': return <Gavel {...iconProps} />
    case 'chat': return <MessageCircle {...iconProps} />
    case 'lock': return <Lock {...iconProps} />
    case 'announce': return <Megaphone {...iconProps} />
    case 'ban': return <Ban {...iconProps} />
    case 'warning': return <AlertTriangle {...iconProps} />
    case 'players': return <Users {...iconProps} />
    case 'logs': return <ScrollText {...iconProps} />
    default: return <span className={iconProps.className} style={{ width: sizeValue, height: sizeValue }} aria-hidden="true" />
  }
}
