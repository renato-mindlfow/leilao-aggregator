import { useState, useEffect } from 'react';
import { 
  Search, 
  MapPin, 
  TrendingUp, 
  Zap, 
  CheckCircle, 
  Star, 
  ChevronDown,
  Monitor,
  Smartphone,
  Filter,
  BarChart3,
  Clock,
  ArrowRight,
  Play
} from 'lucide-react';

// ===== COMPONENTE CONTADOR ANIMADO =====
const AnimatedCounter = ({ end, suffix = '', duration = 2000 }: { end: number; suffix?: string; duration?: number }) => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    let startTime: number;
    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [end, duration]);
  
  return <span>{count.toLocaleString('pt-BR')}{suffix}</span>;
};

// ===== COMPONENTE FAQ =====
const FAQItem = ({ question, answer }: { question: string; answer: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <div className="border-b border-gray-200">
      <button
        className="w-full py-5 flex justify-between items-center text-left hover:text-sky-600 transition"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-medium text-gray-800 pr-4">{question}</span>
        <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="pb-5 text-gray-600 leading-relaxed">
          {answer}
        </div>
      )}
    </div>
  );
};

// ===== COMPONENTE DEPOIMENTO =====
const Testimonial = ({ name, role, image, text, rating }: { 
  name: string; 
  role: string; 
  image: string; 
  text: string;
  rating: number;
}) => (
  <div className="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow">
    <div className="flex items-center gap-1 mb-4">
      {[...Array(rating)].map((_, i) => (
        <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
      ))}
    </div>
    <p className="text-gray-600 mb-6 leading-relaxed">"{text}"</p>
    <div className="flex items-center gap-3">
      <img src={image} alt={name} className="w-12 h-12 rounded-full object-cover" />
      <div>
        <p className="font-semibold text-gray-800">{name}</p>
        <p className="text-sm text-gray-500">{role}</p>
      </div>
    </div>
  </div>
);

