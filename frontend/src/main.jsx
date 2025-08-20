import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// 🔧 关键修复：移除StrictMode以避免重复渲染和重复WebSocket连接
createRoot(document.getElementById('root')).render(
  <App />
)