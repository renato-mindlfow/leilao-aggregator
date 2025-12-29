import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { createClient, User } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  subscription_status: string;
  subscription_plan?: string;
  trial_end_date?: string;
  trial_views_used?: number;
  trial_views_limit?: number;
  subscription_end_date?: string;
}

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  showLoginModal: boolean;
  setShowLoginModal: (show: boolean) => void;
  showPricingModal: boolean;
  setShowPricingModal: (show: boolean) => void;
  signInWithEmail: (email: string, password: string) => Promise<{ data: any; error: any }>;
  signUpWithEmail: (email: string, password: string, name: string) => Promise<{ data: any; error: any }>;
  signInWithGoogle: () => Promise<{ data: any; error: any }>;
  signOut: () => Promise<void>;
  checkAccess: () => Promise<{ can_view: boolean; reason?: string }>;
  incrementView: (propertyId: string) => Promise<void>;
  createCheckout: (plan?: string) => Promise<string | null>;
  canViewProperty: () => boolean;
  getRemainingTrialViews: () => number;
  getTrialDaysRemaining: () => number;
  isAdmin: () => boolean;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = import.meta.env.VITE_API_URL || 'https://leilao-backend-solitary-haze-9882.fly.dev';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);

  useEffect(() => {
    // Verificar sessão atual
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProfile(session.user.id);
      }
      setLoading(false);
    });

    // Listener para mudanças de auth
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        setUser(session?.user ?? null);
        if (session?.user) {
          await fetchProfile(session.user.id);
        } else {
          setProfile(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (userId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/user/profile/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
      }
    } catch (error) {
      console.error('Erro ao buscar perfil:', error);
    }
  };

  const signInWithEmail = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { data, error };
  };

  const signUpWithEmail = async (email: string, password: string, name: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { name }
      }
    });
    return { data, error };
  };

  const signInWithGoogle = async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: 'https://leilohub.com.br'
      }
    });
    return { data, error };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setProfile(null);
  };

  const checkAccess = async () => {
    if (!user) return { can_view: false, reason: 'not_logged_in' };
    
    try {
      const response = await fetch(`${API_URL}/api/user/check-access/${user.id}`, {
        method: 'POST'
      });
      return await response.json();
    } catch (error) {
      console.error('Erro ao verificar acesso:', error);
      return { can_view: false, reason: 'error' };
    }
  };

  const incrementView = async (propertyId: string) => {
    if (!user) return;
    
    try {
      await fetch(`${API_URL}/api/user/increment-view/${user.id}?property_id=${propertyId}`, {
        method: 'POST'
      });
      // Atualizar perfil após incrementar
      await fetchProfile(user.id);
    } catch (error) {
      console.error('Erro ao incrementar view:', error);
    }
  };

  const createCheckout = async (plan = 'monthly') => {
    if (!user || !profile) return null;
    
    try {
      const response = await fetch(
        `${API_URL}/api/asaas/create-checkout?user_id=${user.id}&user_name=${encodeURIComponent(profile.name || user.email || '')}&user_email=${encodeURIComponent(user.email || '')}&plan=${plan}`,
        { method: 'POST' }
      );
      
      if (response.ok) {
        const data = await response.json();
        return data.checkout_url;
      }
    } catch (error) {
      console.error('Erro ao criar checkout:', error);
    }
    return null;
  };

  const canViewProperty = () => {
    if (!profile) return false;
    if (profile.role === 'admin') return true;
    if (profile.subscription_status === 'active') return true;
    if (profile.subscription_status === 'trial') {
      const trialEnd = new Date(profile.trial_end_date || '');
      const now = new Date();
      return trialEnd > now && (profile.trial_views_used || 0) < (profile.trial_views_limit || 20);
    }
    return false;
  };

  const getRemainingTrialViews = () => {
    if (!profile || profile.subscription_status !== 'trial') return 0;
    return Math.max(0, (profile.trial_views_limit || 20) - (profile.trial_views_used || 0));
  };

  const getTrialDaysRemaining = () => {
    if (!profile || profile.subscription_status !== 'trial') return 0;
    const trialEnd = new Date(profile.trial_end_date || '');
    const now = new Date();
    const diff = trialEnd.getTime() - now.getTime();
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  };

  const isAdmin = () => profile?.role === 'admin';

  const value: AuthContextType = {
    user,
    profile,
    loading,
    showLoginModal,
    setShowLoginModal,
    showPricingModal,
    setShowPricingModal,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signOut,
    checkAccess,
    incrementView,
    createCheckout,
    canViewProperty,
    getRemainingTrialViews,
    getTrialDaysRemaining,
    isAdmin,
    refreshProfile: () => user ? fetchProfile(user.id) : Promise.resolve(),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

