import React, { useState, useRef } from 'react';
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

const UploadArea = styled.div`
  border: 2px dashed var(--tg-theme-hint-color, #cccccc);
  border-radius: 8px;
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--tg-theme-bg-color, #ffffff);

  &:hover {
    border-color: var(--tg-theme-button-color, #3390ec);
    background: rgba(51, 144, 236, 0.05);
  }

  &.active {
    border-color: var(--tg-theme-button-color, #3390ec);
    background: rgba(51, 144, 236, 0.1);
  }
`;

const UploadIcon = styled.div`
  font-size: 48px;
  margin-bottom: 12px;
`;

const UploadText = styled.div`
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
`;

const UploadHint = styled.div`
  font-size: 13px;
  color: var(--tg-theme-hint-color, #999999);
`;

const FileInfo = styled.div`
  display: flex;
  align-items: center;
  padding: 12px;
  background: var(--tg-theme-bg-color, #ffffff);
  border-radius: 8px;
  margin-bottom: 12px;
`;

const FileIcon = styled.div`
  font-size: 32px;
  margin-right: 12px;
`;

const FileDetails = styled.div`
  flex: 1;
`;

const FileName = styled.div`
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
`;

const FileSize = styled.div`
  font-size: 12px;
  color: var(--tg-theme-hint-color, #999999);
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

const SecondaryButton = styled(Button)`
  background: transparent;
  border: 1px solid var(--tg-theme-button-color, #3390ec);
  color: var(--tg-theme-button-color, #3390ec);
  margin-top: 8px;
`;

const StatusBox = styled.div`
  padding: 12px;
  border-radius: 8px;
  background: ${props => props.success ? '#d4edda' : '#fff3cd'};
  color: ${props => props.success ? '#155724' : '#856404'};
  margin-bottom: 12px;
  font-size: 14px;
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

const HiddenInput = styled.input`
  display: none;
`;

function AnalysisTab({ settings }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const hasConfig = settings?.has_claude_config;

  const handleFileSelect = (file) => {
    if (file && file.name.endsWith('.csv')) {
      setSelectedFile(file);
      setAnalysisResult(null);
    } else {
      window.Telegram?.WebApp?.showAlert('Пожалуйста, выберите CSV файл');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      window.Telegram?.WebApp?.showAlert('Выберите CSV файл');
      return;
    }

    if (!hasConfig) {
      window.Telegram?.WebApp?.showAlert('Настройте Claude API ключ в разделе "Настройки"');
      return;
    }

    try {
      setIsAnalyzing(true);
      setAnalysisResult(null);

      const response = await apiService.startAnalysis(selectedFile);

      setAnalysisResult({
        success: true,
        message: response.message,
        filename: response.output_file?.split('/').pop(),
      });

      window.Telegram?.WebApp?.showAlert('Анализ завершен! Нажмите "Скачать отчет" для загрузки.');

    } catch (err) {
      console.error('Ошибка анализа:', err);
      setAnalysisResult({
        success: false,
        message: 'Ошибка анализа: ' + err.message,
      });
      window.Telegram?.WebApp?.showAlert('Ошибка: ' + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownload = () => {
    if (analysisResult?.filename) {
      const url = apiService.getAnalysisDownloadUrl(analysisResult.filename);
      window.Telegram?.WebApp?.openLink(url);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <Container>
      {!hasConfig && (
        <WarningBox>
          ⚠️ Перед использованием настройте Claude API ключ в разделе "Настройки"
        </WarningBox>
      )}

      <Section>
        <SectionTitle>🤖 Анализ с Claude AI</SectionTitle>

        {!selectedFile ? (
          <>
            <UploadArea
              className={isDragging ? 'active' : ''}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <UploadIcon>📄</UploadIcon>
              <UploadText>Выберите CSV файл</UploadText>
              <UploadHint>или перетащите файл сюда</UploadHint>
            </UploadArea>

            <HiddenInput
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileInputChange}
            />
          </>
        ) : (
          <>
            <FileInfo>
              <FileIcon>📊</FileIcon>
              <FileDetails>
                <FileName>{selectedFile.name}</FileName>
                <FileSize>{formatFileSize(selectedFile.size)}</FileSize>
              </FileDetails>
            </FileInfo>

            <Button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !hasConfig}
            >
              {isAnalyzing ? '⏳ Анализирование...' : '🚀 Начать анализ'}
            </Button>

            <SecondaryButton
              onClick={() => setSelectedFile(null)}
              disabled={isAnalyzing}
            >
              🔄 Выбрать другой файл
            </SecondaryButton>
          </>
        )}
      </Section>

      {analysisResult && (
        <Section>
          <SectionTitle>📊 Результат</SectionTitle>

          <StatusBox success={analysisResult.success}>
            {analysisResult.success ? '✅' : '❌'} {analysisResult.message}
          </StatusBox>

          {analysisResult.success && (
            <Button onClick={handleDownload}>
              📥 Скачать отчет (DOCX)
            </Button>
          )}
        </Section>
      )}

      <Section>
        <SectionTitle>ℹ️ Информация</SectionTitle>
        <InfoText>
          <strong>Что такое анализ?</strong><br />
          Claude AI анализирует содержимое вашего CSV файла с сообщениями и генерирует
          профессиональный отчет в формате DOCX с ключевыми инсайтами, темами обсуждения
          и выводами.
        </InfoText>
        <InfoText style={{ marginTop: '12px' }}>
          <strong>Требования:</strong><br />
          • Файл должен быть в формате CSV<br />
          • Максимум 3000 строк (ограничение API)<br />
          • Столбцы: Date, From, Text
        </InfoText>
        <InfoText style={{ marginTop: '12px' }}>
          <strong>Модели AI:</strong><br />
          • Claude Opus 4.5 (наиболее мощная)<br />
          • Claude Sonnet 4 (быстрая и точная)
        </InfoText>
      </Section>
    </Container>
  );
}

export default AnalysisTab;
