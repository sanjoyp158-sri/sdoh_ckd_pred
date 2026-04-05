import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientService } from '../services/patientService';
import { useAuthStore } from '../stores/authStore';
import { PatientDetail as PatientDetailType } from '../types/patientDetail';
import { format } from 'date-fns';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import './PatientDetail.css';

function PatientDetail() {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [showAcknowledgeSuccess, setShowAcknowledgeSuccess] = useState(false);

  const { data: patient, isLoading, error } = useQuery<PatientDetailType>({
    queryKey: ['patient', patientId],
    queryFn: () => patientService.getPatient(patientId!),
    enabled: !!patientId,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: () => patientService.acknowledgePatient(patientId!, user?.id || ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId] });
      setShowAcknowledgeSuccess(true);
      setTimeout(() => setShowAcknowledgeSuccess(false), 3000);
    },
  });

  if (isLoading) {
    return <div className="loading">Loading patient details...</div>;
  }

  if (error || !patient) {
    return <div className="error">Error loading patient details</div>;
  }

  const shapData = patient.prediction.shap_explanation.top_factors.map((factor) => ({
    name: factor.feature_name,
    value: factor.shap_value,
    category: factor.category,
  }));

  const egfrTrendData = patient.clinical.egfr_history.map((point) => ({
    date: format(new Date(point.date), 'MMM yyyy'),
    egfr: point.value,
  }));

  const getRiskColor = () => {
    switch (patient.prediction.risk_tier) {
      case 'HIGH':
        return '#ef4444';
      case 'MODERATE':
        return '#f59e0b';
      case 'LOW':
        return '#10b981';
      default:
        return '#6b7280';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'clinical':
        return '#3b82f6';
      case 'administrative':
        return '#8b5cf6';
      case 'sdoh':
        return '#ec4899';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="patient-detail">
      <div className="detail-header">
        <button onClick={() => navigate('/patients')} className="back-button">
          ← Back to Patients
        </button>
        <h1>Patient {patient.patient_id}</h1>
      </div>

      {showAcknowledgeSuccess && (
        <div className="success-message">
          Patient acknowledged successfully
        </div>
      )}

      <div className="detail-grid">
        {/* Risk Score Card */}
        <div className="card risk-card">
          <h2>Risk Assessment</h2>
          <div className="risk-score-display">
            <div
              className="risk-score-circle"
              style={{ borderColor: getRiskColor() }}
            >
              <span className="risk-score-value">
                {(patient.prediction.risk_score * 100).toFixed(1)}%
              </span>
              <span className="risk-score-label">Risk Score</span>
            </div>
            <div className="risk-tier-badge" style={{ backgroundColor: getRiskColor() }}>
              {patient.prediction.risk_tier} RISK
            </div>
          </div>
          <div className="risk-info">
            <div className="info-row">
              <span>Prediction Date:</span>
              <span>{format(new Date(patient.prediction.prediction_date), 'MMM dd, yyyy')}</span>
            </div>
            <div className="info-row">
              <span>Baseline Risk:</span>
              <span>{(patient.prediction.shap_explanation.baseline_risk * 100).toFixed(1)}%</span>
            </div>
          </div>
          {!patient.acknowledged && (
            <button
              onClick={() => acknowledgeMutation.mutate()}
              disabled={acknowledgeMutation.isPending}
              className="acknowledge-button"
            >
              {acknowledgeMutation.isPending ? 'Acknowledging...' : 'Acknowledge Review'}
            </button>
          )}
          {patient.acknowledged && (
            <div className="acknowledged-badge">✓ Acknowledged</div>
          )}
        </div>

        {/* Demographics Card */}
        <div className="card">
          <h2>Demographics</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Age</span>
              <span className="info-value">{patient.demographics.age} years</span>
            </div>
            <div className="info-item">
              <span className="info-label">Sex</span>
              <span className="info-value">{patient.demographics.sex}</span>
            </div>
          </div>
        </div>

        {/* Clinical Data Card */}
        <div className="card clinical-card">
          <h2>Clinical Indicators</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">eGFR</span>
              <span className="info-value">{patient.clinical.egfr.toFixed(1)} mL/min/1.73m²</span>
            </div>
            <div className="info-item">
              <span className="info-label">CKD Stage</span>
              <span className="info-value">Stage {patient.clinical.ckd_stage}</span>
            </div>
            <div className="info-item">
              <span className="info-label">UACR</span>
              <span className="info-value">{patient.clinical.uacr.toFixed(1)} mg/g</span>
            </div>
            <div className="info-item">
              <span className="info-label">HbA1c</span>
              <span className="info-value">{patient.clinical.hba1c.toFixed(1)}%</span>
            </div>
            <div className="info-item">
              <span className="info-label">Blood Pressure</span>
              <span className="info-value">
                {patient.clinical.systolic_bp}/{patient.clinical.diastolic_bp} mmHg
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">BMI</span>
              <span className="info-value">{patient.clinical.bmi.toFixed(1)} kg/m²</span>
            </div>
          </div>
          {patient.clinical.comorbidities.length > 0 && (
            <div className="comorbidities">
              <span className="info-label">Comorbidities:</span>
              <div className="comorbidity-tags">
                {patient.clinical.comorbidities.map((condition) => (
                  <span key={condition} className="tag">
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Administrative Data Card */}
        <div className="card">
          <h2>Administrative Metrics</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Visits (12 mo)</span>
              <span className="info-value">{patient.administrative.visit_frequency_12mo}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Insurance</span>
              <span className="info-value">{patient.administrative.insurance_type}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Visit</span>
              <span className="info-value">
                {format(new Date(patient.administrative.last_visit_date), 'MMM dd, yyyy')}
              </span>
            </div>
          </div>
        </div>

        {/* SDOH Data Card */}
        <div className="card">
          <h2>Social Determinants of Health</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">ADI Percentile</span>
              <span className="info-value">{patient.sdoh.adi_percentile}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Food Desert</span>
              <span className="info-value">{patient.sdoh.food_desert ? 'Yes' : 'No'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Housing Stability</span>
              <span className="info-value">
                {(patient.sdoh.housing_stability_score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Transportation Access</span>
              <span className="info-value">
                {(patient.sdoh.transportation_access_score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Location</span>
              <span className="info-value">{patient.sdoh.rural_urban_code}</span>
            </div>
          </div>
        </div>
      </div>

      {/* SHAP Explanation Chart */}
      <div className="card chart-card">
        <h2>Top Risk Factors (SHAP Analysis)</h2>
        <p className="chart-description">
          These factors contribute most to the patient's risk score. Positive values increase risk,
          negative values decrease risk.
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={shapData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={150} />
            <Tooltip />
            <Bar
              dataKey="value"
              fill="#3b82f6"
              shape={(props: any) => {
                const fill = getCategoryColor(props.payload.category);
                return <rect {...props} fill={fill} />;
              }}
            />
          </BarChart>
        </ResponsiveContainer>
        <div className="legend">
          <span className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#3b82f6' }}></span>
            Clinical
          </span>
          <span className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#8b5cf6' }}></span>
            Administrative
          </span>
          <span className="legend-item">
            <span className="legend-color" style={{ backgroundColor: '#ec4899' }}></span>
            SDOH
          </span>
        </div>
      </div>

      {/* eGFR Trend Chart */}
      {egfrTrendData.length > 0 && (
        <div className="card chart-card">
          <h2>eGFR Trend</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={egfrTrendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis label={{ value: 'eGFR (mL/min/1.73m²)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="egfr"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 4 }}
                name="eGFR"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default PatientDetail;
