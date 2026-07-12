import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Home } from './pages/Home'
import { GameRoom } from './pages/GameRoom'
import { Toast } from './components/common/Toast'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/game" element={<GameRoom />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {/* Global feedback layer: store errors + realtime connection status */}
      <Toast />
    </BrowserRouter>
  )
}

export default App
