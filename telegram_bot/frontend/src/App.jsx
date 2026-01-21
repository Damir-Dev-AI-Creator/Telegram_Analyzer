import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { retrieveLaunchParams } from '@telegram-apps/sdk';

// Компоненты
import ExportTab from './components/ExportTab';
import AnalysisTab from './components/AnalysisTab';
import SettingsTab from './components/SettingsTab';

// API сервис
import { apiService } from './services/api';

const AppContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--tg-theme-bg-color, #ffffff);
  color: var(--tg-theme-text-color, #000000);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--tg-theme-secondary-bg-color, #f0f0f0);
  border-bottom: 1px solid var(--tg-theme-hint-color, #e0e0e0);
`;

const Title = styled.h1`
  font-size: 20px;
  font-weight: 600;
  margin: 0;
`;

const TabContainer = styled.div`
  display: flex;
  background: var(--tg-theme-secondary-bg-color, #f0f0f0);
  border-bottom: 1px solid var(--tg-theme-hint-color, #e0e0e0);
  overflow-x: auto;
`;

const Tab = styled.button`
  flex: 1;
  padding: 12px 16px;
  border: none;
  background: ${props => props.active ? 'var(--tg-theme-button-color, #3390ec)' : 'transparent'};
  color: ${props => props.active ? 'var(--tg-theme-button-text-color, #ffffff)' : 'var(--tg-theme-text-color, #000000)'};
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    opacity: 0.8;
  }

  &:active {
    opacity: 0.6;
  }
`;

const Content = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 16px;
`;

const LoadingOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const Spinner = styled.div`
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 1s linear infinite;

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

function App() {
  const [activeTab, setActiveTab] = useState('export');
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    initApp();
  }, []);

  const initApp = async () => {
    try {
      // Инициализация Telegram WebApp
      if (window.Telegram?.WebApp) {
        const webApp = window.Telegram.WebApp;
        webApp.ready();
        webApp.expand();

        // Установка цветовой темы
        const themeParams = webApp.themeParams;
        document.documentElement.style.setProperty('--tg-theme-bg-color', themeParams.bg_color || '#ffffff');
        document.documentElement.style.setProperty('--tg-theme-text-color', themeParams.text_color || '#000000');
        document.documentElement.style.setProperty('--tg-theme-button-color', themeParams.button_color || '#3390ec');
        document.documentElement.style.setProperty('--tg-theme-button-text-color', themeParams.button_text_color || '#ffffff');

        // Получение initData
        const initData = webApp.initData;

        if (!initData) {
          throw new Error('Не удалось получить данные от Telegram');
        }

        // Инициализация API сервиса
        apiService.setInitData(initData);

        // Валидация аутентификации
        const response = await apiService.validateAuth();
        setUser(response.user);

        // Загрузка настроек
        await loadSettings();

      } else {
        throw new Error('Приложение должно быть открыто в Telegram');
      }
    } catch (err) {
      console.error('Ошибка инициализации:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSettings = async () => {
    try {
      const response = await apiService.getSettings();
      setSettings(response.settings);
    } catch (err) {
      console.error('Ошибка загрузки настроек:', err);
    }
  };

  const handleSettingsUpdate = async (newSettings) => {
    try {
      setIsLoading(true);
      await apiService.updateSettings(newSettings);
      await loadSettings();

      // Показываем уведомление через Telegram WebApp
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert('Настройки успешно сохранены!');
      }
    } catch (err) {
      console.error('Ошибка сохранения настроек:', err);
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert('Ошибка сохранения: ' + err.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <LoadingOverlay>
        <Spinner />
      </LoadingOverlay>
    );
  }

  if (error) {
    return (
      <AppContainer>
        <Content>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <h2>❌ Ошибка</h2>
            <p>{error}</p>
          </div>
        </Content>
      </AppContainer>
    );
  }

  return (
    <AppContainer>
      <Header>
        <Title>Ysell Analyzer</Title>
        {user && (
          <div style={{ fontSize: '12px', opacity: 0.7 }}>
            {user.first_name}
          </div>
        )}
      </Header>

      <TabContainer>
        <Tab
          active={activeTab === 'export'}
          onClick={() => setActiveTab('export')}
        >
          📱 Экспорт
        </Tab>
        <Tab
          active={activeTab === 'analysis'}
          onClick={() => setActiveTab('analysis')}
        >
          🤖 Анализ
        </Tab>
        <Tab
          active={activeTab === 'settings'}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Настройки
        </Tab>
      </TabContainer>

      <Content>
        {activeTab === 'export' && (
          <ExportTab settings={settings} />
        )}
        {activeTab === 'analysis' && (
          <AnalysisTab settings={settings} />
        )}
        {activeTab === 'settings' && (
          <SettingsTab
            settings={settings}
            onUpdate={handleSettingsUpdate}
          />
        )}
      </Content>
    </AppContainer>
  );
}

export default App;
