import { useAuthStore } from '../stores/authStore';
import './Header.css';

function Header() {
  const { user, logout } = useAuthStore();

  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">CKD Early Detection System</h1>
        <div className="header-actions">
          <span className="header-user">
            {user?.username} ({user?.role})
          </span>
          <button onClick={logout} className="header-logout">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
