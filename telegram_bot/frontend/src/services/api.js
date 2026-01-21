import axios from 'axios';

/**
 * API сервис для взаимодействия с backend
 */
class ApiService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.initData = null;

    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor для добавления initData к каждому запросу
    this.client.interceptors.request.use((config) => {
      if (this.initData && config.data) {
        config.data = {
          ...config.data,
          init_data: this.initData,
        };
      }
      return config;
    });
  }

  /**
   * Установка initData от Telegram WebApp
   */
  setInitData(initData) {
    this.initData = initData;
  }

  /**
   * Валидация аутентификации
   */
  async validateAuth() {
    const response = await this.client.post('/auth/validate', {
      init_data: this.initData,
    });
    return response.data;
  }

  /**
   * Получение настроек пользователя
   */
  async getSettings() {
    const response = await this.client.post('/settings/get', {
      init_data: this.initData,
    });
    return response.data;
  }

  /**
   * Обновление настроек пользователя
   */
  async updateSettings(settings) {
    const response = await this.client.post('/settings/update', {
      init_data: this.initData,
      ...settings,
    });
    return response.data;
  }

  /**
   * Запуск экспорта чата
   */
  async startExport(chatIdentifier, dateFrom, dateTo) {
    const response = await this.client.post('/export/start', {
      init_data: this.initData,
      chat_identifier: chatIdentifier,
      date_from: dateFrom,
      date_to: dateTo,
    });
    return response.data;
  }

  /**
   * Получение статуса экспорта
   */
  async getExportStatus(taskId) {
    const response = await this.client.get(`/export/status/${taskId}`, {
      params: {
        init_data: this.initData,
      },
    });
    return response.data;
  }

  /**
   * Скачивание результата экспорта
   */
  getExportDownloadUrl(taskId) {
    return `${this.baseURL}/export/download/${taskId}?init_data=${encodeURIComponent(this.initData)}`;
  }

  /**
   * Запуск анализа CSV файла
   */
  async startAnalysis(file) {
    const formData = new FormData();
    formData.append('csv_file', file);
    formData.append('init_data', this.initData);

    const response = await this.client.post('/analyze/start', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  /**
   * Скачивание результата анализа
   */
  getAnalysisDownloadUrl(filename) {
    return `${this.baseURL}/analyze/download/${filename}?init_data=${encodeURIComponent(this.initData)}`;
  }
}

export const apiService = new ApiService();
