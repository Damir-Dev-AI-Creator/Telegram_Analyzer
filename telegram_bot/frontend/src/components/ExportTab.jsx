import React, { useState } from 'react';
import styled from 'styled-components';
import { apiService } from '../services/api';

const Container = styled.div`
  max-width: 600px;
  margin: 0 auto;
`;

const Section = styled.div`
  background: var(--tg-theme-secondary-bg-color, #f5f5f5);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
`;

const SectionTitle = styled.h2`
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
`;

const InputGroup = styled.div`
  margin-bottom: 12px;
`;

const Label = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--tg-theme-hint-color, #999999);
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid var(--tg-theme-hint-color, #e0e0e0);
  border-radius: 8px;
  background: var(--tg-theme-bg-color, #ffffff);
  color: var(--tg-theme-text-color, #000000);
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: var(--tg-theme-button-color, #3390ec);
  }
`;

const Button = styled.button`
  width: 100%;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  background: var(--tg-theme-button-color, #3390ec);
  color: var(--tg-theme-button-text-color, #ffffff);
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.8;
  }

  &:active {
    opacity: 0.6;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const StatusCard = styled.div`
  padding: 12px;
  border-radius: 8px;
  background: ${props => {
    switch (props.status) {
      case 'completed': return '#d4edda';
      case 'failed': return '#f8d7da';
      case 'in_progress': return '#fff3cd';
      default: return '#d1ecf1';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'completed': return '#155724';
      case 'failed': return '#721c24';
      case 'in_progress': return '#856404';
      default: return '#0c5460';
    }
  }};
  margin-bottom: 12px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 8px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 8px;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: var(--tg-theme-button-color, #3390ec);
  width: ${props => props.progress}%;
  transition: width 0.3s;
`;

const InfoText = styled.p`
  font-size: 13px;
  color: var(--tg-theme-hint-color, #999999);
  margin: 8px 0 0 0;
  line-height: 1.4;
`;

const WarningBox = styled.div`
  padding: 12px;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #856404;
`;

function ExportTab({ settings }) {
  const [chatIdentifier, setChatIdentifier] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);

  const hasConfig = settings?.has_telegram_config;

  const handleExport = async () => {
    if (!chatIdentifier.trim()) {
      window.Telegram?.WebApp?.showAlert('Введите идентификатор чата');
      return;
    }

    if (!hasConfig) {
      window.Telegram?.WebApp?.showAlert('Настройте Telegram API ключи в разделе "Настройки"');
      return;
    }

    try {
      setIsExporting(true);
      setTaskStatus({ status: 'pending', progress: 0 });

      const response = await apiService.startExport(
        chatIdentifier,
        dateFrom || null,
        dateTo || null
      );

      const taskId = response.task_id;

      // Polling статуса
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiService.getExportStatus(taskId);
          const task = statusResponse.task;

          setTaskStatus(task);

          if (task.status === 'completed') {
            clearInterval(pollInterval);
            setIsExporting(false);

            // Показываем кнопку скачивания
            window.Telegram?.WebApp?.showAlert(
              'Экспорт завершен! Нажмите кнопку "Скачать" для загрузки файла.'
            );
          } else if (task.status === 'failed') {
            clearInterval(pollInterval);
            setIsExporting(false);
            window.Telegram?.WebApp?.showAlert('Ошибка экспорта: ' + task.error);
          }
        } catch (err) {
          console.error('Ошибка получения статуса:', err);
          clearInterval(pollInterval);
          setIsExporting(false);
        }
      }, 2000);

      // Таймаут на 5 минут
      setTimeout(() => {
        clearInterval(pollInterval);
        if (isExporting) {
          setIsExporting(false);
          window.Telegram?.WebApp?.showAlert('Превышено время ожидания');
        }
      }, 300000);

    } catch (err) {
      console.error('Ошибка запуска экспорта:', err);
      window.Telegram?.WebApp?.showAlert('Ошибка: ' + err.message);
      setIsExporting(false);
    }
  };

  const handleDownload = () => {
    if (taskStatus?.id) {
      const url = apiService.getExportDownloadUrl(taskStatus.id);
      window.Telegram?.WebApp?.openLink(url);
    }
  };

  return (
    <Container>
      {!hasConfig && (
        <WarningBox>
          ⚠️ Перед использованием настройте Telegram API ключи в разделе "Настройки"
        </WarningBox>
      )}

      <Section>
        <SectionTitle>📱 Параметры экспорта</SectionTitle>

        <InputGroup>
          <Label>Идентификатор чата *</Label>
          <Input
            type="text"
            placeholder="@username или ID чата"
            value={chatIdentifier}
            onChange={(e) => setChatIdentifier(e.target.value)}
            disabled={isExporting}
          />
          <InfoText>
            Введите @username канала/группы или числовой ID чата
          </InfoText>
        </InputGroup>

        <InputGroup>
          <Label>Дата начала (необязательно)</Label>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            disabled={isExporting}
          />
        </InputGroup>

        <InputGroup>
          <Label>Дата окончания (необязательно)</Label>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            disabled={isExporting}
          />
        </InputGroup>

        <Button
          onClick={handleExport}
          disabled={isExporting || !hasConfig}
        >
          {isExporting ? '⏳ Экспортирование...' : '🚀 Начать экспорт'}
        </Button>
      </Section>

      {taskStatus && (
        <Section>
          <SectionTitle>📊 Статус экспорта</SectionTitle>

          <StatusCard status={taskStatus.status}>
            <div style={{ fontWeight: '600' }}>
              {taskStatus.status === 'pending' && '⏳ Ожидание...'}
              {taskStatus.status === 'in_progress' && '⚙️ Экспорт в процессе...'}
              {taskStatus.status === 'completed' && '✅ Экспорт завершен!'}
              {taskStatus.status === 'failed' && '❌ Ошибка экспорта'}
            </div>

            {taskStatus.status === 'in_progress' && (
              <ProgressBar>
                <ProgressFill progress={taskStatus.progress || 0} />
              </ProgressBar>
            )}

            {taskStatus.error && (
              <div style={{ marginTop: '8px', fontSize: '13px' }}>
                {taskStatus.error}
              </div>
            )}
          </StatusCard>

          {taskStatus.status === 'completed' && (
            <Button onClick={handleDownload}>
              📥 Скачать CSV файл
            </Button>
          )}
        </Section>
      )}

      <Section>
        <SectionTitle>ℹ️ Информация</SectionTitle>
        <InfoText>
          <strong>Что такое экспорт?</strong><br />
          Экспорт позволяет выгрузить полную историю сообщений из Telegram чата в CSV формат.
          Вы можете указать диапазон дат для фильтрации сообщений.
        </InfoText>
        <InfoText style={{ marginTop: '12px' }}>
          <strong>Как получить идентификатор чата?</strong><br />
          • Для публичных каналов/групп: используйте @username<br />
          • Для приватных чатов: используйте числовой ID (узнать в @userinfobot)
        </InfoText>
      </Section>
    </Container>
  );
}

export default ExportTab;
