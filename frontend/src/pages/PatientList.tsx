import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { patientService } from '../services/patientService';
import { PatientFilters, RiskTier, CKDStage } from '../types/patient';
import { format } from 'date-fns';
import './PatientList.css';

type SortField = 'risk_score' | 'prediction_date' | 'egfr' | 'patient_id';
type SortDirection = 'asc' | 'desc';

function PatientList() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<PatientFilters>({});
  const [sortField, setSortField] = useState<SortField>('risk_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const { data, isLoading, error } = useQuery({
    queryKey: ['patients', filters],
    queryFn: () => patientService.getPatients(filters),
  });

  const handleFilterChange = (key: keyof PatientFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedPatients = data?.patients ? [...data.patients].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    const multiplier = sortDirection === 'asc' ? 1 : -1;
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return aValue.localeCompare(bValue) * multiplier;
    }
    return ((aValue as number) - (bValue as number)) * multiplier;
  }) : [];

  const getRiskTierColor = (tier: RiskTier) => {
    switch (tier) {
      case RiskTier.HIGH:
        return 'risk-high';
      case RiskTier.MODERATE:
        return 'risk-moderate';
      case RiskTier.LOW:
        return 'risk-low';
      default:
        return '';
    }
  };

  if (isLoading) {
    return <div className="loading">Loading patients...</div>;
  }

  if (error) {
    return <div className="error">Error loading patients</div>;
  }

  return (
    <div className="patient-list">
      <div className="patient-list-header">
        <h1>Patient Risk Dashboard</h1>
        <div className="patient-count">
          {data?.total || 0} patients
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Risk Tier</label>
          <select
            value={filters.risk_tier || ''}
            onChange={(e) => handleFilterChange('risk_tier', e.target.value)}
          >
            <option value="">All</option>
            <option value={RiskTier.HIGH}>High Risk</option>
            <option value={RiskTier.MODERATE}>Moderate Risk</option>
            <option value={RiskTier.LOW}>Low Risk</option>
          </select>
        </div>

        <div className="filter-group">
          <label>CKD Stage</label>
          <select
            value={filters.ckd_stage || ''}
            onChange={(e) => handleFilterChange('ckd_stage', e.target.value)}
          >
            <option value="">All</option>
            <option value={CKDStage.STAGE_2}>Stage 2</option>
            <option value={CKDStage.STAGE_3A}>Stage 3a</option>
            <option value={CKDStage.STAGE_3B}>Stage 3b</option>
            <option value={CKDStage.STAGE_4}>Stage 4</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Date From</label>
          <input
            type="date"
            value={filters.date_from || ''}
            onChange={(e) => handleFilterChange('date_from', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Date To</label>
          <input
            type="date"
            value={filters.date_to || ''}
            onChange={(e) => handleFilterChange('date_to', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Search</label>
          <input
            type="text"
            placeholder="Patient ID..."
            value={filters.search || ''}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table className="patient-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('patient_id')}>
                Patient ID {sortField === 'patient_id' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Age</th>
              <th>Sex</th>
              <th onClick={() => handleSort('risk_score')}>
                Risk Score {sortField === 'risk_score' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Risk Tier</th>
              <th>CKD Stage</th>
              <th onClick={() => handleSort('egfr')}>
                eGFR {sortField === 'egfr' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('prediction_date')}>
                Prediction Date {sortField === 'prediction_date' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedPatients.map((patient) => (
              <tr
                key={patient.patient_id}
                onClick={() => navigate(`/patients/${patient.patient_id}`)}
                className="patient-row"
              >
                <td>{patient.patient_id}</td>
                <td>{patient.age}</td>
                <td>{patient.sex}</td>
                <td>{patient.risk_score.toFixed(3)}</td>
                <td>
                  <span className={`risk-badge ${getRiskTierColor(patient.risk_tier)}`}>
                    {patient.risk_tier.toUpperCase()}
                  </span>
                </td>
                <td>Stage {patient.ckd_stage}</td>
                <td>{patient.egfr.toFixed(1)}</td>
                <td>{format(new Date(patient.prediction_date), 'MMM dd, yyyy')}</td>
                <td>
                  {patient.acknowledged ? (
                    <span className="status-badge status-acknowledged">Acknowledged</span>
                  ) : (
                    <span className="status-badge status-pending">Pending</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PatientList;
