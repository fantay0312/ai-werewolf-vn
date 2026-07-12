import { Component, type ErrorInfo, type ReactNode } from 'react'
import { TriangleAlert } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  message: string
}

/**
 * Top-level render-error guard. A throw anywhere in the game tree (a malformed
 * log breaking a regex, an unexpected role, etc.) previously white-screened the
 * whole app; now it renders a recoverable fallback instead.
 *
 * Uses window.location rather than router hooks so it can sit above the router
 * and still offer navigation as a class component.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('ErrorBoundary caught a render error:', error, info.componentStack)
  }

  private handleHome = (): void => {
    // Keep the session so the game isn't lost to a transient render bug.
    window.location.href = '/'
  }

  private handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950 p-6 text-center">
        <div className="flex max-w-md flex-col items-center gap-4 rounded-2xl border border-[color:var(--border-gilded)] bg-[#141210]/90 p-8 shadow-2xl backdrop-blur-md">
          <TriangleAlert className="w-12 h-12 text-[#c5a059]" strokeWidth={1.5} />
          <h1 className="font-display text-xl font-bold text-parchment tracking-wide">页面出错了</h1>
          <p className="text-sm leading-relaxed text-parchment-dim">
            渲染时发生异常，游戏进度已保存。你可以重新加载页面，或返回首页。
          </p>
          {this.state.message && (
            <p className="max-w-full break-words rounded-lg bg-black/40 px-3 py-2 font-mono text-xs text-red-300/80">
              {this.state.message}
            </p>
          )}
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={this.handleReload}
              className="rounded-full border border-amber-500/50 bg-amber-500/15 px-6 py-2 text-sm font-medium tracking-wide text-amber-200 transition-all hover:border-amber-400 hover:bg-amber-500/25"
            >
              重新加载
            </button>
            <button
              onClick={this.handleHome}
              className="rounded-full border border-white/20 bg-white/5 px-6 py-2 text-sm font-medium tracking-wide text-white/70 transition-all hover:bg-white/10 hover:text-white"
            >
              返回首页
            </button>
          </div>
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
