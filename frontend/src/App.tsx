import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { darkThemeConfig } from './theme';
import MainLayout from './components/MainLayout';
import AnalysisPage from './pages/AnalysisPage';
import TradesPage from './pages/TradesPage';
import ProfilePage from './pages/ProfilePage';
import SentimentPage from './pages/SentimentPage';
import SectorPage from './pages/SectorPage';
import MacroPage from './pages/MacroPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <ConfigProvider locale={zhCN} theme={darkThemeConfig}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/analysis" replace />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="trades" element={<TradesPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="sentiment" element={<SentimentPage />} />
            <Route path="sector" element={<SectorPage />} />
            <Route path="macro" element={<MacroPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
