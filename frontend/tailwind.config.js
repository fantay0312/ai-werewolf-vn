/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'bg-primary': '#0f0a1a',
                'bg-secondary': '#1a1028',
                'color-gold': '#ffd700',
                'color-red': '#dc2626',
                'color-green': '#22c55e',
                'color-blue': '#3b82f6',
                'color-purple': '#8b5cf6',
                'content-primary': '#e2e8f0',
                'content-secondary': '#94a3b8',
            },
            fontFamily: {
                'title': ['"ZCOOL KuaiLe"', '"STKaiti"', 'serif'],
                'body': ['Inter', '"PingFang SC"', 'sans-serif'],
                'mono': ['"JetBrains Mono"', 'monospace'],
            }
        },
    },
    plugins: [],
}
