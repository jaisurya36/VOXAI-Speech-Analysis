import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import AnalyzePage from './pages/AnalyzePage'
import ResultsPage from './pages/ResultsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="analyze" element={<AnalyzePage />} />
        <Route path="results/:analysisId" element={<ResultsPage />} />
      </Route>
    </Routes>
  )
}

export default App
