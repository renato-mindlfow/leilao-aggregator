import { useAuth } from '../../contexts/AuthContext';
import { Button } from '@/components/ui/button';

export const TrialBanner = () => {
  const { 
    user, 
    profile, 
    getRemainingTrialViews, 
    getTrialDaysRemaining,
    setShowPricingModal 
  } = useAuth();

  if (!user || !profile || profile.subscription_status !== 'trial') {
    return null;
  }

  const trialViews = getRemainingTrialViews();
  const trialDays = getTrialDaysRemaining();
  
  const isLow = trialViews <= 5 || trialDays <= 3;
  const isExpired = trialViews <= 0 || trialDays <= 0;

  if (isExpired) {
    return (
      <div className="bg-red-500 text-white px-4 py-2 text-center text-sm">
        Seu trial expirou! 
        <Button 
          onClick={() => setShowPricingModal(true)}
          variant="ghost"
          className="ml-2 text-white hover:bg-white/20 h-auto p-1"
        >
          Assine agora
        </Button>
      </div>
    );
  }

  return (
    <div className={`${isLow ? 'bg-amber-500' : 'bg-emerald-500'} text-white px-4 py-2 text-center text-sm`}>
      🎉 Trial gratuito: <strong>{trialDays} dias</strong> e <strong>{trialViews} visualizações</strong> restantes
      <Button 
        onClick={() => setShowPricingModal(true)}
        variant="secondary"
        className="ml-3 bg-white text-emerald-600 hover:bg-gray-100 h-auto py-1 px-3 text-xs"
      >
        Assinar agora
      </Button>
    </div>
  );
};

export default TrialBanner;


