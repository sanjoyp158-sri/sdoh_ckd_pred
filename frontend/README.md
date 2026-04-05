# CKD Early Detection System - Provider Dashboard

React-based provider dashboard for the CKD Early Detection System.

## Technology Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router** for routing
- **TanStack Query** for data fetching
- **Zustand** for state management
- **Recharts** for data visualization
- **Vitest** for testing

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Layout.tsx
│   ├── pages/          # Page components
│   │   ├── Login.tsx
│   │   ├── PatientList.tsx
│   │   └── PatientDetail.tsx
│   ├── stores/         # Zustand stores
│   │   └── authStore.ts
│   ├── services/       # API services
│   ├── types/          # TypeScript types
│   ├── test/           # Test utilities
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## Features

- **Authentication**: JWT-based authentication with role-based access control
- **Patient List**: Filterable and sortable patient list with risk stratification
- **Patient Detail**: Detailed patient view with SHAP explanations and clinical data
- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: Automatic data refresh with TanStack Query

## Requirements Validation

- **Requirement 6.1**: Provider dashboard displays all patients with risk scores and tiers
- **Requirement 6.2**: Filtering by risk tier, CKD stage, and date range
- **Requirement 6.3**: Patient detail view with top 5 SHAP factors
- **Requirement 6.4**: Display of clinical, administrative, and SDOH indicators
- **Requirement 6.5**: Provider acknowledgment recording
