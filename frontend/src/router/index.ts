import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'
import GameRoom from '../views/GameRoom.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'landing',
            component: LandingView
        },
        {
            path: '/game',
            name: 'game',
            component: GameRoom
        }
    ]
})

export default router
