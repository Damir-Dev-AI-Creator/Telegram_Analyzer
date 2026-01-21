import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

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
  font-family: monospace;

  &:focus {
    outline: none;
    border-color: var(--tg-theme-button-color, #3390ec);
  }

  &::placeholder {
    color: var(--tg-theme-hint-color, #cccccc);
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

const InfoText = styled.p`
  font-size: 13px;
  color: var(--tg-theme-hint-color, #999999);
  margin: 8px 0 0 0;
  line-height: 1.4;
`;

const Link = styled.a`
  color: var(--tg-theme-link-color, #3390ec);
  text-decoration: none;
  font-weight: 500;

  &:hover {
    text-decoration: underline;
  }
`;

const StatusIndicator = styled.div`
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: ${props => props.configured ? '#d4edda' : '#f8d7da'};
  color: ${props => props.configured ? '#155724' : '#721c24'};
  margin-bottom: 12px;
`;

const Divider = styled.div`
  height: 1px;
  background: var(--tg-theme-hint-color, #e0e0e0);
  margin: 16px 0;
`;

const InstructionBox = styled.div`
  padding: 12px;
  background: #e7f3ff;
  border-left: 4px solid #3390ec;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #0c5460;
`;

const StepList = styled.ol`
  margin: 8px 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.6;
`;

function SettingsTab({ settings, onUpdate }) {
  const [telegramApiId, setTelegramApiId] = useState('');
  const [telegramApiHash, setTelegramApiHash] = useState('');
  const [telegramPhone, setTelegramPhone] = useState('');
  const [claudeApiKey, setClaudeApiKey] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setTelegramApiId(settings.telegram_api_id || '');
      setTelegramApiHash('');  // Не показываем зашифрованные данные
      setTelegramPhone(settings.telegram_phone || '');
      setClaudeApiKey('');  // Не показываем зашифрованные данные
    }
  }, [settings]);

  const handleSave = async () => {
    setIsSaving(true);

    const updatedSettings = {};

    // Добавляем только измененные поля
    if (telegramApiId) updatedSettings.telegram_api_id = telegramApiId;
    if (telegramApiHash) updatedSettings.telegram_api_hash = telegramApiHash;
    if (telegramPhone) updatedSettings.telegram_phone = telegramPhone;
    if (claudeApiKey) updatedSettings.claude_api_key = claudeApiKey;

    try {
      await onUpdate(updatedSettings);
    } finally {
      setIsSaving(false);
    }
  };

  const hasTelegramConfig = settings?.has_telegram_config;
  const hasClaudeConfig = settings?.has_claude_config;

  return (
    <Container>
      {/* Telegram API Settings */}
      <Section>
        <SectionTitle>📱 Telegram API</SectionTitle>

        <StatusIndicator configured={hasTelegramConfig}>
          {hasTelegramConfig ? '✅ Настроено' : '⚠️ Требуется настройка'}
        </StatusIndicator>

        <InstructionBox>
          <strong>Как получить Telegram API ключи:</strong>
          <StepList>
            <li>Перейдите на <Link href="https://my.telegram.org/apps" target="_blank">my.telegram.org/apps</Link></li>
            <li>Войдите с номером телефона</li>
            <li>Создайте приложение (любое название)</li>
            <li>Скопируйте API_ID и API_HASH</li>
          </StepList>
        </InstructionBox>

        <InputGroup>
          <Label>API ID *</Label>
          <Input
            type="text"
            placeholder="1234567"
            value={telegramApiId}
            onChange={(e) => setTelegramApiId(e.target.value)}
          />
          <InfoText>Числовой идентификатор вашего приложения</InfoText>
        </InputGroup>

        <InputGroup>
          <Label>API Hash *</Label>
          <Input
            type="password"
            placeholder={hasTelegramConfig ? '••••••••••••••••' : 'abcdef1234567890abcdef1234567890'}
            value={telegramApiHash}
            onChange={(e) => setTelegramApiHash(e.target.value)}
          />
          <InfoText>32-символьный хеш вашего приложения</InfoText>
        </InputGroup>

        <InputGroup>
          <Label>Номер телефона *</Label>
          <Input
            type="tel"
            placeholder="+79991234567"
            value={telegramPhone}
            onChange={(e) => setTelegramPhone(e.target.value)}
          />
          <InfoText>Ваш номер телефона в международном формате</InfoText>
        </InputGroup>
      </Section>

      <Divider />

      {/* Claude API Settings */}
      <Section>
        <SectionTitle>🤖 Claude AI API</SectionTitle>

        <StatusIndicator configured={hasClaudeConfig}>
          {hasClaudeConfig ? '✅ Настроено' : '⚠️ Требуется настройка'}
        </StatusIndicator>

        <InstructionBox>
          <strong>Как получить Claude API ключ:</strong>
          <StepList>
            <li>Перейдите на <Link href="https://console.anthropic.com" target="_blank">console.anthropic.com</Link></li>
            <li>Зарегистрируйтесь или войдите</li>
            <li>Перейдите в раздел "API Keys"</li>
            <li>Создайте новый ключ</li>
            <li>Скопируйте ключ (он начинается с "sk-ant-...")</li>
          </StepList>
        </InstructionBox>

        <InputGroup>
          <Label>API Key *</Label>
          <Input
            type="password"
            placeholder={hasClaudeConfig ? '••••••••••••••••' : 'sk-ant-api03-...'}
            value={claudeApiKey}
            onChange={(e) => setClaudeApiKey(e.target.value)}
          />
          <InfoText>Ваш Claude API ключ (хранится в зашифрованном виде)</InfoText>
        </InputGroup>
      </Section>

      <Button onClick={handleSave} disabled={isSaving}>
        {isSaving ? '💾 Сохранение...' : '💾 Сохранить настройки'}
      </Button>

      {/* Security Info */}
      <Section style={{ marginTop: '16px' }}>
        <SectionTitle>🔒 Безопасность</SectionTitle>
        <InfoText>
          <strong>Ваши данные защищены:</strong><br />
          • Все API ключи хранятся в зашифрованном виде<br />
          • Данные хранятся только на сервере бота<br />
          • Доступ есть только у вас<br />
          • Мы не имеем доступа к вашим ключам
        </InfoText>
      </Section>

      {/* Help Section */}
      <Section>
        <SectionTitle>❓ Помощь</SectionTitle>
        <InfoText>
          <strong>Возникли проблемы?</strong><br />
          • Проверьте правильность ввода ключей<br />
          • Убедитесь, что номер телефона в формате +7...<br />
          • Для Claude API нужен активный аккаунт с балансом<br />
          • При ошибках проверьте логи в консоли
        </InfoText>
      </Section>
    </Container>
  );
}

export default SettingsTab;
