import api from './api';
import { PatientFilters, PatientsResponse } from '../types/patient';

export const patientService = {
  getPatients: async (filters?: PatientFilters): Promise<PatientsResponse> => {
    const params = new URLSearchParams();
    
    if (filters?.risk_tier) params.append('risk_tier', filters.risk_tier);
    if (filters?.ckd_stage) params.append('ckd_stage', filters.ckd_stage);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    if (filters?.search) params.append('search', filters.search);
    
    const response = await api.get(`/patients?${params.toString()}`);
    return response.data;
  },

  getPatient: async (patientId: string) => {
    const response = await api.get(`/patients/${patientId}`);
    return response.data;
  },

  acknowledgePatient: async (patientId: string, providerId: string) => {
    const response = await api.post('/acknowledgments', {
      patient_id: patientId,
      provider_id: providerId,
    });
    return response.data;
  },
};
