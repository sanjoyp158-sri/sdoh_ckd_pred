import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';
import { modelPerformanceService } from '../services/modelPerformanceService';
import { MetricRow, SubgroupRow, ShapFeature } from '../types/modelPerformance';
import './ModelDashboard.css';

const CATEGORY_COLORS: Record<string, string> = {
  Clinical: '#3b82f6',
  SDOH: '#8b5cf6',
  Utilization: '#6b7280',
  Interaction: '#f59e0b',
};

function MetricCard({ label, value, subtitle }: { label: string; value: string; subtitle?: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );
}

function PerformanceTable({ metrics }: { metrics: MetricRow[] }) {
  return (
    <div className="dashboard-card">
      <h2 className="card-title">Table 2: Performance Metrics</h2>
      <div className="table-wrapper">
        <table className="perf-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Cohort</th>
              <th>AUROC (95% CI)</th>
              <th>Sensitivity</th>
              <th>Specificity</th>
              <th>PPV</th>
              <th>NPV</th>
              <th>F1</th>
              <th>AUPRC</th>
              <th>Brier</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, i) => (
              <tr key={i} className={m.model.includes('Clinical') ? 'baseline-row' : ''}>
                <td className="model-name">{m.model}</td>
                <td>{m.cohort}</td>
                <td className="auroc-cell">{m.AUROC_95CI}</td>
                <td>{m.Sensitivity.toFixed(2)}</td>
                <td>{m.Specificity.toFixed(2)}</td>
                <td>{m.PPV.toFixed(2)}</td>
                <td>{m.NPV.toFixed(2)}</td>
                <td>{m.F1.toFixed(2)}</td>
                <td>{m.AUPRC.toFixed(2)}</td>
                <td>{m.Brier.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ShapChart({ features }: { features: ShapFeature[] }) {
  const data = features.slice(0, 12).map((f) => ({
    name: f.feature.replace(/_/g, ' '),
    value: f.shap_pct,
    category: f.category,
  }));

  return (
    <div className="dashboard-card">
      <h2 className="card-title">SHAP Feature Importance</h2>
      <div className="chart-legend">
        {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
          <span key={cat} className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: color }} />
            {cat}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data} layout="vertical" margin={{ left: 140 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" unit="%" />
          <YAxis dataKey="name" type="category" width={135} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(val: number) => `${val.toFixed(1)}%`} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={CATEGORY_COLORS[entry.category] || '#94a3b8'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EquityChart({ subgroups }: { subgroups: SubgroupRow[] }) {
  const data = subgroups.map((s) => ({
    name: s.subgroup,
    AUROC: s.AUROC,
    PPV: s.PPV,
    N: s.N,
  }));

  return (
    <div className="dashboard-card">
      <h2 className="card-title">Table 3: Equity Analysis (Subgroup AUROC)</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" angle={-20} textAnchor="end" tick={{ fontSize: 11 }} />
          <YAxis domain={[0.5, 1.0]} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(val: number, name: string) => [val.toFixed(4), name]}
            labelFormatter={(label) => {
              const sg = subgroups.find((s) => s.subgroup === label);
              return `${label} (n=${sg?.N.toLocaleString()})`;
            }}
          />
          <Legend />
          <Bar dataKey="AUROC" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="PPV" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="equity-table">
        <table className="perf-table">
          <thead>
            <tr>
              <th>Subgroup</th>
              <th>N</th>
              <th>AUROC (95% CI)</th>
              <th>PPV</th>
              <th>Sensitivity</th>
              <th>F1</th>
            </tr>
          </thead>
          <tbody>
            {subgroups.map((s, i) => (
              <tr key={i}>
                <td className="model-name">{s.subgroup}</td>
                <td>{s.N.toLocaleString()}</td>
                <td>{s.AUROC_95CI}</td>
                <td>{s.PPV.toFixed(2)}</td>
                <td>{s.Sensitivity.toFixed(2)}</td>
                <td>{s.F1.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ModelDashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['model-performance'],
    queryFn: () => modelPerformanceService.getPerformance(),
  });

  if (isLoading) {
    return (
      <div className="model-dashboard">
        <div className="loading-state">Loading model performance data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="model-dashboard">
        <div className="error-state">
          Unable to load model performance data. Ensure the backend is running
          and the pipeline has been executed (steps 2-4).
        </div>
      </div>
    );
  }

  // Extract key metrics for header cards
  const fullExt = data.performance_metrics.find(
    (m) => m.model === 'SDOH-CKDPred' && m.cohort.includes('External')
  );
  const baseExt = data.performance_metrics.find(
    (m) => m.model.includes('Clinical') && m.cohort.includes('External')
  );
  const aurocGap = fullExt && baseExt ? fullExt.AUROC - baseExt.AUROC : 0;

  // SHAP category totals
  const categoryTotals: Record<string, number> = {};
  data.shap_importance.forEach((f) => {
    categoryTotals[f.category] = (categoryTotals[f.category] || 0) + f.shap_pct;
  });

  return (
    <div className="model-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Model Performance Dashboard</h1>
          <p className="dashboard-subtitle">SDOH-CKDPred Evaluation Results</p>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="metrics-row">
        <MetricCard
          label="SDOH-CKDPred AUROC"
          value={fullExt?.AUROC.toFixed(3) || '-'}
          subtitle={fullExt?.AUROC_95CI}
        />
        <MetricCard
          label="Clinical-Only AUROC"
          value={baseExt?.AUROC.toFixed(3) || '-'}
          subtitle={baseExt?.AUROC_95CI}
        />
        <MetricCard
          label="AUROC Improvement"
          value={`+${(aurocGap * 100).toFixed(1)} pp`}
          subtitle="P < 0.001 (DeLong's test)"
        />
        <MetricCard
          label="Sensitivity"
          value={fullExt?.Sensitivity.toFixed(2) || '-'}
          subtitle={`PPV: ${fullExt?.PPV.toFixed(2) || '-'}`}
        />
        <MetricCard
          label="Brier Score"
          value={fullExt?.Brier.toFixed(3) || '-'}
          subtitle="Lower is better"
        />
      </div>

      {/* Performance Table */}
      <PerformanceTable metrics={data.performance_metrics} />

      {/* Charts Row */}
      <div className="charts-row">
        <ShapChart features={data.shap_importance} />
      </div>

      {/* SHAP Category Summary */}
      <div className="dashboard-card category-summary">
        <h2 className="card-title">SHAP Category Contributions</h2>
        <div className="category-bars">
          {Object.entries(categoryTotals)
            .sort(([, a], [, b]) => b - a)
            .map(([cat, pct]) => (
              <div key={cat} className="category-bar-row">
                <span className="category-label">{cat}</span>
                <div className="category-bar-bg">
                  <div
                    className="category-bar-fill"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: CATEGORY_COLORS[cat] || '#94a3b8',
                    }}
                  />
                </div>
                <span className="category-pct">{pct.toFixed(1)}%</span>
              </div>
            ))}
        </div>
      </div>

      {/* Equity Analysis */}
      <EquityChart subgroups={data.subgroup_equity} />

      {/* Model Comparison */}
      {data.model_comparison.length > 0 && (
        <div className="dashboard-card">
          <h2 className="card-title">Model Comparison</h2>
          <div className="table-wrapper">
            <table className="perf-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>AUROC</th>
                </tr>
              </thead>
              <tbody>
                {data.model_comparison.map((m, i) => (
                  <tr key={i} className={m.model === 'XGBoost' ? 'highlight-row' : ''}>
                    <td className="model-name">{m.model}</td>
                    <td>{m.AUROC}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default ModelDashboard;
