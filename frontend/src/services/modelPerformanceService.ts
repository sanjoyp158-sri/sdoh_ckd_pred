import api from './api';
import { ModelPerformanceData } from '../types/modelPerformance';

export const modelPerformanceService = {
  getPerformance: async (): Promise<ModelPerformanceData> => {
    const response = await api.get('/model-performance');
    return response.data;
  },
};
