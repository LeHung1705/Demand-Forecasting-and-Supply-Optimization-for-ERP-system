import { useApp } from '../context/AppContext';

export const useAuth = () => {
  const { user, login, logout } = useApp();

  const isAuthenticated = () => {
    return !!user && !!localStorage.getItem('token');
  };

  const hasRole = (role) => {
    return user?.roles?.includes(role) || false;
  };

  return {
    user,
    login,
    logout,
    isAuthenticated,
    hasRole,
  };
};