// ===== COMPONENTE PRINCIPAL =====
export default function LandingPage() {
  const [isAnnual, setIsAnnual] = useState(true);

  return (
    <div className="min-h-screen bg-white">
      
      {/* ===== HEADER ===== */}
      <header className="fixed top-0 left-0 right-0 bg-gradient-to-b from-sky-500 to-sky-400 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <a href="/" className="flex items-center gap-3">
              <img 
                src="/logo-horizontal-trimmed.png" 
                alt="LeiloHub" 
                className="h-12 brightness-0 invert"
              />
            </a>
            
            {/* Menu */}
            <nav className="hidden md:flex items-center gap-8">
              <a href="#funcionalidades" className="text-white/90 hover:text-white transition font-medium">Funcionalidades</a>
              <a href="#como-funciona" className="text-white/90 hover:text-white transition font-medium">Como Funciona</a>
              <a href="#precos" className="text-white/90 hover:text-white transition font-medium">Preços</a>
              <a href="#depoimentos" className="text-white/90 hover:text-white transition font-medium">Depoimentos</a>
            </nav>
            
            {/* CTA */}
            <div className="flex items-center gap-4">
              <a href="https://leilohub.com.br" className="text-white/90 hover:text-white transition font-medium hidden sm:block">
                Entrar
              </a>
              <a 
                href="https://leilohub.com.br" 
                className="bg-white text-sky-600 px-5 py-2.5 rounded-lg font-semibold hover:bg-sky-50 transition shadow-md"
              >
                Começar Grátis
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* ===== HERO ===== */}
      <section className="pt-24 pb-20 bg-gradient-to-b from-sky-50 via-white to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            
            {/* Texto */}
            <div>
              <div className="inline-flex items-center gap-2 bg-sky-100 text-sky-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
                <Zap className="w-4 h-4" />
                A plataforma mais tecnológica do mercado
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-6">
                Encontre o imóvel de leilão 
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600"> perfeito para você</span>
              </h1>
              
              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                Enquanto seus concorrentes perdem horas vasculhando dezenas de sites, você descobre os <strong>leilões mais escondidos</strong> com um simples clique. Agregamos +280 leiloeiros em um só lugar. Nossa IA analisa, categoriza e encontra as melhores oportunidades com até <strong>99% de desconto</strong>.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <a 
                  href="/" 
                  className="bg-gradient-to-r from-sky-500 to-blue-600 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:shadow-xl hover:shadow-sky-500/25 transition flex items-center justify-center gap-2"
                >
                  Testar Grátis por 10 Dias
                  <ArrowRight className="w-5 h-5" />
                </a>
                <a 
                  href="#como-funciona" 
                  className="border-2 border-gray-200 text-gray-700 px-8 py-4 rounded-xl font-semibold text-lg hover:border-sky-500 hover:text-sky-600 transition flex items-center justify-center gap-2"
                >
                  <Play className="w-5 h-5" />
                  Ver Como Funciona
                </a>
              </div>
              
              <div className="flex items-center gap-6 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-sky-500" />
                  Sem cartão de crédito
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-sky-500" />
                  Cancele quando quiser
                </div>
              </div>
            </div>
            
            {/* Imagem Hero - Mockup Desktop */}
            <div className="relative">
              <div className="bg-gradient-to-br from-sky-500 to-blue-600 rounded-3xl p-1">
                <div className="bg-gray-900 rounded-3xl p-2">
                  <div className="bg-white rounded-2xl overflow-hidden shadow-2xl">
                    {/* Barra do navegador fake */}
                    <div className="bg-gray-100 px-4 py-2 flex items-center gap-2">
                      <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-400"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                        <div className="w-3 h-3 rounded-full bg-green-400"></div>
                      </div>
                      <div className="flex-1 bg-white rounded px-3 py-1 text-xs text-gray-400 ml-4">
                        leilohub.com.br
                      </div>
                    </div>
                    {/* Screenshot da plataforma - placeholder melhorado */}
                    <div className="aspect-video bg-gradient-to-br from-sky-50 to-blue-50 p-6">
                      {/* Header fake */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-yellow-500 rounded"></div>
                          <div className="bg-gray-300 rounded h-4 w-20"></div>
                        </div>
                        <div className="flex gap-2">
                          <div className="bg-sky-500 rounded h-6 w-16"></div>
                          <div className="bg-gray-200 rounded h-6 w-16"></div>
                        </div>
                      </div>
                      
                      {/* Cards fake */}
                      <div className="grid grid-cols-3 gap-3">
                        {[1,2,3].map(i => (
                          <div key={i} className="bg-white rounded-lg shadow p-3">
                            <div className="bg-gradient-to-br from-sky-100 to-sky-200 rounded h-20 mb-2 flex items-center justify-center">
                              <span className="text-sky-400 text-xs">Imóvel</span>
                            </div>
                            <div className="bg-gray-200 rounded h-2 w-3/4 mb-1"></div>
                            <div className="bg-gray-100 rounded h-2 w-1/2 mb-2"></div>
                            <div className="flex justify-between">
                              <div className="bg-green-100 rounded h-3 w-12"></div>
                              <div className="bg-sky-500 rounded h-3 w-16"></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Badge flutuante */}
              <div className="absolute -bottom-6 -left-6 bg-white rounded-2xl shadow-xl p-4 flex items-center gap-3">
                <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-sky-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-800">70%</p>
                  <p className="text-sm text-gray-500">economia de tempo</p>
                </div>
              </div>
              
              {/* Badge flutuante direita */}
              <div className="absolute -top-4 -right-4 bg-white rounded-2xl shadow-xl p-4">
                <div className="flex items-center gap-2">
                  <div className="flex -space-x-2">
                    <div className="w-8 h-8 bg-sky-500 rounded-full border-2 border-white"></div>
                    <div className="w-8 h-8 bg-blue-500 rounded-full border-2 border-white"></div>
                    <div className="w-8 h-8 bg-indigo-500 rounded-full border-2 border-white"></div>
                  </div>
                  <p className="text-sm text-gray-600">+500 investidores</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== MÉTRICAS ===== */}
      <section className="py-16 bg-white border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <p className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600">
                <AnimatedCounter end={30000} suffix="+" />
              </p>
              <p className="text-gray-600 mt-2">Imóveis disponíveis</p>
            </div>
            <div className="text-center">
              <p className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600">
                <AnimatedCounter end={280} suffix="+" />
              </p>
              <p className="text-gray-600 mt-2">Leiloeiros monitorados</p>
            </div>
            <div className="text-center">
              <p className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600">
                <AnimatedCounter end={99} suffix="%" />
              </p>
              <p className="text-gray-600 mt-2">Desconto máximo encontrado</p>
            </div>
            <div className="text-center">
              <p className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-500 to-blue-600">
                <AnimatedCounter end={27} />
              </p>
              <p className="text-gray-600 mt-2">Estados cobertos</p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== PROBLEMA / SOLUÇÃO ===== */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              Chega de informações duplicadas e truncadas
            </h2>
            <p className="text-xl text-gray-600">
              Você merece a <strong>melhor ferramenta do mercado</strong> nas suas mãos. Enquanto outros agregadores entregam dados incompletos e desatualizados, o LeiloHub usa inteligência artificial para garantir qualidade.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8">
            {/* Sem LeiloHub */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100">
              <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center mb-6">
                <span className="text-2xl">😩</span>
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-4">Sem o LeiloHub</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3 text-gray-600">
                  <span className="text-red-500 mt-1">✗</span>
                  Horas vasculhando dezenas de sites diferentes
                </li>
                <li className="flex items-start gap-3 text-gray-600">
                  <span className="text-red-500 mt-1">✗</span>
                  Informações desatualizadas e incompletas
                </li>
                <li className="flex items-start gap-3 text-gray-600">
                  <span className="text-red-500 mt-1">✗</span>
                  Oportunidades perdidas para concorrentes mais rápidos
                </li>
                <li className="flex items-start gap-3 text-gray-600">
                  <span className="text-red-500 mt-1">✗</span>
                  Dados duplicados que confundem sua análise
                </li>
                <li className="flex items-start gap-3 text-gray-600">
                  <span className="text-red-500 mt-1">✗</span>
                  Filtros limitados que não atendem suas necessidades
                </li>
              </ul>
            </div>
            
            {/* Com LeiloHub */}
            <div className="bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl p-8 text-white">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-6">
                <span className="text-2xl">🚀</span>
              </div>
              <h3 className="text-xl font-bold mb-4">Com o LeiloHub</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  Todos os leilões em um único lugar
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  Dados atualizados em tempo real com IA
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  Encontre oportunidades antes da concorrência
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  Sem duplicatas, informações limpas e organizadas
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  Filtros avançados por localização, preço e desconto
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ===== FUNCIONALIDADES ===== */}
      <section id="funcionalidades" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              Funcionalidades que fazem a diferença
            </h2>
            <p className="text-xl text-gray-600">
              Desenvolvido por investidores, para investidores. Cada funcionalidade foi pensada para maximizar seus resultados.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <Search className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Busca Inteligente</h3>
              <p className="text-gray-600">
                Filtros avançados por estado, cidade, categoria, faixa de preço e percentual de desconto. Encontre exatamente o que procura.
              </p>
            </div>
            
            {/* Feature 2 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <MapPin className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Mapa Interativo</h3>
              <p className="text-gray-600">
                Visualize todos os imóveis no mapa. Identifique oportunidades por região e analise a localização antes de investir.
              </p>
            </div>
            
            {/* Feature 3 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <BarChart3 className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Análise de Desconto</h3>
              <p className="text-gray-600">
                Veja o percentual de desconto calculado automaticamente. Ordene por maior desconto e encontre as melhores oportunidades.
              </p>
            </div>
            
            {/* Feature 4 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <Filter className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Dados Limpos</h3>
              <p className="text-gray-600">
                Nossa IA remove duplicatas e normaliza informações. Você recebe dados confiáveis e prontos para análise.
              </p>
            </div>
            
            {/* Feature 5 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <Clock className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Atualização Constante</h3>
              <p className="text-gray-600">
                Monitoramos 280+ leiloeiros automaticamente. Novos imóveis aparecem na plataforma assim que são publicados.
              </p>
            </div>
            
            {/* Feature 6 */}
            <div className="bg-slate-50 rounded-2xl p-6 hover:shadow-lg transition group">
              <div className="w-14 h-14 bg-gradient-to-br from-sky-500 to-blue-600 rounded-2xl flex items-center justify-center mb-5 group-hover:scale-110 transition">
                <Smartphone className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-800 mb-3">Acesso em Qualquer Lugar</h3>
              <p className="text-gray-600">
                Plataforma 100% responsiva. Acesse do computador, tablet ou celular e nunca perca uma oportunidade.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== COMO FUNCIONA ===== */}
      <section id="como-funciona" className="py-20 bg-gradient-to-br from-slate-900 to-slate-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Como funciona
            </h2>
            <p className="text-xl text-slate-300">
              Em 3 passos simples você começa a encontrar as melhores oportunidades
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Passo 1 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-sky-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                1
              </div>
              <h3 className="text-xl font-bold mb-3">Crie sua conta grátis</h3>
              <p className="text-slate-400">
                Cadastro em menos de 1 minuto. Sem cartão de crédito, sem compromisso. 10 dias para testar todas as funcionalidades.
              </p>
            </div>
            
            {/* Passo 2 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-sky-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                2
              </div>
              <h3 className="text-xl font-bold mb-3">Defina seus filtros</h3>
              <p className="text-slate-400">
                Escolha estados, cidades, categorias e faixa de preço. Salve suas buscas favoritas para acessar rapidamente.
              </p>
            </div>
            
            {/* Passo 3 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-sky-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl font-bold">
                3
              </div>
              <h3 className="text-xl font-bold mb-3">Encontre oportunidades</h3>
              <p className="text-slate-400">
                Analise os imóveis, compare preços e descontos. Clique direto no site do leiloeiro para dar seu lance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== DISPOSITIVOS ===== */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
                Acesse de qualquer dispositivo
              </h2>
              <p className="text-xl text-gray-600 mb-8">
                Plataforma 100% responsiva e otimizada. Seja no escritório, em casa ou na rua, você sempre terá acesso às melhores oportunidades de leilão.
              </p>
              
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center">
                    <Monitor className="w-6 h-6 text-sky-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800">Desktop</h4>
                    <p className="text-gray-600">Experiência completa com todas as funcionalidades</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-sky-100 rounded-xl flex items-center justify-center">
                    <Smartphone className="w-6 h-6 text-sky-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800">Mobile</h4>
                    <p className="text-gray-600">Interface otimizada para telas menores</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Mockup dispositivos */}
            <div className="relative">
              {/* Desktop mockup */}
              <div className="bg-gray-900 rounded-2xl p-2 shadow-2xl">
                <div className="bg-white rounded-xl overflow-hidden">
                  <div className="bg-gray-100 px-3 py-1.5 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div>
                    <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                  </div>
                  <div className="aspect-video bg-gradient-to-br from-sky-50 to-blue-50 p-4">
                    {/* Header fake */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-1.5">
                        <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                        <div className="bg-gray-300 rounded h-3 w-16"></div>
                      </div>
                      <div className="flex gap-1.5">
                        <div className="bg-sky-500 rounded h-4 w-12"></div>
                        <div className="bg-gray-200 rounded h-4 w-12"></div>
                      </div>
                    </div>
                    
                    {/* Cards fake melhorados */}
                    <div className="grid grid-cols-3 gap-2">
                      {[1,2,3].map(i => (
                        <div key={i} className="bg-white rounded-lg shadow p-2">
                          <div className="bg-gradient-to-br from-sky-100 to-sky-200 rounded h-12 mb-2 flex items-center justify-center">
                            <span className="text-sky-400 text-xs">Imóvel</span>
                          </div>
                          <div className="bg-gray-200 rounded h-1.5 w-3/4 mb-1"></div>
                          <div className="bg-gray-100 rounded h-1.5 w-1/2 mb-1.5"></div>
                          <div className="flex justify-between">
                            <div className="bg-green-100 rounded h-2.5 w-10"></div>
                            <div className="bg-sky-500 rounded h-2.5 w-12"></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Mobile mockup */}
              <div className="absolute -bottom-8 -right-4 w-32 bg-gray-900 rounded-2xl p-1 shadow-2xl">
                <div className="bg-white rounded-xl overflow-hidden">
                  <div className="bg-gradient-to-r from-sky-500 to-blue-600 h-4 flex items-center justify-center">
                    <div className="w-2 h-2 bg-white/30 rounded-full"></div>
                  </div>
                  <div className="p-2 space-y-2">
                    <div className="bg-white border border-gray-200 rounded p-1.5">
                      <div className="bg-gradient-to-br from-sky-100 to-sky-200 rounded h-8 mb-1"></div>
                      <div className="bg-gray-200 rounded h-1 w-3/4 mb-0.5"></div>
                      <div className="bg-sky-500 rounded h-1 w-1/2"></div>
                    </div>
                    <div className="bg-white border border-gray-200 rounded p-1.5">
                      <div className="bg-gradient-to-br from-sky-100 to-sky-200 rounded h-8 mb-1"></div>
                      <div className="bg-gray-200 rounded h-1 w-3/4 mb-0.5"></div>
                      <div className="bg-sky-500 rounded h-1 w-1/2"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== DEPOIMENTOS ===== */}
      <section id="depoimentos" className="py-20 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              O que nossos clientes dizem
            </h2>
            <p className="text-xl text-gray-600">
              Investidores reais compartilhando suas experiências com o LeiloHub
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <Testimonial
              name="Ricardo Mendes"
              role="Investidor Imobiliário há 8 anos"
              image="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face"
              text="Antes eu gastava 3-4 horas por dia vasculhando sites de leiloeiros. Com o LeiloHub, faço a mesma análise em 20 minutos. Já arrematei 3 imóveis que encontrei exclusivamente aqui."
              rating={5}
            />
            
            <Testimonial
              name="Dra. Camila Santos"
              role="Advogada especializada em leilões"
              image="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop&crop=face"
              text="Recomendo para todos os meus clientes. A plataforma é séria, os dados são confiáveis e o suporte é excelente. Finalmente uma ferramenta profissional nesse mercado."
              rating={5}
            />
            
            <Testimonial
              name="João Paulo Silva"
              role="Primeiro leilão arrematado em 2024"
              image="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face"
              text="Era iniciante e tinha medo de leilões. O LeiloHub me deu segurança para encontrar meu primeiro imóvel. Comprei um apartamento com 45% de desconto!"
              rating={5}
            />
          </div>
        </div>
      </section>

      {/* ===== PREÇOS ===== */}
      <section id="precos" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              Investimento que se paga no primeiro negócio
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Quanto vale encontrar um imóvel com 50% de desconto? Com certeza mais do que R$ 69,90 por mês.
            </p>
            
            {/* Toggle Mensal/Anual */}
            <div className="inline-flex items-center gap-3 bg-slate-100 p-1 rounded-full">
              <button
                onClick={() => setIsAnnual(false)}
                className={`px-6 py-2 rounded-full font-medium transition ${!isAnnual ? 'bg-white shadow text-gray-800' : 'text-gray-600'}`}
              >
                Mensal
              </button>
              <button
                onClick={() => setIsAnnual(true)}
                className={`px-6 py-2 rounded-full font-medium transition ${isAnnual ? 'bg-white shadow text-gray-800' : 'text-gray-600'}`}
              >
                Anual
                <span className="ml-2 text-xs bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full">-22%</span>
              </button>
            </div>
          </div>
          
          {/* Card de Preço */}
          <div className="max-w-lg mx-auto">
            <div className="bg-gradient-to-br from-sky-500 to-blue-600 rounded-3xl p-1">
              <div className="bg-white rounded-3xl p-8">
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">LeiloHub Premium</h3>
                  <p className="text-gray-600">Acesso completo a todas as funcionalidades</p>
                </div>
                
                <div className="text-center mb-8">
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-5xl font-bold text-gray-800">
                      R$ {isAnnual ? '69,90' : '89,90'}
                    </span>
                    <span className="text-gray-500">/mês</span>
                  </div>
                  {isAnnual && (
                    <p className="text-sm text-gray-500 mt-2">
                      Cobrado anualmente (R$ 838,80)
                    </p>
                  )}
                </div>
                
                <ul className="space-y-4 mb-8">
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Acesso a 30.000+ imóveis</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">280+ leiloeiros monitorados</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Filtros avançados ilimitados</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Mapa interativo</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Ordenação por maior desconto</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Atualizações diárias</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-sky-500 flex-shrink-0" />
                    <span className="text-gray-700">Suporte por WhatsApp</span>
                  </li>
                </ul>
                
                <a
                  href="/"
                  className="block w-full bg-gradient-to-r from-sky-500 to-blue-600 text-white text-center py-4 rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-sky-500/25 transition"
                >
                  Começar 10 Dias Grátis
                </a>
                
                <p className="text-center text-sm text-gray-500 mt-4">
                  Sem cartão de crédito • Cancele quando quiser
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== FAQ ===== */}
      <section className="py-20 bg-slate-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              Perguntas frequentes
            </h2>
          </div>
          
          <div className="bg-white rounded-2xl p-6 md:p-8 shadow-sm">
            <FAQItem
              question="Como funciona o período de teste?"
              answer="Você tem 10 dias para testar todas as funcionalidades do LeiloHub gratuitamente, sem precisar cadastrar cartão de crédito. Durante esse período, pode visualizar até 20 imóveis completos. Se gostar, é só assinar para continuar com acesso ilimitado."
            />
            <FAQItem
              question="De onde vêm os imóveis listados?"
              answer="Monitoramos mais de 280 leiloeiros em todo o Brasil, incluindo Caixa Econômica Federal, Santander, Bradesco, além de leiloeiros judiciais e extrajudiciais. Nossa tecnologia de IA coleta e organiza os dados automaticamente."
            />
            <FAQItem
              question="Os dados são confiáveis e atualizados?"
              answer="Sim! Utilizamos inteligência artificial para manter os dados sempre atualizados e remover duplicatas. Cada imóvel tem link direto para o site oficial do leiloeiro, onde você pode confirmar as informações e dar seu lance."
            />
            <FAQItem
              question="Posso cancelar a qualquer momento?"
              answer="Sim, você pode cancelar sua assinatura a qualquer momento, sem multa ou burocracia. Basta acessar sua conta e solicitar o cancelamento. Você continuará tendo acesso até o fim do período pago."
            />
            <FAQItem
              question="O LeiloHub faz a arrematação por mim?"
              answer="Não. O LeiloHub é uma plataforma de busca e análise. Encontramos as melhores oportunidades e direcionamos você para o site do leiloeiro oficial, onde você faz seu cadastro e participa do leilão normalmente."
            />
            <FAQItem
              question="Vocês cobram comissão sobre arrematações?"
              answer="Não cobramos nenhuma comissão. Você paga apenas a assinatura mensal ou anual. Todo o lucro da sua arrematação é seu."
            />
          </div>
        </div>
      </section>

      {/* ===== CTA FINAL ===== */}
      <section className="py-20 bg-gradient-to-br from-sky-500 to-blue-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Pronto para encontrar seu próximo negócio?
          </h2>
          <p className="text-xl text-sky-100 mb-8 max-w-2xl mx-auto">
            Junte-se a centenas de investidores que já estão economizando tempo e encontrando as melhores oportunidades com o LeiloHub.
          </p>
          <a
            href="/"
            className="inline-flex items-center gap-2 bg-white text-sky-600 px-8 py-4 rounded-xl font-semibold text-lg hover:shadow-xl transition"
          >
            Começar Grátis Agora
            <ArrowRight className="w-5 h-5" />
          </a>
          <p className="mt-4 text-sky-100 text-sm">
            10 dias grátis • Sem cartão de crédito • Cancele quando quiser
          </p>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="bg-slate-900 text-slate-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            {/* Logo */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <img 
                  src="/logo-horizontal-trimmed.png" 
                  alt="LeiloHub" 
                  className="h-8"
                />
              </div>
              <p className="text-sm">
                A plataforma mais completa para encontrar imóveis de leilão no Brasil.
              </p>
            </div>
            
            {/* Links */}
            <div>
              <h4 className="text-white font-semibold mb-4">Produto</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#funcionalidades" className="hover:text-white transition">Funcionalidades</a></li>
                <li><a href="#precos" className="hover:text-white transition">Preços</a></li>
                <li><a href="#depoimentos" className="hover:text-white transition">Depoimentos</a></li>
                <li><a href="#" className="hover:text-white transition">FAQ</a></li>
              </ul>
            </div>
            
            {/* Legal */}
            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">Termos de Uso</a></li>
                <li><a href="#" className="hover:text-white transition">Política de Privacidade</a></li>
              </ul>
            </div>
            
            {/* Contato */}
            <div>
              <h4 className="text-white font-semibold mb-4">Contato</h4>
              <ul className="space-y-2 text-sm">
                <li>contato@leilohub.com.br</li>
                <li>WhatsApp: (11) 99999-9999</li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-800 pt-8 text-center text-sm">
            <p>© 2025 LeiloHub. Todos os direitos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

