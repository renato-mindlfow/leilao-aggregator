import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { X, Check, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';

export const PricingModal = () => {
  const { 
    showPricingModal, 
    setShowPricingModal,
    createCheckout,
    profile,
    getRemainingTrialViews,
    getTrialDaysRemaining
  } = useAuth();
  
  const [loading, setLoading] = useState<string | null>(null);

  if (!showPricingModal) return null;

  const handleSubscribe = async (plan: string) => {
    setLoading(plan);
    try {
      const checkoutUrl = await createCheckout(plan);
      if (checkoutUrl) {
        window.location.href = checkoutUrl;
      }
    } catch (error) {
      console.error('Erro ao criar checkout:', error);
    } finally {
      setLoading(null);
    }
  };

  const trialViews = getRemainingTrialViews();
  const trialDays = getTrialDaysRemaining();
  const isTrialExpired = profile?.subscription_status === 'trial' && (trialViews <= 0 || trialDays <= 0);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 sm:p-8 max-w-3xl w-full relative max-h-[90vh] overflow-y-auto">
        {/* Botão Fechar */}
        <button
          onClick={() => setShowPricingModal(false)}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <div className="text-center mb-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-800">
            {isTrialExpired ? 'Seu trial expirou!' : 'Escolha seu plano'}
          </h2>
          <p className="text-gray-500 mt-2">
            {isTrialExpired 
              ? 'Assine agora para continuar acessando todos os imóveis'
              : 'Acesso ilimitado a todos os imóveis de leilão do Brasil'}
          </p>
          
          {profile?.subscription_status === 'trial' && !isTrialExpired && (
            <div className="mt-4 bg-amber-50 text-amber-700 px-4 py-2 rounded-lg inline-block">
              ⏰ Restam <strong>{trialDays} dias</strong> e <strong>{trialViews} visualizações</strong> no seu trial
            </div>
          )}
        </div>

        {/* Planos */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Plano Mensal */}
          <div className="border-2 border-gray-200 rounded-2xl p-6 hover:border-emerald-500 transition">
            <h3 className="text-xl font-bold text-gray-800">Mensal</h3>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-800">R$ 89,90</span>
              <span className="text-gray-500">/mês</span>
            </div>
            
            <ul className="mt-6 space-y-3">
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Acesso ilimitado a imóveis
              </li>
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Alertas de novos leilões
              </li>
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Cancele quando quiser
              </li>
            </ul>
            
            <Button
              onClick={() => handleSubscribe('monthly')}
              disabled={loading === 'monthly'}
              variant="outline"
              className="w-full mt-6 border-2 border-emerald-600 text-emerald-600 hover:bg-emerald-50"
            >
              {loading === 'monthly' ? 'Processando...' : 'Assinar Mensal'}
            </Button>
          </div>

          {/* Plano Anual */}
          <div className="border-2 border-emerald-500 rounded-2xl p-6 relative bg-emerald-50">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white px-4 py-1 rounded-full text-sm font-semibold flex items-center gap-1">
              <Zap size={16} />
              Mais Popular
            </div>
            
            <h3 className="text-xl font-bold text-gray-800">Anual</h3>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-800">R$ 69,90</span>
              <span className="text-gray-500">/mês</span>
            </div>
            <p className="text-emerald-600 font-medium">
              12x de R$ 69,90 = R$ 838,80/ano
            </p>
            <p className="text-emerald-700 text-sm font-semibold mt-1">
              Economize 22% (R$ 240/ano)
            </p>
            
            <ul className="mt-6 space-y-3">
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Tudo do plano mensal
              </li>
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Economia de 22%
              </li>
              <li className="flex items-center gap-2 text-gray-600">
                <Check className="text-emerald-500" size={20} />
                Suporte prioritário
              </li>
            </ul>
            
            <Button
              onClick={() => handleSubscribe('yearly')}
              disabled={loading === 'yearly'}
              className="w-full mt-6 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {loading === 'yearly' ? 'Processando...' : 'Assinar Anual'}
            </Button>
          </div>
        </div>

        {/* Garantia */}
        <p className="text-center text-gray-500 text-sm mt-6">
          🔒 Pagamento seguro • Cancele a qualquer momento • Satisfação garantida
        </p>
      </div>
    </div>
  );
};

export default PricingModal;


